from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

"""
文档分块模块
提供简单的文本切片功能，支持重叠窗口。
"""

@dataclass
class Chunk:
    """分块结果结构体"""
    idx: int          # 在当前文档中的序号
    text: str         # 分块文本内容
    page: Optional[int] = None  # PDF可用页码；TXT/MD可先留空


def simple_chunk(text: str, chunk_size: int, overlap: int) -> List[Chunk]:
    """
    简单滑动窗口分块
    
    :param text: 输入长文本
    :param chunk_size: 每个块的最大字符长度
    :param overlap: 相邻块之间的重叠字符长度
    :return: Chunk 列表
    """
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
            
        # 移动窗口起点，回退 overlap 长度
        start = max(0, end - overlap)

    return chunks
