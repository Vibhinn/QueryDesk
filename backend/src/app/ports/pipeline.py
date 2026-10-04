from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.types import PipelineState


class QueryPipelineInterface(ABC):
    @abstractmethod
    def run(self, question: str, history: list[dict[str, Any]] | None = None) -> PipelineState:
        ...
