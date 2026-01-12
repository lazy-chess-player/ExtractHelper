
# ExtractHelper

## 中文简介

ExtractHelper 是一个 **本地离线优先（offline-first）的 RAG（Retrieval-Augmented Generation）资料库助手**。它把本地文档入库到 SQLite，使用向量检索（FAISS）找到证据片段，再调用本地 GGUF 大模型（llama.cpp / llama-cpp-python）生成回答，并输出可追溯的证据来源。

适用场景：本地资料整理，算法/课程资料检索等。

---

## English Overview

ExtractHelper is a **local, offline-first RAG (Retrieval-Augmented Generation) knowledge base assistant**.

Workflow:

1. Put documents into `data/raw/`
2. Ingest into SQLite with chunking
3. Build a FAISS vector index with local embeddings
4. Ask questions with a local GGUF LLM (llama.cpp) and show evidence

> Recommended platform: Windows 10/11, Conda environment, Python 3.10+.

---

## 功能 Features

### 中文

- 文档入库：PDF / TXT / MD -> 解析 -> 分块（chunking） -> SQLite
- 向量检索：Sentence Transformers 生成 embedding，FAISS 建索引并检索 TopK 证据
- 本地 RAG 问答：TopK 证据拼上下文，调用本地 GGUF 模型生成回答
- 证据展示：输出证据列表（来源文件、页码、相似度分数、片段）

### English

- Document ingestion: PDF / TXT / MD -> parse -> chunk -> SQLite
- Retrieval: Sentence Transformers embeddings + FAISS TopK search
- Local RAG: build a bounded context from evidence and call a local GGUF model
- Evidence display: show evidence list with source metadata and scores

---

## Project structure / 项目结构（推荐）

> 说明：这是推荐结构。若你的实际结构与此略有差异，以你的仓库为准。

```text
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
    raw/                # input documents (NOT committed)
    kb/                 # kb.sqlite3, faiss.index, HF cache (NOT committed)
    models/             # GGUF models (NOT committed)
  scripts/
    download_gguf.py
  env_setup.bat
  check_env.py
  requirements.txt
  environment.yml
  PROJECT_HANDOFF.md
  README.md
  .gitignore
```

------

## Quick start / 快速开始

### 1) Create and activate env / 创建并激活环境

```bat
conda env create -f environment.yml
conda activate extracthelper
pip install -r requirements.txt
```

### 2) (Recommended) set Hugging Face cache / 设置 Hugging Face 缓存与镜像

Create `env_setup.bat` at the repo root:

```bat
@echo off
set HF_ENDPOINT=https://hf-mirror.com
set HF_HOME=%CD%\\data\\kb\\hf_home
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

echo HF_ENDPOINT=%HF_ENDPOINT%
echo HF_HOME=%HF_HOME%
echo Done.
```

Then every time you open a new terminal:

```bat
cd /d D:\\Code\\Project\\ExtractHelper
call env_setup.bat
conda activate extracthelper
```

### 3) Self check / 环境自检

```bat
python check_env.py
```

Expected: `ALL OK`.

### 4) Ingest documents / 入库

Put files into `data\\raw\\`, then run:

```bat
python -m app.ingest.ingest
```

### 5) Build index / 建索引

```bat
python -m app.retrieval.build_index
```

### 6) Search / 检索

```bat
python -m app.retrieval.search "动态规划 状态定义"
```

### 7) Download a GGUF LLM / 下载 GGUF 模型（示例）

Option A (hf CLI):

```bat
hf download Qwen/Qwen2.5-3B-Instruct-GGUF qwen2.5-3b-instruct-q4_k_m.gguf --local-dir data\\models --local-dir-use-symlinks False
```

Option B (Python script):

```bat
python scripts\\download_gguf.py
```

### 8) RAG ask / RAG 问答

Make sure `app/config.py` points to the GGUF file:

```python
MODELS_DIR = DATA_DIR / "models"
LLM_GGUF_PATH = MODELS_DIR / "qwen2.5-3b-instruct-q4_k_m.gguf"
```

Then:

```bat
python -m app.rag.ask "什么是dp？dp有哪些类型？"
```

------

## KB update (add / update / delete) / 资料库更新（增改删）

A simple, stable workflow is to rebuild after ingestion.

Create `update_kb.bat`:

```bat
@echo off
cd /d %~dp0

call env_setup.bat
conda activate extracthelper

python -m app.ingest.ingest
python -m app.retrieval.build_index

echo DONE.
```

Usage:

```bat
update_kb.bat
```

------

