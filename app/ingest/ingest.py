from __future__ import annotations
from pathlib import Path

from app.config import CHUNK_OVERLAP, CHUNK_SIZE, DB_PATH, RAW_DIR
from app.ingest.loaders import iter_documents, load_document
from app.ingest.chunker import simple_chunk
from app.ingest.db import connect, init_db, upsert_document, clear_chunks_for_doc, insert_chunk


def ingest_folder(folder: Path) -> None:
    conn = connect(DB_PATH)
    init_db(conn)

    files = list(iter_documents(folder))
    print(f"[ingest] found {len(files)} files in {folder}")

    # （可选）同步删除：raw 里不存在的文件，从数据库里删掉
    file_set = set(str(p) for p in files)
    rows = conn.execute("SELECT id, path FROM documents").fetchall()
    for doc_id, path in rows:
        if path not in file_set:
            conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()

    for fp in files:
        doc = load_document(fp)
        doc_id = upsert_document(conn, str(fp), doc.doc_type)

        # 先简单：每次入库都清空旧 chunk 再写入（后面我们会升级为增量更新）
        clear_chunks_for_doc(conn, doc_id)

        chunks = simple_chunk(doc.text, CHUNK_SIZE, CHUNK_OVERLAP)
        for ch in chunks:
            insert_chunk(conn, doc_id, ch.idx, ch.text, ch.page)

        conn.commit()
        print(f"[ingest] {fp.name}: {len(chunks)} chunks")

    conn.close()
    print(f"[ingest] done. db = {DB_PATH}")



if __name__ == "__main__":
    ingest_folder(RAW_DIR)
