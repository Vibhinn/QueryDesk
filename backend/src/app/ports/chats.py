from abc import ABC, abstractmethod
from typing import Any


class ChatRepositoryInterface(ABC):
    @abstractmethod
    def create_chat(self, user_id: str, title: str | None = None) -> dict[str, Any]:
        ...

    @abstractmethod
    def list_chats(self, user_id: str) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_chat(self, chat_id: str, user_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def list_messages(self, chat_id: str, user_id: str) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def add_message(self, chat_id: str, user_id: str, role: str, content: str,
                    payload: dict[str, Any] | None = None) -> dict[str, Any]:
        ...

    @abstractmethod
    def update_message_payload(self, chat_id: str, user_id: str, message_id: str,
                               additions: dict[str, Any]) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def save_feedback(self, chat_id: str, user_id: str, message_id: str, rating: str,
                      comment: str | None) -> dict[str, Any] | None:
        ...
