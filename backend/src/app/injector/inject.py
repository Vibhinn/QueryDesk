from src.app.injector import container

from ..adapters import AuthAdapter, HealthAdapter, QueryAdapter, SummaryAdapter, ChatAdapter


def get_auth_adapter() -> AuthAdapter:
    return container.resolve(AuthAdapter)

def get_health_adapter() -> HealthAdapter:
    return container.resolve(HealthAdapter)

def get_query_adapter() -> QueryAdapter:
    return container.resolve(QueryAdapter)

def get_summary_adapter() -> SummaryAdapter:
    return container.resolve(SummaryAdapter)

def get_chat_adapter() -> ChatAdapter:
    return container.resolve(ChatAdapter)
