from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.app.ports import AnalyticsDatabaseRepositoryInterface


class PostgresAnalyticsRepository(AnalyticsDatabaseRepositoryInterface):
    """Runs validated read-only SQL against the analytics database."""

    def __init__(self, engine: Engine, query_timeout_ms: int):
        self.engine = engine
        self.query_timeout_ms = query_timeout_ms

    def explain(self, sql: str) -> None:
        # PostgreSQL EXPLAIN checks the plan without executing the query.
        with self.engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            connection.exec_driver_sql(f"SET LOCAL statement_timeout = {int(self.query_timeout_ms)}")
            # SQLAlchemy's text execution escapes literal percent signs for psycopg.
            connection.execute(text("EXPLAIN " + sql))

    def fetch(self, sql: str, max_rows: int) -> tuple[list[str], list[dict[str, Any]]]:
        with self.engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            connection.exec_driver_sql(f"SET LOCAL statement_timeout = {int(self.query_timeout_ms)}")
            # Use SQLAlchemy compilation so percent signs in LIKE/ILIKE patterns
            # are treated as SQL text, not psycopg parameter placeholders.
            result = connection.execute(text(sql))
            columns = list(result.keys())
            records = [dict(row._mapping) for row in result.fetchmany(max_rows)]
        return columns, records
