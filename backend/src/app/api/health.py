from fastapi import APIRouter, Depends

from ..injector import get_health_adapter
from ..adapters import HealthAdapter

health_api_router = APIRouter(prefix="/api")


@health_api_router.get("/health")
def health(health_adapter: HealthAdapter = Depends(get_health_adapter)):
    return health_adapter.health()
