from abc import ABC, abstractmethod
from typing import Any


class AnalyticsDatabaseRepositoryInterface(ABC):
    @abstractmethod
    def explain(self, sql: str) -> None:
        """Checks the query plan without running the query."""
        ...

    @abstractmethod
    def fetch(self, sql: str, max_rows: int) -> tuple[list[str], list[dict[str, Any]]]:
        ...
