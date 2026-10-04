from abc import ABC, abstractmethod


class LLMRepositoryInterface(ABC):
    @abstractmethod
    def invoke(self, messages: list[tuple[str, str]]) -> str:
        """(role, content) pairs in, the model's reply as plain text out."""
        ...
