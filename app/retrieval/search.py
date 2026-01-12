from __future__ import annotations

import sqlite3
import sys

import faiss
import numpy as np

from app.config import DB_PATH, EMBED_MODEL_NAME, FAISS_INDEX_PATH
from app.retrieval.embedder import Embedder


def fetch_chunk(conn: sqlite3.Connection, chunk_id: int):
    sql = """
    SELECT d.path, d.doc_type, c.page, c.content
    FROM chunks c
    JOIN documents d ON d.id = c.doc_id
    WHERE c.id = ?
    """
    return conn.execute(sql, (chunk_id,)).fetchone()


def search(query: str, top_k: int = 5) -> None:
    if not FAISS_INDEX_PATH.exists():
        raise RuntimeError("找不到 faiss.index：请先运行 python -m app.retrieval.build_index")

    # 1) load index
    index = faiss.read_index(str(FAISS_INDEX_PATH))

    # 2) embed query
    embedder = Embedder(EMBED_MODEL_NAME)
    qvec = embedder.encode([query], batch_size=1)  # (1, dim)

    # 3) search
    scores, ids = index.search(qvec, top_k)

    conn = sqlite3.connect(str(DB_PATH))

    print(f"\nQuery: {query}\n")
    for rank, (score, cid) in enumerate(zip(scores[0], ids[0]), start=1):
        if cid == -1:
            continue
        row = fetch_chunk(conn, int(cid))
        if not row:
            continue

        path, doc_type, page, content = row
        snippet = content[:200].replace("\n", " ").strip()

        print(f"[{rank}] score={float(score):.4f}")
        print(f"    source: {path} ({doc_type}) page={page}")
        print(f"    text  : {snippet}")
        print()

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('用法: python -m app.retrieval.search "你的问题"')
        sys.exit(1)

    q = " ".join(sys.argv[1:])
    search(q, top_k=5)
