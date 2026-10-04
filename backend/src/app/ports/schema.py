from abc import ABC, abstractmethod


class SchemaRepositoryInterface(ABC):
    dialect: str

    @abstractmethod
    def retrieve(self, question: str, hinted_tables: list[str] | None = None, limit: int = 8) -> str:
        ...

    @abstractmethod
    def candidate_table_names(self, question: str, limit: int = 20) -> list[str]:
        ...

    @abstractmethod
    def all_table_names(self) -> set[str]:
        ...

    @abstractmethod
    def catalog_summary(self) -> str:
        ...
