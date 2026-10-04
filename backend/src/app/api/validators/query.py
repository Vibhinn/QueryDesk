from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class SummarizeRequest(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
