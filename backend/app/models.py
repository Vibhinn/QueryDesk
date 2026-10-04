from typing import Any, Literal
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


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


class ChatCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)


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


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_downvote_comment(self):
        if self.rating == "down" and not (self.comment and self.comment.strip()):
            raise ValueError("Please add a short comment explaining your feedback.")
        return self


class ChatDetail(BaseModel):
    chat: ChatSummary
    messages: list[ChatMessage]


class ChatTurnResponse(BaseModel):
    user_message: ChatMessage
    assistant_message: ChatMessage
    result: QueryResponse


class SummarizeRequest(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]


class SummarizeResponse(BaseModel):
    summary: str
