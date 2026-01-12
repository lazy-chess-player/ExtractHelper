from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pymupdf  # PyMuPDF


@dataclass
class DocText:
    path: Path
    doc_type: str          # "pdf" / "txt" / "md"
    text: str
    pages: Optional[List[Tuple[int, str]]] = None  # 仅PDF：[(page_no, text), ...]


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
        t = page.get_text("text") or ""
        t = t.strip()
        pages.append((i + 1, t))
        full.append(t)
    text = "\n\n".join(full).strip()
    return DocText(path=path, doc_type="pdf", text=text, pages=pages)


def load_document(path: Path) -> DocText:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix == ".txt":
        return load_txt(path)
    if suffix == ".md":
        return load_md(path)
    raise ValueError(f"Unsupported file type: {path.name}")


def iter_documents(folder: Path) -> Iterable[Path]:
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".pdf", ".txt", ".md"}:
            yield p
