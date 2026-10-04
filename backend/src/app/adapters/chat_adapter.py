from __future__ import annotations

from typing import Any, TYPE_CHECKING

from src.utils.types import ChatDetail, ChatMessage, ChatSummary, ChatTurnResponse, QueryResponse

from ..exceptions import ChatNotFound, MessageNotFound, ServiceUnavailable

if TYPE_CHECKING:
    from ..factory import ApplicationServiceFactory


class ChatAdapter:
    def __init__(self, services: ApplicationServiceFactory):
        self.services = services

    def list_chats(self, user_id: str) -> list[dict[str, Any]]:
        return self.services.get_chat_repo().list_chats(user_id)

    def create_chat(self, user_id: str, title: str | None) -> dict[str, Any]:
        return self.services.get_chat_repo().create_chat(user_id, title)

    def get_chat(self, chat_id: str, user_id: str) -> ChatDetail:
        chat_repo = self.services.get_chat_repo()
        chat = chat_repo.get_chat(chat_id, user_id)
        if not chat:
            raise ChatNotFound("Chat not found.")
        return ChatDetail(
            chat=ChatSummary(**chat),
            messages=[ChatMessage(**m) for m in chat_repo.list_messages(chat_id, user_id)],
        )

    def query_in_chat(self, chat_id: str, user_id: str, question: str) -> ChatTurnResponse:
        chat_repo = self.services.get_chat_repo()
        if not chat_repo.get_chat(chat_id, user_id):
            raise ChatNotFound("Chat not found.")
        history = chat_repo.list_messages(chat_id, user_id)
        # Commit the user's turn before calling the model or analytics database.
        # A downstream outage therefore cannot erase the submitted question.
        user_message = chat_repo.add_message(chat_id, user_id, "user", question)
        try:
            result = QueryResponse.from_pipeline_state(self.services.get_pipeline().run(question, history=history))
        except ServiceUnavailable as exc:
            # Kept identical to the old HTTPException text, which rendered as "503: <detail>"
            result = QueryResponse(status="error", message=f"Could not process this message: 503: {exc}")
        except Exception as exc:
            result = QueryResponse(status="error", message=f"Could not process this message: {exc}")
        assistant_message = chat_repo.add_message(
            chat_id,
            user_id,
            "assistant",
            self._assistant_content(result),
            {"question": question, **result.model_dump()},
        )
        return ChatTurnResponse(
            user_message=ChatMessage(**user_message),
            assistant_message=ChatMessage(**assistant_message),
            result=result,
        )

    def save_feedback(self, chat_id: str, user_id: str, message_id: str, rating: str,
                      comment: str | None) -> dict[str, Any]:
        saved = self.services.get_chat_repo().save_feedback(chat_id, user_id, message_id, rating, comment)
        if not saved:
            raise MessageNotFound("Assistant message not found.")
        return saved

    @staticmethod
    def _assistant_content(result: QueryResponse) -> str:
        if result.status == "complete":
            return f"Query returned {result.row_count}{' or more' if result.truncated else ''} rows."
        return result.message or result.status.replace("_", " ").capitalize()
