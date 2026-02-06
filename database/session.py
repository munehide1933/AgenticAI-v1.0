import json
import time
import uuid
from typing import Any, Dict, List, Optional

from core.models import CodeArtifact
from utils.crypto import encryptor

from database.manager import db


class SessionManager:
    def create_session(self, title: str, domain: str, language: str = "中文") -> str:
        session_id = str(uuid.uuid4())
        now = time.time()

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, title, domain, language, created_at, updated_at, summary, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, title, domain, language, now, now, "", "active"),
            )
        return session_id

    def list_sessions(
        self, domain: Optional[str] = None, status: str = "active"
    ) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            if domain and domain != "all":
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE domain = ? AND status = ? ORDER BY updated_at DESC",
                    (domain, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE status = ? ORDER BY updated_at DESC",
                    (status,),
                ).fetchall()
        return [dict(row) for row in rows]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            return dict(row) if row else None

    def add_message(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None
    ):
        # 加密消息内容
        encrypted_content = encryptor.encrypt(content)
        encrypted_metadata = (
            encryptor.encrypt(json.dumps(metadata)) if metadata else None
        )

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, encrypted_content, encrypted_metadata, time.time()),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (time.time(), session_id),
            )

        # 自动更新会话摘要（仅在用户消息时，使用明文）
        if role == "user":
            self.update_session_summary(session_id, content)

    def get_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit),
            ).fetchall()

        # 解密消息内容
        messages = []
        for row in rows:
            msg = dict(row)
            msg["content"] = encryptor.decrypt(msg["content"])
            if msg.get("metadata"):
                try:
                    msg["metadata"] = json.loads(encryptor.decrypt(msg["metadata"]))
                except:
                    msg["metadata"] = None
            messages.append(msg)

        return messages

    def save_artifact(self, session_id: str, artifact: CodeArtifact):
        # 加密代码内容
        encrypted_code = encryptor.encrypt(artifact.code)
        encrypted_explanation = encryptor.encrypt(artifact.explanation)

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO artifacts (session_id, artifact_type, title, content, language, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    "code",
                    artifact.title,
                    encrypted_code,
                    artifact.language,
                    time.time(),
                ),
            )

    def update_session_summary(self, session_id: str, first_user_message: str = None):
        """自动生成会话摘要（基于第一条用户消息）"""
        try:
            if first_user_message:
                # 直接使用传入的明文消息
                summary = (
                    first_user_message[:60] + "..."
                    if len(first_user_message) > 60
                    else first_user_message
                )
            else:
                # 从数据库读取（需要解密）
                messages = self.get_messages(session_id, limit=1)
                if messages and messages[0]["role"] == "user":
                    first_msg = messages[0]["content"]
                    summary = (
                        first_msg[:60] + "..." if len(first_msg) > 60 else first_msg
                    )
                else:
                    return

            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE sessions SET summary = ? WHERE session_id = ?",
                    (summary, session_id),
                )
        except Exception as e:
            print(f"更新摘要失败: {e}")

    def delete_session(self, session_id: str):
        """逻辑删除会话（不删除数据库记录，仅标记为已删除）"""
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                ("deleted", time.time(), session_id),
            )


session_mgr = SessionManager()
