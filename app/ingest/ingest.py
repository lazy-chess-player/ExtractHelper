from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import List, Tuple

from app.config import CHUNK_OVERLAP, CHUNK_SIZE, DB_PATH, RAW_DIR
from app.ingest.loaders import iter_documents, load_document, DocText
from app.ingest.chunker import simple_chunk
from app.ingest.db import (
    connect,
    ensure_schema,
    get_document,
    upsert_document,
    mark_document_deleted,
    mark_chunks_deleted_for_doc,
    insert_chunk,
)
from app.retrieval.retrieve import add_to_delta_index
from app.retrieval.build_index import build_index


def _file_stat(p: Path) -> Tuple[float, int]:
    st = p.stat()
    return float(st.st_mtime), int(st.st_size)

def _sha256_file(p: Path, buf: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def _chunk_doc(doc: DocText):
    if doc.pages:
        out = []
        idx = 0
        for page_no, page_text in doc.pages:
            for ch in simple_chunk(page_text, CHUNK_SIZE, CHUNK_OVERLAP):
                ch.page = page_no
                ch.idx = idx
                idx += 1
                out.append(ch)
        return out
    return simple_chunk(doc.text, CHUNK_SIZE, CHUNK_OVERLAP)

def _ingest_one(conn, fp: Path, force: bool = False) -> int:
    path = str(fp)
    mtime, size = _file_stat(fp)
    row = get_document(conn, path)

    if row and not force:
        doc_id, doc_type, file_hash, old_mtime, old_size, is_deleted = row
        if is_deleted == 0 and old_mtime == mtime and old_size == size:
            return 0

    file_hash = _sha256_file(fp)
    doc = load_document(fp)
    doc_id = upsert_document(conn, path, doc.doc_type, file_hash, mtime, size)

    # 更新：旧 chunks 软删除
    mark_chunks_deleted_for_doc(conn, doc_id)

    chunks = _chunk_doc(doc)
    new_ids: List[int] = []
    new_texts: List[str] = []

    for ch in chunks:
        cid = insert_chunk(conn, doc_id, ch.idx, ch.text, ch.page)
        new_ids.append(cid)
        new_texts.append(ch.text)

    conn.commit()
    add_to_delta_index(new_ids, new_texts)

    print(f"[ingest] {fp.name}: {len(chunks)} chunks (updated)")
    return len(chunks)

def delete_paths(paths: List[Path]) -> None:
    conn = connect(DB_PATH)
    ensure_schema(conn)

    for p in paths:
        row = get_document(conn, str(p))
        if not row:
            print(f"[delete] not found in db: {p}")
            continue
        doc_id = int(row[0])
        mark_chunks_deleted_for_doc(conn, doc_id)
        mark_document_deleted(conn, doc_id)
        conn.commit()
        print(f"[delete] marked deleted: {p}")

    conn.close()

def sync_folder(folder: Path, force: bool = False) -> None:
    conn = connect(DB_PATH)
    ensure_schema(conn)

    files = list(iter_documents(folder))
    print(f"[sync] found {len(files)} files in {folder}")

    file_set = set(str(p) for p in files)

    # raw 不存在但 DB 里存在 -> 标记删除
    rows = conn.execute("SELECT id, path FROM documents WHERE is_deleted=0").fetchall()
    for doc_id, path in rows:
        if path not in file_set:
            mark_chunks_deleted_for_doc(conn, int(doc_id))
            mark_document_deleted(conn, int(doc_id))
    conn.commit()

    changed = 0
    for fp in files:
        changed += _ingest_one(conn, fp, force=force)

    conn.close()
    print(f"[sync] done. changed_chunks={changed}. db={DB_PATH}")

def compact_rebuild_index() -> None:
    build_index()
    print("[compact] base index rebuilt and delta cleared.")

def main():
    parser = argparse.ArgumentParser(prog="python -m app.ingest.ingest")
    sub = parser.add_subparsers(dest="cmd")

    p_sync = sub.add_parser("sync", help="sync raw folder incrementally (default)")
    p_sync.add_argument("--folder", type=str, default=str(RAW_DIR))
    p_sync.add_argument("--force", action="store_true")

    p_add = sub.add_parser("add", help="add/update specific files")
    p_add.add_argument("paths", nargs="+")
    p_add.add_argument("--force", action="store_true")

    p_del = sub.add_parser("delete", help="delete specific files (soft delete)")
    p_del.add_argument("paths", nargs="+")

    sub.add_parser("compact", help="rebuild base index from active chunks and clear delta")

    args = parser.parse_args()

    if args.cmd in (None, "sync"):
        folder = Path(getattr(args, "folder", str(RAW_DIR)))
        force = bool(getattr(args, "force", False))
        sync_folder(folder, force=force)
        return

    if args.cmd == "add":
        conn = connect(DB_PATH)
        ensure_schema(conn)
        for p in [Path(x) for x in args.paths]:
            _ingest_one(conn, p, force=args.force)
        conn.close()
        return

    if args.cmd == "delete":
        delete_paths([Path(x) for x in args.paths])
        return

    if args.cmd == "compact":
        compact_rebuild_index()
        return

if __name__ == "__main__":
    main()
