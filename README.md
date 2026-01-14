# ExtractHelper

ExtractHelper 是一个 **本地离线优先（Local Offline-First）的 RAG 资料库助手**。
它支持将本地文档（PDF/MD/TXT）构建为向量知识库，并结合本地 GGUF 大模型进行检索增强生成（RAG）问答。
现已集成 **NiceGUI Web 界面**，稳定流畅，支持浏览器访问。

---

## 主要特性

- **本地隐私**：所有数据处理、向量检索、模型推理均在本地完成，无需联网。
- **多格式支持**：支持 PDF（保留页码）、Markdown、TXT 文档入库。
- **增量更新**：智能识别文件变更，仅处理新增或修改的文档。
- **混合索引**：结合 SQLite（元数据）与 FAISS（向量索引），支持高效检索。
- **图形界面**：基于 NiceGUI 的现代化 Web 界面，支持多轮对话、资料同步、索引管理。
- **稳定可靠**：摒弃了易崩溃的本地 Native GUI，采用成熟的 Web 技术栈。

---

## 快速开始

### 1. 环境准备

推荐使用 Conda 管理环境。

```bash
# 创建环境 (Python 3.10+)
conda create -n extracthelper python=3.10
conda activate extracthelper

# 安装依赖
pip install -r requirements.txt
```

### 2. 模型下载

本项目默认使用 `Qwen2.5-3B-Instruct` 的 GGUF 量化版本。请下载模型文件并放入 `data/models/` 目录。

```bash
# 使用 Hugging Face CLI 下载 (示例)
hf download Qwen/Qwen2.5-3B-Instruct-GGUF qwen2.5-3b-instruct-q4_k_m.gguf --local-dir data/models --local-dir-use-symlinks False
```

确保 `data/models/` 下存在 `qwen2.5-3b-instruct-q4_k_m.gguf` 文件（或修改 `app/config.py` 中的路径）。

### 3. 数据准备

将你的文档（PDF, MD, TXT）放入 `data/raw/` 目录中。

---

## 运行方式

### 方式 A：一键启动 (推荐)

直接双击项目根目录下的 **`run_gui.bat`** 脚本。
它会自动启动服务并在浏览器中打开界面。

或者在命令行运行：

```bash
python -m app.gui.web_app
```

访问地址：`http://localhost:8551`

- **智能问答 Tab**：像聊天软件一样提问，系统会自动检索并附带参考资料引用。
- **资料库管理 Tab**：
  - **同步 Raw 目录**：扫描 `data/raw`，自动处理新增/修改的文件。
  - **重建索引**：全量重新构建向量索引（推荐在大量变动后执行）。

### 方式 B：命令行 (CLI)

如果你更喜欢终端操作或需要自动化脚本：

1.  **入库同步**：
    ```bash
    python -m app.ingest.ingest sync
    ```
2.  **重建索引**：
    ```bash
    python -m app.ingest.ingest compact
    ```
3.  **多轮对话**：
    ```bash
    python -m app.rag.ask
    ```
4.  **单次检索测试**：
    ```bash
    python -m app.retrieval.search "动态规划 状态定义"
    ```

---

## 项目结构

```text
ExtractHelper/
  app/
    gui/
      web_app.py     # NiceGUI Web 界面入口 (主程序)
      flet_app.py    # (Legacy) Flet 界面
    ingest/          # 文档处理与入库 (SQLite)
    retrieval/       # 向量检索 (FAISS + SentenceTransformers)
    rag/             # 问答逻辑 (llama-cpp-python)
    app_core.py      # 核心业务逻辑封装
    config.py        # 全局配置
    bootstrap.py     # 环境初始化 (HF镜像等)
  data/
    raw/             # 原始文档存放处
    kb/              # 知识库数据 (SQLite, FAISS Index)
    models/          # GGUF 模型文件
  requirements.txt   # 依赖列表
  README.md          # 说明文档
  run_gui.bat        # Windows 启动脚本
```

## 注意事项

- **首次运行**：会自动下载 Embedding 模型（`BAAI/bge-small-zh-v1.5`），请确保网络通畅（已配置 HF 镜像）。
- **Web 端口**：默认使用 `8551` 端口。如果被占用，请修改 `app/gui/web_app.py`。
- **PyMuPDF**：如果遇到 `fitz` 导入错误，请确保安装的是 `pymupdf` 包。
