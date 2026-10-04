from __future__ import annotations

import json
from typing import Any


def database_error_message(exc: Exception) -> str:
    details = str(exc).lower()
    if "statement timeout" in details or "query_canceled" in details or "canceling statement" in details:
        return "This query took too long to finish. Try narrowing the date range or adding a filter."
    if "could not connect" in details or "connection refused" in details or "connection is closed" in details:
        return "The database is temporarily unavailable. Please try again in a moment."
    return "The database couldn’t complete this query. Try adjusting the filters or rephrasing your request."


def parse_json_object(value: str) -> dict[str, Any]:
    value = value.strip()
    if value.startswith("```"):
        value = value.strip("`")
        if value.lower().startswith("json"):
            value = value[4:]
    start, end = value.find("{"), value.rfind("}")
    if start < 0 or end < start:
        raise ValueError("The configured model returned an invalid structured response.")
    return json.loads(value[start:end + 1])


def history_context(history: list[dict[str, Any]] | None) -> str:
    compact = []
    for message in (history or [])[-10:]:
        item: dict[str, Any] = {"role": message.get("role"), "content": message.get("content", "")}
        payload = message.get("payload") or {}
        if item["role"] == "assistant" and payload:
            item["result"] = {
                key: payload.get(key)
                for key in ("status", "intent", "resolved_question", "message", "sql", "columns", "suggestions")
                if payload.get(key) is not None
            }
            if payload.get("rows"):
                item["result"]["sample_rows"] = payload["rows"][:8]
        compact.append(item)
    return json.dumps(compact, ensure_ascii=False)[:12000]


def json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
