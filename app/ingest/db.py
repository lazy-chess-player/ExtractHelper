from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Optional

# 只建表，不建依赖新列的索引（索引在 ensure_schema 末尾创建）
SCHEMA_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT UNIQUE NOT NULL,
  doc_type TEXT NOT NULL,

  file_hash TEXT,
  file_mtime REAL,
  file_size INTEGER,

  is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id INTEGER NOT NULL,
  chunk_index INTEGER NOT NULL,
  page INTEGER,
  content TEXT NOT NULL,

  content_hash TEXT,
  is_deleted INTEGER NOT NULL DEFAULT 0,

  FOREIGN KEY(doc_id) REFERENCES documents(id)
);
"""

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_active ON chunks(is_deleted, id);
CREATE INDEX IF NOT EXISTS idx_documents_active ON documents(is_deleted, id);
"""

def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def _col_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)

def _add_column(conn: sqlite3.Connection, table: str, col: str, ddl: str) -> None:
    # SQLite ADD COLUMN 没有 IF NOT EXISTS，所以用 PRAGMA 先判断
    if _col_exists(conn, table, col):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")

def ensure_schema(conn: sqlite3.Connection) -> None:
    # 1) 先保证表存在（对旧库不会改已有表结构）
    conn.executescript(SCHEMA_TABLES_SQL)

    # 2) 再对旧库补齐新列（必须在创建依赖列的索引之前）
    # documents
    _add_column(conn, "documents", "file_hash", "TEXT")
    _add_column(conn, "documents", "file_mtime", "REAL")
    _add_column(conn, "documents", "file_size", "INTEGER")
    _add_column(conn, "documents", "is_deleted", "INTEGER NOT NULL DEFAULT 0")

    # chunks
    _add_column(conn, "chunks", "content_hash", "TEXT")
    _add_column(conn, "chunks", "is_deleted", "INTEGER NOT NULL DEFAULT 0")

    conn.commit()

    # 3) 最后再创建索引（现在 is_deleted 一定存在，不会再报 no such column）
    conn.executescript(INDEXES_SQL)
    conn.commit()

# 兼容旧代码：你原来叫 init_db
def init_db(conn: sqlite3.Connection) -> None:
    ensure_schema(conn)

def get_document(conn: sqlite3.Connection, path: str):
    return conn.execute(
        """
        SELECT id, doc_type, file_hash, file_mtime, file_size, is_deleted
        FROM documents
        WHERE path=?
        """,
        (path,),
    ).fetchone()

def upsert_document(
    conn: sqlite3.Connection,
    path: str,
    doc_type: str,
    file_hash: Optional[str] = None,
    file_mtime: Optional[float] = None,
    file_size: Optional[int] = None,
) -> int:
    conn.execute(
        """
        INSERT INTO documents(path, doc_type, file_hash, file_mtime, file_size, is_deleted)
        VALUES(?, ?, ?, ?, ?, 0)
        ON CONFLICT(path) DO UPDATE SET
          doc_type=excluded.doc_type,
          file_hash=excluded.file_hash,
          file_mtime=excluded.file_mtime,
          file_size=excluded.file_size,
          is_deleted=0
        """,
        (path, doc_type, file_hash, file_mtime, file_size),
    )
    row = conn.execute("SELECT id FROM documents WHERE path=?", (path,)).fetchone()
    assert row is not None
    return int(row[0])

def mark_document_deleted(conn: sqlite3.Connection, doc_id: int) -> None:
    conn.execute("UPDATE documents SET is_deleted=1 WHERE id=?", (doc_id,))

def mark_chunks_deleted_for_doc(conn: sqlite3.Connection, doc_id: int) -> None:
    conn.execute(
        "UPDATE chunks SET is_deleted=1 WHERE doc_id=? AND is_deleted=0",
        (doc_id,),
    )

# 兼容旧代码名字：clear_chunks_for_doc（现在默认软删除）
def clear_chunks_for_doc(conn: sqlite3.Connection, doc_id: int) -> None:
    mark_chunks_deleted_for_doc(conn, doc_id)

def _hash_text(t: str) -> str:
    h = hashlib.sha256()
    h.update((t or "").encode("utf-8", errors="ignore"))
    return h.hexdigest()

def insert_chunk(
    conn: sqlite3.Connection,
    doc_id: int,
    chunk_index: int,
    content: str,
    page: Optional[int],
) -> int:
    chash = _hash_text(content)
    cur = conn.execute(
        """
        INSERT INTO chunks(doc_id, chunk_index, page, content, content_hash, is_deleted)
        VALUES(?, ?, ?, ?, ?, 0)
        """,
        (doc_id, chunk_index, page, content, chash),
    )
    return int(cur.lastrowid)
