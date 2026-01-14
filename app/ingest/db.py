from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Optional

"""
数据库层 (SQLite)
负责管理 documents 和 chunks 表的 Schema 定义、连接创建以及底层 CRUD 操作。
"""

# 表结构定义
# documents: 存储文件元数据（路径、hash、修改时间等）
# chunks: 存储切分后的文本片段
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

# 索引定义
INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_active ON chunks(is_deleted, id);
CREATE INDEX IF NOT EXISTS idx_documents_active ON documents(is_deleted, id);
"""

def connect(db_path: Path) -> sqlite3.Connection:
    """创建并返回 SQLite 连接，启用 WAL 模式"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def _col_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    """检查表中是否存在指定列"""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)

def _add_column(conn: sqlite3.Connection, table: str, col: str, ddl: str) -> None:
    """幂等地添加列"""
    if _col_exists(conn, table, col):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")

def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    确保数据库 Schema 是最新的。
    包含表创建、新列补齐（Migration）和索引创建。
    """
    # 1) 先保证表存在
    conn.executescript(SCHEMA_TABLES_SQL)

    # 2) 补齐后续版本新增的列
    # documents
    _add_column(conn, "documents", "file_hash", "TEXT")
    _add_column(conn, "documents", "file_mtime", "REAL")
    _add_column(conn, "documents", "file_size", "INTEGER")
    _add_column(conn, "documents", "is_deleted", "INTEGER NOT NULL DEFAULT 0")

    # chunks
    _add_column(conn, "chunks", "content_hash", "TEXT")
    _add_column(conn, "chunks", "is_deleted", "INTEGER NOT NULL DEFAULT 0")

    conn.commit()

    # 3) 创建索引
    conn.executescript(INDEXES_SQL)
    conn.commit()

# 兼容旧代码别名
def init_db(conn: sqlite3.Connection) -> None:
    ensure_schema(conn)

def get_document(conn: sqlite3.Connection, path: str):
    """根据路径查询文档记录"""
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
    """
    插入或更新文档记录。
    如果路径已存在，则更新元数据并将 is_deleted 置为 0。
    """
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
    """软删除文档"""
    conn.execute("UPDATE documents SET is_deleted=1 WHERE id=?", (doc_id,))

def mark_chunks_deleted_for_doc(conn: sqlite3.Connection, doc_id: int) -> None:
    """软删除指定文档下的所有 chunks"""
    conn.execute(
        "UPDATE chunks SET is_deleted=1 WHERE doc_id=? AND is_deleted=0",
        (doc_id,),
    )

def clear_chunks_for_doc(conn: sqlite3.Connection, doc_id: int) -> None:
    """兼容别名：清除（软删除）文档 chunks"""
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
    """插入单个 chunk 记录"""
    chash = _hash_text(content)
    cur = conn.execute(
        """
        INSERT INTO chunks(doc_id, chunk_index, page, content, content_hash, is_deleted)
        VALUES(?, ?, ?, ?, ?, 0)
        """,
        (doc_id, chunk_index, page, content, chash),
    )
    return int(cur.lastrowid)
