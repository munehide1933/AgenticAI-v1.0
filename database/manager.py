import sqlite3
from contextlib import contextmanager

from config.settings import DATABASE_PATH


class DatabaseManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self._init_schema()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    language TEXT DEFAULT '中文',
                    status TEXT DEFAULT 'active',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    summary TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    language TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id)"
            )

            # 添加 summary 列（如果是旧数据库升级）
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN summary TEXT")
                print("✓ 已添加 summary 列到 sessions 表")
            except sqlite3.OperationalError:
                # 列已存在，忽略
                pass


db = DatabaseManager()
