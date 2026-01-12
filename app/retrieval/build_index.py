from __future__ import annotations

import sqlite3
import faiss
import numpy as np

from app.config import DB_PATH, EMBED_MODEL_NAME, FAISS_INDEX_PATH, FAISS_DELTA_INDEX_PATH
from app.retrieval.embedder import Embedder
from app.ingest.db import connect, ensure_schema


def build_index(top_n: int | None = None) -> None:
    conn = connect(DB_PATH)
    ensure_schema(conn)

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

    embedder = Embedder(EMBED_MODEL_NAME)
    vecs = embedder.encode(texts, batch_size=32)
    dim = int(vecs.shape[1])

    base = faiss.IndexFlatIP(dim)
    index = faiss.IndexIDMap2(base)
    index.add_with_ids(vecs, chunk_ids)

    FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    print(f"[index] saved base: {FAISS_INDEX_PATH}")

    # reset delta
    empty_delta = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
    faiss.write_index(empty_delta, str(FAISS_DELTA_INDEX_PATH))
    print(f"[index] reset delta: {FAISS_DELTA_INDEX_PATH}")


if __name__ == "__main__":
    build_index()
