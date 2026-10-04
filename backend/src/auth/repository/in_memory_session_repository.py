"""Short-lived in-memory bearer sessions.

This is intended for a private demo. Email is an identity label, not proof of
identity; there is no password or email verification.
"""
from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

from src.app.ports import SessionRepositoryInterface

if TYPE_CHECKING:
    from src.utils.types import AuthenticatedUser

SESSION_TTL_SECONDS = 24 * 60 * 60


class InMemorySessionRepository(SessionRepositoryInterface):
    def __init__(self, ttl_seconds: int = SESSION_TTL_SECONDS):
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._sessions: dict[str, tuple[AuthenticatedUser, float]] = {}

    def save(self, token: str, user: AuthenticatedUser) -> None:
        expires_at = time.monotonic() + self._ttl_seconds
        with self._lock:
            now = time.monotonic()
            expired = [key for key, (_, expiry) in self._sessions.items() if expiry <= now]
            for key in expired:
                self._sessions.pop(key, None)
            self._sessions[token] = (user, expires_at)

    def get(self, token: str) -> AuthenticatedUser | None:
        with self._lock:
            session = self._sessions.get(token)
            if session and session[1] > time.monotonic():
                return session[0]
            self._sessions.pop(token, None)
        return None

    def delete(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)
