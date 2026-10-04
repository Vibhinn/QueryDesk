from src.app.ports import LLMRepositoryInterface

from ..connection import LLMConnection
from ..formatting import response_text


class LangChainRepository(LLMRepositoryInterface):
    def invoke(self, messages: list[tuple[str, str]]) -> str:
        return response_text(LLMConnection.get_connection().invoke(messages))
