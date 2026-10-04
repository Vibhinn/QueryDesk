from __future__ import annotations

from typing import Any, TypedDict


class AuthenticatedUser(TypedDict):
    user_id: str
    email: str
    preferred_username: str


class PipelineState(TypedDict, total=False):
    question: str
    resolved_question: str
    history: list[dict[str, Any]]
    stages: list[str]
    status: str
    message: str
    intent: str
    scope: dict[str, Any]
    suggestions: list[str]
    context: str
    sql: str
    validated_sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
