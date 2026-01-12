# ExtractHelper

A local RAG (Retrieval Augmented Generation) knowledge base assistant.

The project supports a full offline workflow:

1. Put documents into `data/raw/`
2. Ingest into SQLite with chunking
3. Build a FAISS vector index with local embeddings
4. Ask questions with a local GGUF LLM (llama.cpp) and show evidence

> Recommended platform: Windows 10/11, Conda environment, Python 3.10+.

---

## Features

- Document ingestion
  - Supported: PDF, TXT, MD
  - Chunking with overlap and basic cleaning
  - Store metadata and chunks in SQLite
- Retrieval
  - Embeddings with Sentence Transformers
  - FAISS IndexIDMap2, vector id equals `chunks.id`
  - CLI search that prints TopK evidence with score and snippet
- RAG Q&A
  - Retrieve TopK, build context, call `llama-cpp-python` with a local GGUF model
  - Evidence list plus answer with citations

---

## Project structure (expected)

```
ExtractHelper/
  app/
    config.py
    ingest/
      loaders.py
      chunker.py
      db.py
      ingest.py
    retrieval/
      embedder.py
      build_index.py
      search.py
    rag/
      ask.py
  data/
    raw/                # input documents (not committed)
    kb/                 # kb.sqlite3, faiss.index, hf cache (not committed)
    models/             # GGUF models (not committed)
  scripts/
    download_gguf.py
  env_setup.bat
  check_env.py
  requirements.txt
  environment.yml
  PROJECT_HANDOFF.md
  README.md
```

---

## Quick start

### 1) Create and activate env

If you already have `environment.yml` + `requirements.txt`:

```bat
conda env create -f environment.yml
conda activate extracthelper
pip install -r requirements.txt
```

### 2) (Recommended) set Hugging Face cache + mirror

Create `env_setup.bat` at the repo root:

```bat
@echo off
set HF_ENDPOINT=https://hf-mirror.com
set HF_HOME=%CD%\data\kb\hf_home
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

echo HF_ENDPOINT=%HF_ENDPOINT%
echo HF_HOME=%HF_HOME%
echo Done.
```

Then, every time you open a new terminal:

```bat
cd /d D:\Code\Project\ExtractHelper
call env_setup.bat
conda activate extracthelper
```

### 3) Self check

```bat
python check_env.py
```

Expected: `ALL OK`.

### 4) Ingest documents

Put files into `data\raw\`, then run:

```bat
python -m app.ingest.ingest
```

### 5) Build index

```bat
python -m app.retrieval.build_index
```

### 6) Search

```bat
python -m app.retrieval.search "动态规划 状态定义"
```

### 7) Download a GGUF LLM (example: Qwen2.5-3B)

Option A (hf CLI):

```bat
hf download Qwen/Qwen2.5-3B-Instruct-GGUF qwen2.5-3b-instruct-q4_k_m.gguf --local-dir data\models --local-dir-use-symlinks False
```

Option B (Python script):

```bat
python scripts\download_gguf.py
```

### 8) RAG ask

Make sure `app/config.py` points to the GGUF file:

```python
MODELS_DIR = DATA_DIR / "models"
LLM_GGUF_PATH = MODELS_DIR / "qwen2.5-3b-instruct-q4_k_m.gguf"
```

Then:

```bat
python -m app.rag.ask "什么是dp？dp有哪些类型？"
```

---

## Notes

- Large data (documents, caches, GGUF models) should not be committed. Use `.gitignore`.
- If you want to publish a reproducible demo, put a small sample file into `data/raw_sample/` and update README.

---

## License

Choose a license (MIT is commonly used for learning projects).
