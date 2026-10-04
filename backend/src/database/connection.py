from __future__ import annotations

from enum import StrEnum

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


class DatabaseType(StrEnum):
    ANALYTICS = "analytics"
    APP = "app"


class DatabaseConnection:
    _engines: dict[DatabaseType, Engine] = {}

    @classmethod
    def initialize(cls, database_type: DatabaseType, database_url: str) -> Engine:
        cls._engines[database_type] = create_engine(database_url, pool_pre_ping=True)
        return cls._engines[database_type]

    @classmethod
    def get_connection(cls, database_type: DatabaseType) -> Engine:
        engine = cls._engines.get(database_type)
        if engine is None:
            raise ValueError(f"Database {database_type} not initialized")
        return engine
