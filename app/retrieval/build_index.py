from __future__ import annotations

import sqlite3
import faiss
import numpy as np

from app.config import DB_PATH, EMBED_MODEL_NAME, FAISS_INDEX_PATH, FAISS_DELTA_INDEX_PATH
from app.retrieval.embedder import Embedder
from app.ingest.db import connect, ensure_schema

"""
索引构建模块
负责从 SQLite 数据库中读取所有 Active Chunks，全量构建 FAISS 索引。
通常在初次入库后、或需要整理碎片时调用。
"""

def build_index(top_n: int | None = None) -> None:
    """
    全量重建索引流程：
    1. 连接 DB，读取所有未删除的 Chunks。
    2. 计算所有文本的 Embedding。
    3. 创建新的 IndexIDMap2 (FlatIP)。
    4. 写入 Base Index 文件。
    5. 重置（清空）Delta Index 文件。
    
    :param top_n: 仅处理前 N 条数据（用于测试）
    """
    conn = connect(DB_PATH)
    ensure_schema(conn)

    # 读取 Active Chunks
    rows = conn.execute(
        """
        SELECT c.id, c.content
        FROM chunks c
        JOIN documents d ON d.id = c.doc_id
        WHERE c.is_deleted = 0 AND d.is_deleted = 0
        ORDER BY c.id ASC
        """
    ).fetchall()
    conn.close()

    if top_n is not None:
        rows = rows[:top_n]

    if not rows:
        raise RuntimeError("active chunks 为空：请先 ingest")

    chunk_ids = np.array([r[0] for r in rows], dtype="int64")
    texts = [r[1] for r in rows]

    print(f"[index] loaded active chunks: {len(texts)}")

    # 批量计算向量
    embedder = Embedder(EMBED_MODEL_NAME)
    vecs = embedder.encode(texts, batch_size=32)
    dim = int(vecs.shape[1])

    # 构建 Base Index
    base = faiss.IndexFlatIP(dim)
    index = faiss.IndexIDMap2(base)
    index.add_with_ids(vecs, chunk_ids)

    FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    print(f"[index] saved base: {FAISS_INDEX_PATH}")

    # 重置 Delta Index
    # Base Index 已经包含了所有当前有效数据，因此 Delta 可以清空
    empty_delta = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
    faiss.write_index(empty_delta, str(FAISS_DELTA_INDEX_PATH))
    print(f"[index] reset delta: {FAISS_DELTA_INDEX_PATH}")


if __name__ == "__main__":
    build_index()
