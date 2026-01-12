from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import pymupdf  # PyMuPDF

@dataclass
class DocText:
    path: Path
    doc_type: str
    text: str
    pages: Optional[List[Tuple[int, str]]] = None  # PDF: [(page_no, text)]

LoaderFn = Callable[[Path], DocText]
_LOADER_REGISTRY: Dict[str, LoaderFn] = {}

def register_loader(suffix: str, fn: LoaderFn) -> None:
    _LOADER_REGISTRY[suffix.lower()] = fn

def supported_suffixes() -> set[str]:
    return set(_LOADER_REGISTRY.keys())

def load_txt(path: Path) -> DocText:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return DocText(path=path, doc_type="txt", text=text)

def load_md(path: Path) -> DocText:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return DocText(path=path, doc_type="md", text=text)

def load_pdf(path: Path) -> DocText:
    doc = pymupdf.open(str(path))
    pages: List[Tuple[int, str]] = []
    full = []
    for i in range(len(doc)):
        page = doc[i]
        t = (page.get_text("text") or "").strip()
        pages.append((i + 1, t))
        full.append(t)
    text = "\n\n".join(full).strip()
    return DocText(path=path, doc_type="pdf", text=text, pages=pages)

register_loader(".pdf", load_pdf)
register_loader(".txt", load_txt)
register_loader(".md", load_md)

def load_document(path: Path) -> DocText:
    fn = _LOADER_REGISTRY.get(path.suffix.lower())
    if not fn:
        raise ValueError(f"Unsupported file type: {path.name}")
    return fn(path)

def iter_documents(folder: Path) -> Iterable[Path]:
    exts = supported_suffixes()
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p
