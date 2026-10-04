from fastapi import APIRouter, Depends

from ..injector import get_chat_adapter, get_summary_adapter
from ..adapters import ChatAdapter, SummaryAdapter
from .security import get_current_user
from .validators import ChatCreateRequest, FeedbackRequest, QueryRequest
from src.utils.types import (AuthenticatedUser, ChatDetail, ChatSummary, ChatTurnResponse, MessageFeedback,
                             SummarizeResponse)

chats_api_router = APIRouter(prefix="/api/chats")


@chats_api_router.get("", response_model=list[ChatSummary])
def list_chats(user: AuthenticatedUser = Depends(get_current_user),
               chat_adapter: ChatAdapter = Depends(get_chat_adapter)):
    return chat_adapter.list_chats(user["user_id"])


@chats_api_router.post("", response_model=ChatSummary)
def create_chat(request: ChatCreateRequest, user: AuthenticatedUser = Depends(get_current_user),
                chat_adapter: ChatAdapter = Depends(get_chat_adapter)):
    return chat_adapter.create_chat(user["user_id"], request.title)


@chats_api_router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(chat_id: str, user: AuthenticatedUser = Depends(get_current_user),
             chat_adapter: ChatAdapter = Depends(get_chat_adapter)):
    return chat_adapter.get_chat(chat_id, user["user_id"])


@chats_api_router.post("/{chat_id}/query", response_model=ChatTurnResponse)
def query_in_chat(chat_id: str, request: QueryRequest, user: AuthenticatedUser = Depends(get_current_user),
                  chat_adapter: ChatAdapter = Depends(get_chat_adapter)):
    return chat_adapter.query_in_chat(chat_id, user["user_id"], request.question)


@chats_api_router.post("/{chat_id}/messages/{message_id}/summarize", response_model=SummarizeResponse)
def summarize_chat_message(chat_id: str, message_id: str, user: AuthenticatedUser = Depends(get_current_user),
                           summary_adapter: SummaryAdapter = Depends(get_summary_adapter)):
    return summary_adapter.summarize_chat_message(chat_id, message_id, user["user_id"])


@chats_api_router.post("/{chat_id}/messages/{message_id}/feedback", response_model=MessageFeedback)
def submit_message_feedback(chat_id: str, message_id: str, request: FeedbackRequest,
                            user: AuthenticatedUser = Depends(get_current_user),
                            chat_adapter: ChatAdapter = Depends(get_chat_adapter)):
    return chat_adapter.save_feedback(chat_id, user["user_id"], message_id, request.rating, request.comment)
