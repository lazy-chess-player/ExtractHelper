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

"""
检索模块
负责从 FAISS 索引（Base + Delta）中检索最相似的 Chunks。
"""

def _load_index_maybe(path: Path):
    """尝试加载 FAISS 索引，不存在则返回 None"""
    if path.exists():
        return faiss.read_index(str(path))
    return None

def _ensure_delta_index(dim: int):
    """确保 Delta 索引存在（创建新的 IndexIDMap2 + IndexFlatIP）"""
    base = faiss.IndexFlatIP(dim)
    return faiss.IndexIDMap2(base)

def load_base_and_delta() -> Tuple[Any, Any]:
    """加载 Base 和 Delta 两个索引"""
    base = _load_index_maybe(FAISS_INDEX_PATH)
    delta = _load_index_maybe(FAISS_DELTA_INDEX_PATH)
    return base, delta

def fetch_chunk(conn, chunk_id: int):
    """
    根据 ID 从 SQLite 获取 Chunk 详情。
    同时过滤已删除的 Chunk 或 Document。
    """
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
    """
    执行向量检索。
    
    1. 加载 Base 和 Delta 索引。
    2. 计算 Query 向量。
    3. 在两个索引中分别检索 Top K * overfetch 个结果。
    4. 合并结果，按分数排序并去重。
    5. 从 DB 回查内容，过滤已删除项。
    6. 返回最终 Top K 结果。
    
    :param query: 查询语句
    :param top_k: 目标结果数量
    :param overfetch: 预取倍数（应对删除项过滤）
    :return: 证据列表
    """
    base, delta = load_base_and_delta()
    if base is None and delta is None:
        raise RuntimeError("找不到任何索引文件：请先 build_index 或先 ingest 生成 delta")

    embedder = Embedder(EMBED_MODEL_NAME)
    qvec = embedder.encode([query], batch_size=1)

    k = max(top_k * overfetch, top_k)
    pairs: List[Tuple[float, int]] = []

    # 分别搜索 Base 和 Delta
    for idx in (base, delta):
        if idx is None:
            continue
        scores, ids = idx.search(qvec, k)
        for s, cid in zip(scores[0], ids[0]):
            cid = int(cid)
            if cid == -1:
                continue
            pairs.append((float(s), cid))

    # 全局排序
    pairs.sort(key=lambda x: x[0], reverse=True)

    # 去重 (同一 Chunk ID 取最高分，理论上不会有重复ID，除非索引错乱，这里做保险)
    best: Dict[int, float] = {}
    for s, cid in pairs:
        if cid not in best:
            best[cid] = s

    conn = connect(DB_PATH)
    ensure_schema(conn)

    evidence: List[Dict[str, Any]] = []
    # 逐个回查 DB，直到凑够 top_k
    for cid, score in sorted(best.items(), key=lambda x: x[1], reverse=True):
        row = fetch_chunk(conn, cid)
        if not row:
            continue # 已删除或不存在
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
    """
    实时向 Delta 索引添加新向量。
    
    :param chunk_ids: 新 Chunk 的 ID 列表
    :param texts: 对应的文本列表
    """
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
