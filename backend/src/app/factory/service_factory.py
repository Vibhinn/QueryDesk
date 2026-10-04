from __future__ import annotations

from typing import Callable, TypeVar, TYPE_CHECKING

from ..exceptions import ServiceUnavailable

if TYPE_CHECKING:
    from ..ports import QueryPipelineInterface, ChatRepositoryInterface

T = TypeVar("T")


class ApplicationServiceFactory:
    """Holds the services that need an outside resource to start (SCHEMA.md, databases).
    One that fails to start is reported by /api/health, and its endpoints return 503,
    instead of stopping the whole server."""

    def __init__(self,
                 build_pipeline: Callable[[], QueryPipelineInterface],
                 build_chat_repo: Callable[[], ChatRepositoryInterface]):
        self.__pipeline, self.__pipeline_error = self.__try_build(build_pipeline)
        self.__chat_repo, self.__chat_repo_error = self.__try_build(build_chat_repo)

    @staticmethod
    def __try_build(build: Callable[[], T]) -> tuple[T | None, str]:
        try:
            return build(), ""
        except Exception as exc:
            return None, str(exc)

    @property
    def pipeline_loaded(self) -> bool:
        return self.__pipeline is not None

    @property
    def chat_repo_loaded(self) -> bool:
        return self.__chat_repo is not None

    @property
    def startup_error(self) -> str:
        return self.__pipeline_error or self.__chat_repo_error

    def get_pipeline(self) -> QueryPipelineInterface:
        if self.__pipeline is None:
            raise ServiceUnavailable(f"NL2SQL is not configured: {self.__pipeline_error}")
        return self.__pipeline

    def get_chat_repo(self) -> ChatRepositoryInterface:
        if self.__chat_repo is None:
            raise ServiceUnavailable(f"Chat history is unavailable: {self.__chat_repo_error}")
        return self.__chat_repo
