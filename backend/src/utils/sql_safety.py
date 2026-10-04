from __future__ import annotations

import re
from sqlglot import exp, parse
from sqlglot.errors import ParseError


class SQLRejected(ValueError):
    pass


def sqlglot_dialect_name(dialect: str) -> str:
    normalized = dialect.strip().lower().replace("_", " ").replace("-", " ")
    aliases = {
        "postgresql": "postgres",
        "postgres sql": "postgres",
        "mssql": "tsql",
        "sql server": "tsql",
        "microsoft sql server": "tsql",
        "google bigquery": "bigquery",
        "sqlite3": "sqlite",
    }
    return aliases.get(normalized, normalized.replace(" ", ""))


def validate_sql(sql: str, dialect: str, known_tables: set[str]) -> tuple[str, exp.Expression]:
    candidate = sql.strip().removesuffix(";").strip()
    if not candidate:
        raise SQLRejected("The model did not produce SQL.")
    read_dialect = sqlglot_dialect_name(dialect)
    try:
        statements = parse(candidate, read=read_dialect)
    except ParseError as exc:
        raise SQLRejected(f"SQL could not be parsed for {dialect}: {exc}") from exc
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SQLRejected("Only one SQL statement is allowed.")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise SQLRejected("Only read-only SELECT queries are allowed.")
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command, exp.Merge)
    if any(tree.find(kind) for kind in forbidden):
        raise SQLRejected("The query contains a forbidden SQL operation.")
    if any(select.args.get("into") or select.args.get("locks") for select in tree.find_all(exp.Select)):
        raise SQLRejected("SELECT INTO and row-locking queries are not allowed.")
    ctes = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if name and name not in {t.lower() for t in known_tables} and name not in ctes:
            raise SQLRejected(f"Table '{table.name}' is not present in SCHEMA.md.")
    # SQL parameter syntax remains supported; raw multi-statement execution is rejected above.
    return candidate, tree


def optimize_read_query(sql: str, tree: exp.Expression, dialect: str, max_rows: int) -> str:
    """Apply only a predictable result cap; database EXPLAIN runs before execution."""
    if isinstance(tree, (exp.Select, exp.Union)) and not tree.args.get("limit"):
        tree = tree.copy()
        tree = tree.limit(max_rows)
    return tree.sql(dialect=sqlglot_dialect_name(dialect))


def strip_code_fence(value: str) -> str:
    text = value.strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()
