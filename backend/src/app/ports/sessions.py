from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.types import AuthenticatedUser


class SessionRepositoryInterface(ABC):
    @abstractmethod
    def save(self, token: str, user: AuthenticatedUser) -> None:
        ...

    @abstractmethod
    def get(self, token: str) -> AuthenticatedUser | None:
        ...

    @abstractmethod
    def delete(self, token: str) -> None:
        ...
