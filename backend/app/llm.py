"""Configurable LangChain model adapter. Keys are read only by the server."""
from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from .config import get_settings


@lru_cache
def get_chat_model() -> BaseChatModel:
    settings = get_settings()
    provider = settings.model_provider.lower()
    common = {"temperature": settings.model_temperature}
    if settings.model_api_key:
        common["api_key"] = settings.model_api_key
    if provider in {"gemini", "google", "google_genai", "google-generativeai"}:
        from langchain_google_genai import ChatGoogleGenerativeAI

        params = {"model": settings.model_name, "temperature": settings.model_temperature}
        if settings.google_api_key:
            params["api_key"] = settings.google_api_key
        elif settings.model_api_key:
            params["api_key"] = settings.model_api_key
        return ChatGoogleGenerativeAI(**params)
    if provider in {"openai-compatible", "openai_compatible", "openai"}:
        from langchain_openai import ChatOpenAI

        params = {**common, "model": settings.model_name}
        base_url = settings.model_base_url.rstrip("/")
        # The OpenAI SDK requires a non-empty token even when local servers do
        # not authenticate. These servers commonly ignore this placeholder.
        if not settings.model_api_key and base_url:
            params["api_key"] = "local-no-key"
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]
        if base_url:
            params["base_url"] = base_url
        return ChatOpenAI(**params)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=settings.model_name, **common)
    # LangChain's provider registry supports additional integrations when their
    # provider package is installed in the backend environment.
    from langchain.chat_models import init_chat_model

    kwargs = {**common, "model": settings.model_name, "model_provider": provider}
    if settings.model_base_url:
        kwargs["base_url"] = settings.model_base_url
    return init_chat_model(**kwargs)
