from .dependency_container import DependencyContainer

container = DependencyContainer()

from .inject import get_auth_adapter, get_health_adapter, get_query_adapter, get_summary_adapter, get_chat_adapter


__all__ = ["container", "get_auth_adapter", "get_health_adapter", "get_query_adapter", "get_summary_adapter",
           "get_chat_adapter"]
