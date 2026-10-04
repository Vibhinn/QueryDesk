"""SQLite-backed conversation history, kept separate from the analytics database."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ChatStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_chat_created
                    ON messages(chat_id, created_at);
                """
            )

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_chat(self, title: str | None = None) -> dict[str, Any]:
        chat_id, now = str(uuid.uuid4()), self._now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO chats(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (chat_id, title or "New chat", now, now),
            )
        return self.get_chat(chat_id)

    def list_chats(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM chats ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def get_chat(self, chat_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
        return dict(row) if row else None

    def list_messages(self, chat_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at, rowid", (chat_id,)
            ).fetchall()
        result = []
        for row in rows:
            message = dict(row)
            message["payload"] = json.loads(message.pop("payload_json") or "{}")
            result.append(message)
        return result

    def add_message(self, chat_id: str, role: str, content: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        message_id, now = str(uuid.uuid4()), self._now()
        with self._connect() as connection:
            existing = connection.execute("SELECT title FROM chats WHERE id = ?", (chat_id,)).fetchone()
            if not existing:
                raise KeyError(chat_id)
            connection.execute(
                "INSERT INTO messages(id, chat_id, role, content, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (message_id, chat_id, role, content, json.dumps(payload or {}, ensure_ascii=False), now),
            )
            if role == "user" and existing["title"] == "New chat":
                title = " ".join(content.split())[:60] or "New chat"
                connection.execute("UPDATE chats SET title = ?, updated_at = ? WHERE id = ?", (title, now, chat_id))
            else:
                connection.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))
        return {
            "id": message_id,
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "payload": payload or {},
            "created_at": now,
        }

    def update_message_payload(self, chat_id: str, message_id: str, additions: dict[str, Any]) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM messages WHERE id = ? AND chat_id = ?", (message_id, chat_id)
            ).fetchone()
            if not row:
                return None
            payload = json.loads(row["payload_json"] or "{}")
            payload.update(additions)
            connection.execute(
                "UPDATE messages SET payload_json = ? WHERE id = ?",
                (json.dumps(payload, ensure_ascii=False), message_id),
            )
            updated = dict(row)
            updated["payload"] = payload
            updated.pop("payload_json", None)
            return updated
