from __future__ import annotations

import secrets
import uuid
from typing import Any, TYPE_CHECKING

from ..exceptions import NotAuthenticated

if TYPE_CHECKING:
    from ..ports import SessionRepositoryInterface
    from src.utils.types import AuthenticatedUser


class AuthAdapter:
    def __init__(self, session_repo: SessionRepositoryInterface):
        self.session_repo = session_repo

    def login(self, email: str) -> dict[str, Any]:
        token, user = self.create_session(email)
        return {"access_token": token, "token_type": "bearer", "user": user}

    def create_session(self, email: str) -> tuple[str, AuthenticatedUser]:
        normalized_email = email.strip().casefold()
        user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"querydesk-user:{normalized_email}"))
        username = normalized_email.partition("@")[0]
        user: AuthenticatedUser = {
            "user_id": user_id,
            "email": normalized_email,
            "preferred_username": username,
        }
        token = secrets.token_urlsafe(32)
        self.session_repo.save(token, user)
        return token, user

    def authenticate(self, scheme: str | None, token: str | None) -> AuthenticatedUser:
        if scheme is None or scheme.lower() != "bearer":
            raise NotAuthenticated("Enter your email to sign in.")
        user = self.session_repo.get(token)
        if user is None:
            raise NotAuthenticated("Your demo session ended. Sign in again.")
        return user

    def logout(self, authorization: str | None) -> None:
        if authorization:
            self.session_repo.delete(authorization.partition(" ")[2])
