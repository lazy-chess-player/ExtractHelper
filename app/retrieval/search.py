from __future__ import annotations
import sys
from app.retrieval.retrieve import retrieve_evidence

def search(query: str, top_k: int = 5) -> None:
    evidence = retrieve_evidence(query, top_k=top_k)

    print(f"\nQuery: {query}\n")
    for rank, e in enumerate(evidence, start=1):
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
