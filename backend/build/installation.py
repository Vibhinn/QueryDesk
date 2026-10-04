from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api import health_api_router, auth_api_router, query_api_router, chats_api_router
from src.utils.config import Settings


class MiddlewareInstallation:
    @staticmethod
    def install_middleware(app: FastAPI, settings: Settings):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Authorization"],
        )

class APIRouterInstallation:
    @staticmethod
    def install_api_routers(app: FastAPI):
        routers = [health_api_router, auth_api_router, query_api_router, chats_api_router]
        for api_router in routers:
            app.include_router(api_router)
