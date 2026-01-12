from __future__ import annotations

from sentence_transformers import SentenceTransformer
import numpy as np


class Embedder:
    def __init__(self, model_name: str):
        # SentenceTransformer 会自动选择设备（CPU/GPU）
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        返回 shape = (n, dim) 的 float32 向量，并且做归一化（用于余弦相似度 / IP检索）
        """
        vecs = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,   # 直接归一化
        )
        return np.asarray(vecs, dtype="float32")
