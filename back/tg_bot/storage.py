"""Локальное хранилище привязки Telegram ↔ аккаунт StudyHub (SQLite)."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).resolve().parent / "tg_bot_data.sqlite"


class Storage:
    def __init__(self, path: Path = DB_PATH) -> None:
        self._path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tg_sessions (
                chat_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                login TEXT NOT NULL,
                name TEXT,
                last_notif_id INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_tg_sessions_user ON tg_sessions(user_id);
            """
        )
        self._conn.commit()

    def get_session(self, chat_id: int) -> Optional[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT chat_id, user_id, role, login, name, last_notif_id FROM tg_sessions WHERE chat_id = ?",
            (chat_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def save_session(
        self,
        chat_id: int,
        user_id: int,
        role: str,
        login: str,
        name: str,
        last_notif_id: int = 0,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO tg_sessions (chat_id, user_id, role, login, name, last_notif_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                user_id = excluded.user_id,
                role = excluded.role,
                login = excluded.login,
                name = excluded.name,
                last_notif_id = excluded.last_notif_id
            """,
            (chat_id, user_id, role, login, name, last_notif_id),
        )
        self._conn.commit()

    def update_last_notif(self, chat_id: int, last_id: int) -> None:
        self._conn.execute(
            "UPDATE tg_sessions SET last_notif_id = ? WHERE chat_id = ?",
            (last_id, chat_id),
        )
        self._conn.commit()

    def update_last_notif_if_greater(self, chat_id: int, last_id: int) -> None:
        self._conn.execute(
            "UPDATE tg_sessions SET last_notif_id = ? WHERE chat_id = ? AND last_notif_id < ?",
            (last_id, chat_id, last_id),
        )
        self._conn.commit()

    def delete_session(self, chat_id: int) -> None:
        self._conn.execute("DELETE FROM tg_sessions WHERE chat_id = ?", (chat_id,))
        self._conn.commit()

    def all_student_sessions(self) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT chat_id, user_id, role, login, name, last_notif_id FROM tg_sessions WHERE role = 'student'"
        )
        return [dict(r) for r in cur.fetchall()]
