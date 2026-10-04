"""Simple email identity with short-lived in-memory bearer sessions.

This is intended for a private demo. Email is an identity label, not proof of
identity; there is no password or email verification.
"""
from __future__ import annotations

import secrets
import threading
import time
import uuid
from typing import TypedDict

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class AuthenticatedUser(TypedDict):
    user_id: str
    email: str
    preferred_username: str


_bearer = HTTPBearer(auto_error=False)
_session_lock = threading.Lock()
_sessions: dict[str, tuple[AuthenticatedUser, float]] = {}
_session_ttl_seconds = 24 * 60 * 60


def create_session(email: str) -> tuple[str, AuthenticatedUser]:
    normalized_email = email.strip().casefold()
    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"querydesk-user:{normalized_email}"))
    username = normalized_email.partition("@")[0]
    user: AuthenticatedUser = {
        "user_id": user_id,
        "email": normalized_email,
        "preferred_username": username,
    }
    token = secrets.token_urlsafe(32)
    expires_at = time.monotonic() + _session_ttl_seconds
    with _session_lock:
        now = time.monotonic()
        expired = [key for key, (_, expiry) in _sessions.items() if expiry <= now]
        for key in expired:
            _sessions.pop(key, None)
        _sessions[token] = (user, expires_at)
    return token, user


def revoke_session(token: str) -> None:
    with _session_lock:
        _sessions.pop(token, None)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Enter your email to sign in.")
    token = credentials.credentials
    with _session_lock:
        session = _sessions.get(token)
        if session and session[1] > time.monotonic():
            return session[0]
        _sessions.pop(token, None)
    raise HTTPException(status_code=401, detail="Your demo session ended. Sign in again.")
