from __future__ import annotations

import sqlite3
from pathlib import Path

import faiss
import numpy as np

from app.config import DB_PATH, EMBED_MODEL_NAME, FAISS_INDEX_PATH
from app.retrieval.embedder import Embedder


def build_index(top_n: int | None = None) -> None:
    # 1) 读取数据库 chunks
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    sql = """
    SELECT c.id, c.content
    FROM chunks c
    ORDER BY c.id ASC
    """
    rows = cur.execute(sql).fetchall()
    conn.close()

    if top_n is not None:
        rows = rows[:top_n]

    if not rows:
        raise RuntimeError("chunks 表为空：请先运行入库脚本 python -m app.ingest.ingest")

    chunk_ids = np.array([r[0] for r in rows], dtype="int64")
    texts = [r[1] for r in rows]

    print(f"[index] loaded chunks: {len(texts)}")

    # 2) 向量化
    embedder = Embedder(EMBED_MODEL_NAME)
    vecs = embedder.encode(texts, batch_size=32)  # (n, dim)
    dim = vecs.shape[1]
    print(f"[index] embedding dim = {dim}")

    # 3) 建 FAISS 索引（用内积 IP，相当于余弦相似度，因为我们已归一化）
    base = faiss.IndexFlatIP(dim)

    # 关键点：用 IndexIDMap2 绑定 “向量ID = chunk_id”
    index = faiss.IndexIDMap2(base)
    index.add_with_ids(vecs, chunk_ids)

    # 4) 保存索引
    FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    print(f"[index] saved: {FAISS_INDEX_PATH}")


if __name__ == "__main__":
    build_index()
