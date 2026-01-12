from __future__ import annotations

import sqlite3
import sys
import re
from pathlib import Path

import faiss
from llama_cpp import Llama

from app.config import (
    DB_PATH,
    EMBED_MODEL_NAME,
    FAISS_INDEX_PATH,
    LLM_GGUF_PATH,
)
from app.retrieval.embedder import Embedder


def _clean_snippet(text: str, max_len: int = 220) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) > max_len:
        t = t[:max_len] + "…"
    return t


def fetch_chunk(conn: sqlite3.Connection, chunk_id: int):
    sql = """
    SELECT d.path, c.id, c.content
    FROM chunks c
    JOIN documents d ON d.id = c.doc_id
    WHERE c.id = ?
    """
    return conn.execute(sql, (chunk_id,)).fetchone()


def retrieve(query: str, top_k: int = 5):
    if not FAISS_INDEX_PATH.exists():
        raise FileNotFoundError(f"找不到索引文件: {FAISS_INDEX_PATH}，请先 build_index")

    index = faiss.read_index(str(FAISS_INDEX_PATH))
    embedder = Embedder(EMBED_MODEL_NAME)
    qvec = embedder.encode([query], batch_size=1)
    scores, ids = index.search(qvec, top_k)

    conn = sqlite3.connect(str(DB_PATH))
    evidence = []
    for score, cid in zip(scores[0], ids[0]):
        cid = int(cid)
        if cid == -1:
            continue
        row = fetch_chunk(conn, cid)
        if not row:
            continue
        path, chunk_id, content = row
        evidence.append(
            {
                "score": float(score),
                "path": str(path),
                "filename": Path(str(path)).name,
                "chunk_id": int(chunk_id),
                "content": content,
                "snippet": _clean_snippet(content, 240),
            }
        )
    conn.close()
    return evidence


def build_context_for_llm(evidence, per_doc_max_chars: int = 1200, max_total_chars: int = 6000) -> str:
    # 给模型的“资料区”不要无限长，避免变慢/跑偏
    blocks = []
    total = 0
    for i, e in enumerate(evidence, start=1):
        content = (e["content"] or "").strip()
        content = re.sub(r"\s+\n", "\n", content)

        if len(content) > per_doc_max_chars:
            content = content[:per_doc_max_chars] + "…"

        block = f"[Doc{i}] source={e['filename']} chunk_id={e['chunk_id']} score={e['score']:.4f}\n{content}"
        if total + len(block) > max_total_chars:
            break
        blocks.append(block)
        total += len(block)

    return "\n\n---\n\n".join(blocks)


def main():
    if len(sys.argv) < 2:
        print('用法: python -m app.rag.ask "你的问题"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    evidence = retrieve(query, top_k=5)
    context = build_context_for_llm(evidence)

    if not LLM_GGUF_PATH.exists():
        raise FileNotFoundError(f"找不到模型文件: {LLM_GGUF_PATH}")

    llm = Llama(
        model_path=str(LLM_GGUF_PATH),
        n_ctx=4096,
        n_threads=8,
        # 如果你发现回答格式怪/不听话，再打开这行：
        # chat_format="chatml",
        verbose=False,
    )

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个本地知识库助手，只能根据我提供的资料回答，禁止编造。"
                "【硬性要求】每句话末尾必须标注引用，格式只能是 [1] 或 [2] 或 [1][2]…（对应 Doc 编号）。"
                "如果资料不足，直接回答“资料中没有/不确定”，并同样给出引用（引用最相关的 Doc）。"
            ),
        },
        {
            "role": "user",
            "content": f"资料如下：\n\n{context}\n\n问题：{query}",
        },
    ]

    out = llm.create_chat_completion(
        messages=messages,
        temperature=0.2,
        max_tokens=512,
    )
    answer = out["choices"][0]["message"]["content"]

    print("\n=== Answer ===\n")
    print(answer)

    print("\n=== References (Readable Evidence) ===\n")
    for i, e in enumerate(evidence, start=1):
        # C 格式：编号 + 文件名 + 可读片段
        print(f"[{i}] {e['filename']}  (chunk_id={e['chunk_id']}, score={e['score']:.4f})")
        print(f"    {e['snippet']}\n")


if __name__ == "__main__":
    main()
