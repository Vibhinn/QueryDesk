"""PostgreSQL tables for user-owned conversations, messages, and feedback."""
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
)


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
