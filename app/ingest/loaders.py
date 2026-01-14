from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import fitz  # PyMuPDF

"""
文档加载模块
负责读取不同格式文件（PDF, TXT, MD），统一转换为 DocText 对象。
"""

@dataclass
class DocText:
    """文档内容结构体"""
    path: Path
    doc_type: str
    text: str
    pages: Optional[List[Tuple[int, str]]] = None  # PDF: [(page_no, text)]

# 注册加载器的类型别名
LoaderFn = Callable[[Path], DocText]
_LOADER_REGISTRY: Dict[str, LoaderFn] = {}

def register_loader(suffix: str, fn: LoaderFn) -> None:
    """注册特定后缀的加载器"""
    _LOADER_REGISTRY[suffix.lower()] = fn

def supported_suffixes() -> set[str]:
    """获取所有支持的文件后缀集合"""
    return set(_LOADER_REGISTRY.keys())

def load_txt(path: Path) -> DocText:
    """加载 TXT 文件"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return DocText(path=path, doc_type="txt", text=text)

def load_md(path: Path) -> DocText:
    """加载 Markdown 文件"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return DocText(path=path, doc_type="md", text=text)

def load_pdf(path: Path) -> DocText:
    """
    加载 PDF 文件
    使用 PyMuPDF 提取每一页的文本，并保留页码信息。
    """
    doc = fitz.open(path)
    full_text = []
    pages = []
    
    for page_index, page in enumerate(doc):
        # 提取当前页文本
        t = page.get_text()
        full_text.append(t)
        # 页码从1开始
        pages.append((page_index + 1, t))
    
    return DocText(
        path=path,
        doc_type="pdf",
        text="\n".join(full_text),
        pages=pages
    )

# 注册默认支持的格式
register_loader(".pdf", load_pdf)
register_loader(".txt", load_txt)
register_loader(".md", load_md)

def load_document(path: Path) -> DocText:
    """
    通用加载入口
    根据文件后缀自动选择加载器。
    """
    fn = _LOADER_REGISTRY.get(path.suffix.lower())
    if not fn:
        raise ValueError(f"Unsupported file type: {path.name}")
    return fn(path)

def iter_documents(folder: Path) -> Iterable[Path]:
    """
    递归遍历目录，返回所有支持格式的文件路径。
    """
    exts = supported_suffixes()
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p
