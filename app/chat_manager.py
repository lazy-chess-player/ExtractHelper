import uuid
import json
import time
from typing import List, Dict, Optional
from app.ingest import db

class ChatManager:
    def __init__(self, conn):
        self.conn = conn
        # 确保表存在 (强制执行，防止新表未创建)
        db.ensure_schema(self.conn)

    def create_new_session(self, title: str = "New Chat") -> str:
        sid = str(uuid.uuid4())
        db.create_session(self.conn, sid, title, time.time())
        self.conn.commit()
        return sid

    def list_sessions(self):
        """返回按时间倒序的会话列表"""
        rows = db.list_sessions(self.conn)
        return [{"id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]

    def get_history(self, session_id: str):
        """获取会话的所有消息"""
        rows = db.get_messages(self.conn, session_id)
        history = []
        for r in rows:
            role, content, ev_json = r
            msg = {"role": role, "content": content}
            if ev_json:
                try:
                    msg["evidence"] = json.loads(ev_json)
                except:
                    pass
            history.append(msg)
        return history

    def add_user_message(self, session_id: str, content: str):
        mid = str(uuid.uuid4())
        db.add_message(self.conn, mid, session_id, "user", content, None, time.time())
        self.conn.commit()

    def add_ai_message(self, session_id: str, content: str, evidence: List[Dict]):
        mid = str(uuid.uuid4())
        ev_json = json.dumps(evidence) if evidence else None
        db.add_message(self.conn, mid, session_id, "assistant", content, ev_json, time.time())
        self.conn.commit()

    def update_title(self, session_id: str, title: str):
        db.update_session_title(self.conn, session_id, title)
        self.conn.commit()

    def delete_session(self, session_id: str):
        db.delete_session(self.conn, session_id)
        self.conn.commit()
