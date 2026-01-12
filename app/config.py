from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
KB_DIR = DATA_DIR / "kb"
DB_PATH = KB_DIR / "kb.sqlite3"

# 分块参数
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

RAW_DIR.mkdir(parents=True, exist_ok=True)
KB_DIR.mkdir(parents=True, exist_ok=True)

# Embedding 模型
EMBED_MODEL_NAME = "BAAI/bge-small-zh-v1.5"

# 索引文件路径：Base + Delta
FAISS_INDEX_PATH = KB_DIR / "faiss.index"
FAISS_DELTA_INDEX_PATH = KB_DIR / "faiss.delta.index"

# LLM 模型
MODELS_DIR = DATA_DIR / "models"
LLM_GGUF_PATH = MODELS_DIR / "qwen2.5-3b-instruct-q4_k_m.gguf"
