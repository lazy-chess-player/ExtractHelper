from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT UNIQUE NOT NULL,
  doc_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id INTEGER NOT NULL,
  chunk_index INTEGER NOT NULL,
  page INTEGER,
  content TEXT NOT NULL,
  FOREIGN KEY(doc_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
"""

def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()

def upsert_document(conn: sqlite3.Connection, path: str, doc_type: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO documents(path, doc_type) VALUES(?, ?)",
        (path, doc_type),
    )
    row = conn.execute("SELECT id FROM documents WHERE path=?", (path,)).fetchone()
    assert row is not None
    return int(row[0])

def clear_chunks_for_doc(conn: sqlite3.Connection, doc_id: int) -> None:
    conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))

def insert_chunk(conn: sqlite3.Connection, doc_id: int, chunk_index: int, content: str, page: Optional[int]) -> None:
    conn.execute(
        "INSERT INTO chunks(doc_id, chunk_index, page, content) VALUES(?, ?, ?, ?)",
        (doc_id, chunk_index, page, content),
    )
