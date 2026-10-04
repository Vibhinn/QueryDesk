from __future__ import annotations

from typing import TYPE_CHECKING

from src.utils.types import QueryResponse

if TYPE_CHECKING:
    from ..factory import ApplicationServiceFactory


class QueryAdapter:
    def __init__(self, services: ApplicationServiceFactory):
        self.services = services

    def query(self, question: str) -> QueryResponse:
        return QueryResponse.from_pipeline_state(self.services.get_pipeline().run(question))
