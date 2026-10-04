from typing import Any, Literal
from datetime import datetime

from pydantic import BaseModel, Field

from .dtypes import PipelineState


class QueryResponse(BaseModel):
    status: str
    message: str = ""
    intent: str | None = None
    resolved_question: str | None = None
    suggestions: list[str] = Field(default_factory=list)
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    stages: list[str] = Field(default_factory=list)

    @classmethod
    def from_pipeline_state(cls, result: PipelineState) -> "QueryResponse":
        return cls(
            status=result.get("status", "error"),
            message=result.get("message", ""),
            intent=result.get("intent"),
            resolved_question=result.get("resolved_question"),
            suggestions=result.get("suggestions", []),
            sql=result.get("validated_sql") or result.get("sql"),
            columns=result.get("columns", []),
            rows=result.get("rows", []),
            row_count=result.get("row_count", 0),
            truncated=result.get("truncated", False),
            stages=result.get("stages", []),
        )


class ChatSummary(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageFeedback(BaseModel):
    rating: Literal["up", "down"]
    comment: str | None = None


class ChatMessage(BaseModel):
    id: str
    chat_id: str
    user_id: str
    role: str
    content: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    feedback: MessageFeedback | None = None


class ChatDetail(BaseModel):
    chat: ChatSummary
    messages: list[ChatMessage]


class ChatTurnResponse(BaseModel):
    user_message: ChatMessage
    assistant_message: ChatMessage
    result: QueryResponse


class SummarizeResponse(BaseModel):
    summary: str
