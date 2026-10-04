from fastapi import APIRouter, Depends, Header, Response

from ..injector import get_auth_adapter
from ..adapters import AuthAdapter
from .security import get_current_user
from .validators import EmailLoginRequest
from src.utils.types import AuthenticatedUser

auth_api_router = APIRouter(prefix="/api/auth")


@auth_api_router.post("/login")
def login(request: EmailLoginRequest, auth_adapter: AuthAdapter = Depends(get_auth_adapter)):
    return auth_adapter.login(request.email)


@auth_api_router.get("/me")
def current_session(user: AuthenticatedUser = Depends(get_current_user)):
    return user


@auth_api_router.post("/logout", status_code=204)
def logout(
    authorization: str | None = Header(default=None),
    _user: AuthenticatedUser = Depends(get_current_user),
    auth_adapter: AuthAdapter = Depends(get_auth_adapter),
):
    auth_adapter.logout(authorization)
    return Response(status_code=204)
