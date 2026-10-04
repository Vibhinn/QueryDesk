from __future__ import annotations

from typing import Any, TYPE_CHECKING

from src.utils.types import SummarizeResponse

from ..exceptions import ChatNotFound, MessageNotFound, NoSQLResultToSummarize, SummaryGenerationFailed

if TYPE_CHECKING:
    from ..factory import ApplicationServiceFactory
    from ..ports import LLMRepositoryInterface

SUMMARY_PROMPT = "Summarize the query result briefly in plain language. State the main finding and mention the SQL's purpose. Do not claim findings absent from the data. If there are no rows, say so. Keep it to 2-4 sentences."


class SummaryAdapter:
    def __init__(self, services: ApplicationServiceFactory, llm: LLMRepositoryInterface):
        self.services = services
        self.llm = llm

    def summarize(self, question: str, sql: str, columns: list[str], rows: list[dict[str, Any]]) -> SummarizeResponse:
        try:
            return SummarizeResponse(summary=self._summarize(question, sql, columns, rows))
        except Exception as exc:
            raise SummaryGenerationFailed(f"Summary generation failed: {exc}") from exc

    def summarize_chat_message(self, chat_id: str, message_id: str, user_id: str) -> SummarizeResponse:
        chat_repo = self.services.get_chat_repo()
        if not chat_repo.get_chat(chat_id, user_id):
            raise ChatNotFound("Chat not found.")
        message = next((m for m in chat_repo.list_messages(chat_id, user_id) if m["id"] == message_id), None)
        if not message or message["role"] != "assistant":
            raise MessageNotFound("Assistant result not found.")
        payload = message.get("payload", {})
        if not payload.get("sql"):
            raise NoSQLResultToSummarize("This message has no SQL result to summarize.")
        try:
            summary = self._summarize(
                str(payload.get("question", "")),
                str(payload["sql"]),
                payload.get("columns", []),
                payload.get("rows", []),
            )
            chat_repo.update_message_payload(chat_id, user_id, message_id, {"summary": summary})
            return SummarizeResponse(summary=summary)
        except Exception as exc:
            raise SummaryGenerationFailed(f"Summary generation failed: {exc}") from exc

    def _summarize(self, question: str, sql: str, columns: list[str], rows: list[dict[str, Any]]) -> str:
        return self.llm.invoke([
            ("system", SUMMARY_PROMPT),
            ("human", f"Question: {question}\nSQL:\n{sql}\nColumns: {columns}\nSample result rows (at most 20): {rows[:20]}"),
        ])
