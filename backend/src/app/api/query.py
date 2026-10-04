from fastapi import APIRouter, Depends

from ..injector import get_query_adapter, get_summary_adapter
from ..adapters import QueryAdapter, SummaryAdapter
from .security import get_current_user
from .validators import QueryRequest, SummarizeRequest
from src.utils.types import AuthenticatedUser, QueryResponse, SummarizeResponse

query_api_router = APIRouter(prefix="/api")


@query_api_router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, _user: AuthenticatedUser = Depends(get_current_user),
          query_adapter: QueryAdapter = Depends(get_query_adapter)):
    return query_adapter.query(request.question)


@query_api_router.post("/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest, _user: AuthenticatedUser = Depends(get_current_user),
              summary_adapter: SummaryAdapter = Depends(get_summary_adapter)):
    return summary_adapter.summarize(request.question, request.sql, request.columns, request.rows)
