from __future__ import annotations

import sys
from pathlib import Path

"""
全局配置文件
定义项目路径、模型路径、分块参数等常量。
"""

# 判断是否在 PyInstaller 打包后的环境中运行
# 如果 sys.frozen 为 True，说明是打包后的 exe，路径需要动态获取
if getattr(sys, "frozen", False):
    # 打包后，executable 指向 exe 文件本身
    # 我们希望 data 目录在 exe 同级目录下
    PROJECT_ROOT = Path(sys.executable).parent
else:
    # 开发模式：基于当前文件定位项目根目录
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 数据存储目录
DATA_DIR = PROJECT_ROOT / "data"
# 原始文档目录 (PDF/MD/TXT)
RAW_DIR = DATA_DIR / "raw"
# 知识库数据目录 (SQLite/FAISS)
KB_DIR = DATA_DIR / "kb"
# SQLite 数据库路径
DB_PATH = KB_DIR / "kb.sqlite3"

# 文档分块参数
# CHUNK_SIZE: 每个分块的目标字符数
CHUNK_SIZE = 900
# CHUNK_OVERLAP: 分块间的重叠字符数，用于保持上下文连贯
CHUNK_OVERLAP = 150

# 自动创建必要目录
RAW_DIR.mkdir(parents=True, exist_ok=True)
KB_DIR.mkdir(parents=True, exist_ok=True)

# Embedding 模型名称 (Sentence Transformers)
# 使用 BAAI/bge-small-zh-v1.5 适合中文场景
EMBED_MODEL_NAME = "BAAI/bge-small-zh-v1.5"

# FAISS 索引文件路径
# Base Index: 全量索引，通常在 compact/rebuild 时生成
FAISS_INDEX_PATH = KB_DIR / "faiss.index"
# Delta Index: 增量索引，用于存储新入库但未合并的 chunks
FAISS_DELTA_INDEX_PATH = KB_DIR / "faiss.delta.index"

# LLM 模型目录与路径 (GGUF 格式)
MODELS_DIR = DATA_DIR / "models"
LLM_GGUF_PATH = MODELS_DIR / "qwen2.5-3b-instruct-q4_k_m.gguf"
