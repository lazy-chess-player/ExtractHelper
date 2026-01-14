from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import DB_PATH, RAW_DIR
from app.ingest.ingest import (
    sync_folder,
    delete_paths,
    compact_rebuild_index,
)
from app.retrieval.build_index import build_index
from app.retrieval.retrieve import retrieve_evidence
from app.rag.ask import create_llm, answer_once
from app.chat_manager import ChatManager
from app.ingest.db import connect


class KnowledgeBaseManager:
    """
    知识库管理服务
    负责文档的增删改、同步以及索引维护。
    """
    def __init__(self, db_path: Path = DB_PATH, raw_dir: Path = RAW_DIR) -> None:
        self.db_path = Path(db_path)
        self.raw_dir = Path(raw_dir)

    def sync_folder(self, folder: Optional[Path] = None, force: bool = False) -> None:
        """
        同步文件夹内容到知识库。
        1. 扫描文件夹中的所有支持文档。
        2. 将新增/修改的文档入库（Chunking -> SQLite -> Delta Index）。
        3. 标记已删除的文档为软删除。
        
        :param folder: 目标文件夹，默认为 RAW_DIR
        :param force: 是否强制重新处理所有文件（忽略修改时间检查）
        """
        target = Path(folder) if folder is not None else self.raw_dir
        sync_folder(target, force=force)

    def add_files(self, paths: List[Path], force: bool = False) -> None:
        """
        将指定文件列表加入知识库。
        
        :param paths: 文件路径列表
        :param force: 是否强制更新
        """
        from app.ingest.ingest import _ingest_one, connect, ensure_schema

        conn = connect(self.db_path)
        ensure_schema(conn)
        try:
            for p in paths:
                _ingest_one(conn, Path(p), force=force)
        finally:
            conn.close()

    def delete_files(self, paths: List[Path]) -> None:
        """
        从知识库中（软）删除指定文件。
        标记 is_deleted=1，下次 rebuild index 时会物理清除。
        
        :param paths: 要删除的文件路径列表
        """
        delete_paths([Path(p) for p in paths])

    def rebuild_index(self, top_n: Optional[int] = None) -> None:
        """
        全量重建向量索引。
        读取所有 active chunks，生成新的 Base Index，并清空 Delta Index。
        
        :param top_n: 仅索引前 N 个 chunk（用于测试）
        """
        build_index(top_n=top_n)

    def compact(self) -> None:
        """
        压缩整理。
        当前等同于 rebuild_index，用于清理软删除留下的空洞。
        """
        compact_rebuild_index()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息。
        :return: 包含 documents 和 chunks 数量的字典
        """
        from app.ingest.db import connect
        conn = connect(self.db_path)
        try:
            doc_count = conn.execute("SELECT COUNT(*) FROM documents WHERE is_deleted=0").fetchone()[0]
            chunk_count = conn.execute("SELECT COUNT(*) FROM chunks WHERE is_deleted=0").fetchone()[0]
            return {"documents": doc_count, "chunks": chunk_count}
        except Exception:
            return {"documents": 0, "chunks": 0}
        finally:
            conn.close()


class RAGService:
    """
    RAG 问答服务
    负责管理 LLM 实例、执行向量检索和生成回答。
    """
    def __init__(self) -> None:
        self._llm = None

    @property
    def llm(self):
        """延迟加载 LLM 实例"""
        if self._llm is None:
            self._llm = create_llm()
        return self._llm

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        执行纯检索。
        :param query: 查询语句
        :param top_k: 返回结果数量
        :return: 证据列表
        """
        return retrieve_evidence(query, top_k=top_k)

    def ask(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, str]]]:
        """
        执行 RAG 问答（支持多轮对话）。
        
        :param question: 用户问题
        :param history: 对话历史 [{"role": "user", "content": ...}, ...]
        :param top_k: 检索证据数量
        :return: (回答文本, 证据列表, 新的对话历史)
        """
        answer, evidence = answer_once(self.llm, question, history=history or [], top_k=top_k)
        new_history = list(history or [])
        new_history.append({"role": "user", "content": question})
        new_history.append({"role": "assistant", "content": answer})
        return answer, evidence, new_history


class ExtractHelperApp:
    """
    应用核心入口类
    组合了 KnowledgeBaseManager 和 RAGService，作为 GUI 或 API 的统一后端。
    """
    def __init__(self, db_path: Path = DB_PATH, raw_dir: Path = RAW_DIR) -> None:
        self.kb = KnowledgeBaseManager(db_path=db_path, raw_dir=raw_dir)
        self.rag = RAGService()
        
        # 初始化 ChatManager
        self.db_conn = connect(db_path)
        self.chat_manager = ChatManager(self.db_conn)
