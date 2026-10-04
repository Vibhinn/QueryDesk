from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from .chat_store import ChatStore
from .auth import AuthenticatedUser, get_current_user
from .config import get_settings
from .llm import get_chat_model
from .models import (
    ChatCreateRequest,
    ChatDetail,
    ChatMessage,
    ChatSummary,
    ChatTurnResponse,
    FeedbackRequest,
    MessageFeedback,
    QueryRequest,
    QueryResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from .pipeline import NL2SQLPipeline, _text
from .schema_context import SchemaContext

settings = get_settings()
app = FastAPI(title="Schema-grounded NL2SQL", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

try:
    schema = SchemaContext(settings.schema_path)
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    pipeline = NL2SQLPipeline(schema, engine)
except Exception as exc:
    schema = None
    engine = None
    pipeline = None
    startup_error = str(exc)
else:
    startup_error = ""

try:
    app_engine = create_engine(settings.app_database_url, pool_pre_ping=True)
    chat_store = ChatStore(app_engine)
    chat_store_error = ""
except Exception as exc:
    app_engine = None
    chat_store = None
    chat_store_error = str(exc)


def _response_from_state(result: dict[str, Any]) -> QueryResponse:
    return QueryResponse(
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


def _require_store() -> ChatStore:
    if chat_store is None:
        raise HTTPException(status_code=503, detail=f"Chat history is unavailable: {chat_store_error}")
    return chat_store


def _require_pipeline() -> NL2SQLPipeline:
    if pipeline is None:
        raise HTTPException(status_code=503, detail=f"NL2SQL is not configured: {startup_error}")
    return pipeline


def _assistant_content(result: QueryResponse) -> str:
    if result.status == "complete":
        return f"Query returned {result.row_count}{' or more' if result.truncated else ''} rows."
    return result.message or result.status.replace("_", " ").capitalize()


def _summarize(question: str, sql: str, columns: list[str], rows: list[dict[str, Any]]) -> str:
    response = get_chat_model().invoke([
        ("system", "Summarize the query result briefly in plain language. State the main finding and mention the SQL's purpose. Do not claim findings absent from the data. If there are no rows, say so. Keep it to 2-4 sentences."),
        ("human", f"Question: {question}\nSQL:\n{sql}\nColumns: {columns}\nSample result rows (at most 20): {rows[:20]}"),
    ])
    return _text(response)


@app.get("/api/health")
def health():
    return {
        "status": "ok" if pipeline else "configuration_error",
        "schema_loaded": schema is not None,
        "chat_store_loaded": chat_store is not None,
        "error": startup_error or chat_store_error,
    }


@app.post("/api/query", response_model=QueryResponse)
def query(request: QueryRequest, _user: AuthenticatedUser = Depends(get_current_user)):
    result = _require_pipeline().run(request.question)
    return _response_from_state(result)


@app.get("/api/chats", response_model=list[ChatSummary])
def list_chats(user: AuthenticatedUser = Depends(get_current_user)):
    return _require_store().list_chats(user["user_id"])


@app.post("/api/chats", response_model=ChatSummary)
def create_chat(request: ChatCreateRequest, user: AuthenticatedUser = Depends(get_current_user)):
    return _require_store().create_chat(user["user_id"], request.title)


@app.get("/api/chats/{chat_id}", response_model=ChatDetail)
def get_chat(chat_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    store = _require_store()
    chat = store.get_chat(chat_id, user["user_id"])
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return ChatDetail(
        chat=ChatSummary(**chat),
        messages=[ChatMessage(**m) for m in store.list_messages(chat_id, user["user_id"])],
    )


@app.post("/api/chats/{chat_id}/query", response_model=ChatTurnResponse)
def query_in_chat(
    chat_id: str,
    request: QueryRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    store = _require_store()
    user_id = user["user_id"]
    if not store.get_chat(chat_id, user_id):
        raise HTTPException(status_code=404, detail="Chat not found.")
    history = store.list_messages(chat_id, user_id)
    # Commit the user's turn before calling the model or analytics database.
    # A downstream outage therefore cannot erase the submitted question.
    user_message = store.add_message(chat_id, user_id, "user", request.question)
    try:
        result = _response_from_state(_require_pipeline().run(request.question, history=history))
    except Exception as exc:
        result = QueryResponse(status="error", message=f"Could not process this message: {exc}")
    assistant_message = store.add_message(
        chat_id,
        user_id,
        "assistant",
        _assistant_content(result),
        {"question": request.question, **result.model_dump()},
    )
    return ChatTurnResponse(
        user_message=ChatMessage(**user_message),
        assistant_message=ChatMessage(**assistant_message),
        result=result,
    )


@app.post("/api/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest, _user: AuthenticatedUser = Depends(get_current_user)):
    try:
        return SummarizeResponse(summary=_summarize(request.question, request.sql, request.columns, request.rows))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Summary generation failed: {exc}") from exc


@app.post("/api/chats/{chat_id}/messages/{message_id}/summarize", response_model=SummarizeResponse)
def summarize_chat_message(
    chat_id: str,
    message_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    store = _require_store()
    user_id = user["user_id"]
    if not store.get_chat(chat_id, user_id):
        raise HTTPException(status_code=404, detail="Chat not found.")
    message = next((m for m in store.list_messages(chat_id, user_id) if m["id"] == message_id), None)
    if not message or message["role"] != "assistant":
        raise HTTPException(status_code=404, detail="Assistant result not found.")
    payload = message.get("payload", {})
    if not payload.get("sql"):
        raise HTTPException(status_code=400, detail="This message has no SQL result to summarize.")
    try:
        summary = _summarize(
            str(payload.get("question", "")),
            str(payload["sql"]),
            payload.get("columns", []),
            payload.get("rows", []),
        )
        store.update_message_payload(chat_id, user_id, message_id, {"summary": summary})
        return SummarizeResponse(summary=summary)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Summary generation failed: {exc}") from exc


@app.post(
    "/api/chats/{chat_id}/messages/{message_id}/feedback",
    response_model=MessageFeedback,
)
def submit_message_feedback(
    chat_id: str,
    message_id: str,
    request: FeedbackRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    store = _require_store()
    saved = store.save_feedback(
        chat_id,
        user["user_id"],
        message_id,
        request.rating,
        request.comment,
    )
    if not saved:
        raise HTTPException(status_code=404, detail="Assistant message not found.")
    return saved
