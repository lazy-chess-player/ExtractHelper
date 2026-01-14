from __future__ import annotations
import sys
from app.retrieval.retrieve import retrieve_evidence

"""
命令行检索工具
用法: python -m app.retrieval.search "查询语句"
"""

def search(query: str, top_k: int = 5) -> None:
    """
    执行检索并打印结果到控制台。
    """
    evidence = retrieve_evidence(query, top_k=top_k)

    print(f"\nQuery: {query}\n")
    for rank, e in enumerate(evidence, start=1):
        # 截断展示
        snippet = (e["content"] or "")[:200].replace("\n", " ").strip()
        print(f"[{rank}] score={float(e['score']):.4f}")
        print(f"    source: {e['path']} ({e['doc_type']}) page={e['page']}")
        print(f"    text  : {snippet}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('用法: python -m app.retrieval.search "query"')
        sys.exit(1)
    q = " ".join(sys.argv[1:])
    search(q, top_k=5)
