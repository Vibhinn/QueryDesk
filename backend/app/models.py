from typing import Any

from pydantic import BaseModel, Field


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
    title: str
    created_at: str
    updated_at: str


class ChatMessage(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


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
