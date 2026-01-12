from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Chunk:
    idx: int
    text: str
    page: Optional[int] = None  # PDF可用页码；TXT/MD可先留空


def simple_chunk(text: str, chunk_size: int, overlap: int) -> List[Chunk]:
    text = (text or "").strip()
    if not text:
        return []

    chunks: List[Chunk] = []
    start = 0
    idx = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        piece = text[start:end].strip()
        if piece:
            chunks.append(Chunk(idx=idx, text=piece))
            idx += 1
        if end == n:
            break
        start = max(0, end - overlap)

    return chunks
