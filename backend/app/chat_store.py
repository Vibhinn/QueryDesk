"""PostgreSQL persistence for user-owned conversations, messages, and feedback."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    JSON,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    and_,
    create_engine,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine


metadata = MetaData()

conversation = Table(
    "conversation",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(255), nullable=False, index=True),
    Column("title", String(120), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("id", "user_id", name="uq_conversation_id_user"),
    Index("ix_conversation_user_updated", "user_id", "updated_at"),
)

messages = Table(
    "messages",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("conversation_id", String(36), nullable=False),
    Column("user_id", String(255), nullable=False, index=True),
    Column("role", String(16), nullable=False),
    Column("content", Text, nullable=False),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
    ForeignKeyConstraint(
        ["conversation_id", "user_id"],
        ["conversation.id", "conversation.user_id"],
        ondelete="CASCADE",
        name="fk_messages_conversation_user",
    ),
    UniqueConstraint("id", "user_id", name="uq_messages_id_user"),
    Index("ix_messages_conversation_created", "conversation_id", "created_at"),
)

feedback = Table(
    "feedback",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("message_id", String(36), nullable=False),
    Column("user_id", String(255), nullable=False, index=True),
    Column("rating", String(8), nullable=False),
    Column("comment", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("rating IN ('up', 'down')", name="ck_feedback_rating"),
    CheckConstraint(
        "rating <> 'down' OR (comment IS NOT NULL AND length(trim(comment)) > 0)",
        name="ck_feedback_down_comment",
    ),
    ForeignKeyConstraint(
        ["message_id", "user_id"],
        ["messages.id", "messages.user_id"],
        ondelete="CASCADE",
        name="fk_feedback_message_user",
    ),
    UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChatStore:
    def __init__(self, engine: Engine):
        self.engine = engine
        metadata.create_all(engine)

    def create_chat(self, user_id: str, title: str | None = None) -> dict[str, Any]:
        now = _now()
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title or "New chat",
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(conversation.insert().values(**row))
        return row

    def list_chats(self, user_id: str) -> list[dict[str, Any]]:
        statement = (
            select(conversation)
            .where(conversation.c.user_id == user_id)
            .order_by(conversation.c.updated_at.desc())
        )
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(statement).mappings().all()]

    def get_chat(self, chat_id: str, user_id: str) -> dict[str, Any] | None:
        statement = select(conversation).where(
            and_(conversation.c.id == chat_id, conversation.c.user_id == user_id)
        )
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return dict(row) if row else None

    def list_messages(self, chat_id: str, user_id: str) -> list[dict[str, Any]]:
        statement = (
            select(
                messages,
                feedback.c.rating.label("feedback_rating"),
                feedback.c.comment.label("feedback_comment"),
            )
            .where(and_(messages.c.conversation_id == chat_id, messages.c.user_id == user_id))
            .outerjoin(
                feedback,
                and_(feedback.c.message_id == messages.c.id, feedback.c.user_id == user_id),
            )
            .order_by(messages.c.created_at, messages.c.id)
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        output = []
        for row in rows:
            item = {key: row[key] for key in messages.c.keys()}
            item["chat_id"] = item.pop("conversation_id")
            rating = row["feedback_rating"]
            item["feedback"] = (
                {"rating": rating, "comment": row["feedback_comment"]}
                if rating
                else None
            )
            output.append(item)
        return output

    def add_message(
        self,
        chat_id: str,
        user_id: str,
        role: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now()
        row = {
            "id": str(uuid.uuid4()),
            "conversation_id": chat_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "payload": payload or {},
            "created_at": now,
        }
        with self.engine.begin() as connection:
            title_row = connection.execute(
                select(conversation.c.title).where(
                    and_(conversation.c.id == chat_id, conversation.c.user_id == user_id)
                ).with_for_update()
            ).first()
            if not title_row:
                raise KeyError(chat_id)
            connection.execute(messages.insert().values(**row))
            updates: dict[str, Any] = {"updated_at": now}
            if role == "user" and title_row.title == "New chat":
                updates["title"] = " ".join(content.split())[:120] or "New chat"
            connection.execute(
                update(conversation)
                .where(and_(conversation.c.id == chat_id, conversation.c.user_id == user_id))
                .values(**updates)
            )
        row["feedback"] = None
        row["chat_id"] = row.pop("conversation_id")
        return row

    def update_message_payload(
        self,
        chat_id: str,
        user_id: str,
        message_id: str,
        additions: dict[str, Any],
    ) -> dict[str, Any] | None:
        with self.engine.begin() as connection:
            statement = select(messages).where(
                and_(
                    messages.c.id == message_id,
                    messages.c.conversation_id == chat_id,
                    messages.c.user_id == user_id,
                )
            ).with_for_update()
            row = connection.execute(statement).mappings().first()
            if not row:
                return None
            payload = dict(row["payload"] or {})
            payload.update(additions)
            connection.execute(
                update(messages)
                .where(messages.c.id == message_id)
                .values(payload=payload)
            )
            return {**dict(row), "payload": payload}

    def save_feedback(
        self,
        chat_id: str,
        user_id: str,
        message_id: str,
        rating: str,
        comment: str | None,
    ) -> dict[str, Any] | None:
        now = _now()
        with self.engine.begin() as connection:
            owned_message = connection.execute(
                select(messages.c.id).where(
                    and_(
                        messages.c.id == message_id,
                        messages.c.conversation_id == chat_id,
                        messages.c.user_id == user_id,
                        messages.c.role == "assistant",
                    )
                )
            ).first()
            if not owned_message:
                return None
            values = {
                "id": str(uuid.uuid4()),
                "message_id": message_id,
                "user_id": user_id,
                "rating": rating,
                "comment": comment.strip() if comment else None,
                "created_at": now,
                "updated_at": now,
            }
            statement = insert(feedback).values(**values)
            statement = statement.on_conflict_do_update(
                constraint="uq_feedback_message_user",
                set_={
                    "rating": statement.excluded.rating,
                    "comment": statement.excluded.comment,
                    "updated_at": now,
                },
            )
            connection.execute(statement)
        return {"rating": values["rating"], "comment": values["comment"]}
