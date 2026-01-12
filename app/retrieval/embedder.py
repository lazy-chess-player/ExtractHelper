from __future__ import annotations

from app.bootstrap import bootstrap
bootstrap()

from sentence_transformers import SentenceTransformer
import numpy as np


class Embedder:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        vecs = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        return np.asarray(vecs, dtype="float32")
