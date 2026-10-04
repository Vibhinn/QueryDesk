from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..injector import get_auth_adapter
from ..adapters import AuthAdapter
from src.utils.types import AuthenticatedUser

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth_adapter: AuthAdapter = Depends(get_auth_adapter),
) -> AuthenticatedUser:
    if credentials is None:
        return auth_adapter.authenticate(None, None)
    return auth_adapter.authenticate(credentials.scheme, credentials.credentials)
