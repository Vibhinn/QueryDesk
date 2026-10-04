from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.responses import JSONResponse

from src.app.adapters import AuthAdapter, HealthAdapter, QueryAdapter, SummaryAdapter, ChatAdapter
from src.app.factory import ApplicationServiceFactory
from src.app.injector import container
from src.app.exceptions import (NotAuthenticated, ChatNotFound, MessageNotFound, NoSQLResultToSummarize,
                                SummaryGenerationFailed, ServiceUnavailable)

from src.auth import InMemorySessionRepository
from src.database import DatabaseConnection, DatabaseType, PostgresAnalyticsRepository, PostgresChatRepository
from src.llm import LLMConnection, LangChainRepository
from src.pipeline import NL2SQLPipeline
from src.schema import MarkdownSchemaRepository

from src.utils.config import Settings, get_settings

from .installation import MiddlewareInstallation, APIRouterInstallation

if TYPE_CHECKING:
    from fastapi import FastAPI


class Builder:
    def __init__(self, app: FastAPI):
        self.app: FastAPI = app
        self.settings: Settings = get_settings()
        self._EXCEPTION_STATUS_CODES: dict[type[Exception], int] = {
            NoSQLResultToSummarize: 400,
            NotAuthenticated: 401,
            ChatNotFound: 404,
            MessageNotFound: 404,
            SummaryGenerationFailed: 502,
            ServiceUnavailable: 503,
        }

    @property
    def exception_map(self):
        return self._EXCEPTION_STATUS_CODES

    def build_and_initialize_app(self):
        self.__install_middleware()

        self.__create_and_initialize_connections()
        self.__register_dependencies()

        self.__install_routers()
        self.__register_exception_handlers()

    def __install_middleware(self):
        MiddlewareInstallation.install_middleware(self.app, self.settings)

    def __install_routers(self):
        APIRouterInstallation.install_api_routers(self.app)

    def __create_and_initialize_connections(self):
        LLMConnection.initialize(self.settings)

    def __register_dependencies(self):
        container.register(Settings, lambda: self.settings)
        container.register(LangChainRepository, lambda: LangChainRepository())
        container.register(InMemorySessionRepository, lambda: InMemorySessionRepository())

        container.register(ApplicationServiceFactory, lambda: ApplicationServiceFactory(
                                                                        build_pipeline=self.__build_pipeline,
                                                                        build_chat_repo=self.__build_chat_repo))

        container.register(AuthAdapter, lambda: AuthAdapter(container.resolve(InMemorySessionRepository)))
        container.register(HealthAdapter, lambda: HealthAdapter(container.resolve(ApplicationServiceFactory)))
        container.register(QueryAdapter, lambda: QueryAdapter(container.resolve(ApplicationServiceFactory)))
        container.register(ChatAdapter, lambda: ChatAdapter(container.resolve(ApplicationServiceFactory)))
        container.register(SummaryAdapter, lambda: SummaryAdapter(container.resolve(ApplicationServiceFactory),
                                                                        container.resolve(LangChainRepository)))

        # Load SCHEMA.md and connect to the databases now, not on the first request
        container.resolve(ApplicationServiceFactory)

    def __build_pipeline(self) -> NL2SQLPipeline:
        schema = MarkdownSchemaRepository(self.settings.schema_path)
        engine = DatabaseConnection.initialize(DatabaseType.ANALYTICS, self.settings.database_url)
        return NL2SQLPipeline(
            schema=schema,
            analytics_db=PostgresAnalyticsRepository(engine, self.settings.query_timeout_ms),
            llm=container.resolve(LangChainRepository),
            settings=self.settings,
        )

    def __build_chat_repo(self) -> PostgresChatRepository:
        engine = DatabaseConnection.initialize(DatabaseType.APP, self.settings.app_database_url)
        return PostgresChatRepository(engine)

    def __register_exception_handlers(self):
        for exception_class, status_code in self._EXCEPTION_STATUS_CODES.items():
            self.app.add_exception_handler(exception_class, self.status_handler(status_code))

    @staticmethod
    def status_handler(status_code: int):
        async def handle(request, exc):
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})
        return handle
