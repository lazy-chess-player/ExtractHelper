from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import faiss

from app.config import (
    DB_PATH,
    EMBED_MODEL_NAME,
    FAISS_INDEX_PATH,
    FAISS_DELTA_INDEX_PATH,
)
from app.retrieval.embedder import Embedder
from app.ingest.db import connect, ensure_schema

def _load_index_maybe(path: Path):
    if path.exists():
        return faiss.read_index(str(path))
    return None

def _ensure_delta_index(dim: int):
    base = faiss.IndexFlatIP(dim)
    return faiss.IndexIDMap2(base)

def load_base_and_delta() -> Tuple[Any, Any]:
    base = _load_index_maybe(FAISS_INDEX_PATH)
    delta = _load_index_maybe(FAISS_DELTA_INDEX_PATH)
    return base, delta

def fetch_chunk(conn, chunk_id: int):
    sql = """
    SELECT d.path, d.doc_type, c.page, c.id, c.content
    FROM chunks c
    JOIN documents d ON d.id = c.doc_id
    WHERE c.id = ?
      AND c.is_deleted = 0
      AND d.is_deleted = 0
    """
    return conn.execute(sql, (chunk_id,)).fetchone()

def retrieve_evidence(query: str, top_k: int = 5, overfetch: int = 5) -> List[Dict[str, Any]]:
    base, delta = load_base_and_delta()
    if base is None and delta is None:
        raise RuntimeError("找不到任何索引文件：请先 build_index 或先 ingest 生成 delta")

    embedder = Embedder(EMBED_MODEL_NAME)
    qvec = embedder.encode([query], batch_size=1)

    k = max(top_k * overfetch, top_k)
    pairs: List[Tuple[float, int]] = []

    for idx in (base, delta):
        if idx is None:
            continue
        scores, ids = idx.search(qvec, k)
        for s, cid in zip(scores[0], ids[0]):
            cid = int(cid)
            if cid == -1:
                continue
            pairs.append((float(s), cid))

    pairs.sort(key=lambda x: x[0], reverse=True)

    # dedup chunk_id
    best: Dict[int, float] = {}
    for s, cid in pairs:
        if cid not in best:
            best[cid] = s

    conn = connect(DB_PATH)
    ensure_schema(conn)

    evidence: List[Dict[str, Any]] = []
    for cid, score in sorted(best.items(), key=lambda x: x[1], reverse=True):
        row = fetch_chunk(conn, cid)
        if not row:
            continue
        path, doc_type, page, chunk_id, content = row
        evidence.append(
            {
                "score": float(score),
                "path": str(path),
                "filename": Path(str(path)).name,
                "doc_type": doc_type,
                "page": page,
                "chunk_id": int(chunk_id),
                "content": content,
                "snippet": (content or "").replace("\n", " ")[:240],
            }
        )
        if len(evidence) >= top_k:
            break

    conn.close()
    return evidence

def add_to_delta_index(chunk_ids: List[int], texts: List[str]) -> None:
    if not chunk_ids:
        return

    embedder = Embedder(EMBED_MODEL_NAME)
    vecs = embedder.encode(texts, batch_size=32)
    dim = int(vecs.shape[1])

    delta = _load_index_maybe(FAISS_DELTA_INDEX_PATH)
    if delta is None:
        delta = _ensure_delta_index(dim)

    ids = np.asarray(chunk_ids, dtype="int64")
    delta.add_with_ids(vecs, ids)

    FAISS_DELTA_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(delta, str(FAISS_DELTA_INDEX_PATH))
