from __future__ import annotations

from app.bootstrap import bootstrap
bootstrap()

from sentence_transformers import SentenceTransformer
import numpy as np


class Embedder:
    """
    向量嵌入服务
    封装 SentenceTransformer，提供统一的 encode 接口。
    """
    def __init__(self, model_name: str):
        """
        初始化加载模型
        :param model_name: Hugging Face 模型名称或本地路径
        """
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        批量计算文本向量。
        
        :param texts: 文本列表
        :param batch_size: 批处理大小
        :return: Numpy 数组 (n_samples, embedding_dim)，float32 类型
        """
        vecs = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True, # 启用归一化，使得点积等同于余弦相似度
        )
        return np.asarray(vecs, dtype="float32")
