from __future__ import annotations

import sys
import re
from llama_cpp import Llama

from app.config import LLM_GGUF_PATH
from app.retrieval.retrieve import retrieve_evidence


def _clean_snippet(text: str, max_len: int = 220) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) > max_len:
        t = t[:max_len] + "…"
    return t

def build_context_for_llm(evidence, per_doc_max_chars: int = 1200, max_total_chars: int = 6000) -> str:
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
        print('用法: python -m app.rag.ask "question"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    evidence = retrieve_evidence(query, top_k=5)
    context = build_context_for_llm(evidence)

    if not LLM_GGUF_PATH.exists():
        raise FileNotFoundError(f"找不到模型文件: {LLM_GGUF_PATH}")

    llm = Llama(
        model_path=str(LLM_GGUF_PATH),
        n_ctx=4096,
        n_threads=8,
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
        {"role": "user", "content": f"资料如下：\n\n{context}\n\n问题：{query}"},
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
        print(f"[{i}] {e['filename']}  (chunk_id={e['chunk_id']}, score={e['score']:.4f})")
        print(f"    {_clean_snippet(e['content'], 240)}\n")

if __name__ == "__main__":
    main()
