"""Lightweight Markdown schema reader and retrieval for SCHEMA.md-style files."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.app.ports import SchemaRepositoryInterface


@dataclass
class TableInfo:
    name: str
    text: str
    columns: set[str]
    terms: set[str]


def words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z0-9_]*", text) if len(w) > 1}


class MarkdownSchemaRepository(SchemaRepositoryInterface):
    def __init__(self, path: Path):
        self.path = path
        self.text = path.read_text(encoding="utf-8")
        self.dialect = self._read_value("Dialect") or "PostgreSQL"
        self.tables = self._parse_tables()
        self.relationships = self._section("Relationships")
        self.definitions = self._section("Business definitions")
        self.global_rules = self._section("Global data rules and caveats")
        if not self.tables:
            raise ValueError("No table definitions found. Add sections like ### `table_name` with a Columns table.")

    def _read_value(self, key: str) -> str:
        match = re.search(rf"\*\*{re.escape(key)}:\*\*\s*(.+)", self.text, re.I)
        return match.group(1).strip().strip("`") if match else ""

    def _section(self, title: str) -> str:
        match = re.search(rf"^##\s+{re.escape(title)}\s*$([\s\S]*?)(?=^##\s+|\Z)", self.text, re.I | re.M)
        return match.group(1).strip() if match else ""

    def _parse_tables(self) -> dict[str, TableInfo]:
        matches = list(re.finditer(r"^###\s+`?([A-Za-z_][\w.]*)`?\s*$", self.text, re.M))
        tables: dict[str, TableInfo] = {}
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(self.text)
            chunk = self.text[match.start():end]
            # Table descriptions end at the next section of the same or higher level.
            end_section = re.search(r"^##\s+", chunk[4:], re.M)
            if end_section:
                chunk = chunk[:4 + end_section.start()]
            name = match.group(1).split(".")[-1]
            columns: set[str] = set()
            for row in re.findall(r"^\|([^\n]+)\|\s*$", chunk, re.M):
                cells = [c.strip() for c in row.split("|")]
                if cells and cells[0].strip("`").lower() != "column" and re.fullmatch(r"`?[A-Za-z_][\w]*`?", cells[0]):
                    columns.add(cells[0].strip("`"))
            tables[name] = TableInfo(name=name, text=chunk, columns=columns, terms=words(chunk))
        return tables

    def retrieve(self, question: str, hinted_tables: list[str] | None = None, limit: int = 8) -> str:
        qwords = words(question)
        hintset = {x.split(".")[-1].lower() for x in (hinted_tables or [])}
        scored = []
        for table in self.tables.values():
            score = len(qwords & table.terms) + (8 if table.name.lower() in hintset else 0)
            # Table and column identifiers receive a small boost.
            score += sum(2 for c in table.columns if c.lower() in qwords)
            scored.append((score, table.name, table))
        selected = [x[2] for x in sorted(scored, key=lambda x: (-x[0], x[1])) if x[0] > 0][:limit]
        if not selected:
            selected = list(self.tables.values())[:min(3, limit)]
        sections = [f"Dialect: {self.dialect}", "Relevant table definitions:\n" + "\n".join(t.text for t in selected)]
        selected_names = {t.name.lower() for t in selected}
        relationship_rows = self._relevant_rows(self.relationships, qwords, selected_names, relationship=True)
        definition_rows = self._relevant_rows(self.definitions, qwords, selected_names)
        rule_lines = self._relevant_bullets(self.global_rules, qwords, selected_names)
        if relationship_rows:
            sections.append("Relevant join relationships:\n" + "\n".join(relationship_rows))
        if definition_rows:
            sections.append("Relevant business definitions:\n" + "\n".join(definition_rows))
        if rule_lines:
            sections.append("Relevant global rules:\n" + "\n".join(rule_lines))
        return "\n\n".join(sections)

    @staticmethod
    def _rows(section: str) -> list[str]:
        return [line.strip() for line in section.splitlines() if line.strip().startswith("|") and not re.fullmatch(r"\|[\s:|+-]+\|", line.strip())]

    @classmethod
    def _relevant_rows(cls, section: str, qwords: set[str], selected_names: set[str], relationship: bool = False) -> list[str]:
        rows = cls._rows(section)
        if len(rows) < 2:
            return rows
        content = rows[2:]
        scored: list[tuple[int, str]] = []
        for row in content:
            row_words = words(row)
            score = len(qwords & row_words)
            if relationship:
                score += 4 if any(name in row.lower() for name in selected_names) else 0
            else:
                score += 2 if any(name in row.lower() for name in selected_names) else 0
            if score > 0:
                scored.append((score, row))
        if not scored:
            return content[:min(4, len(content))]
        return [row for _, row in sorted(scored, key=lambda item: -item[0])[:8]]

    def _relevant_bullets(self, section: str, qwords: set[str], selected_names: set[str]) -> list[str]:
        lines = [line.strip() for line in section.splitlines() if line.strip().startswith(("* ", "- "))]
        scored = []
        for line in lines:
            score = len(qwords & words(line)) + (2 if any(name in line.lower() for name in selected_names) else 0)
            if score:
                scored.append((score, line))
        return [line for _, line in sorted(scored, key=lambda item: -item[0])[:10]] or lines[:6]

    def candidate_table_names(self, question: str, limit: int = 20) -> list[str]:
        qwords = words(question)
        ranked = sorted(
            self.tables.values(),
            key=lambda table: (-len(qwords & table.terms) - 2 * sum(c.lower() in qwords for c in table.columns), table.name),
        )
        return [table.name for table in ranked[:limit]]

    def all_table_names(self) -> set[str]:
        return set(self.tables)

    def catalog_summary(self) -> str:
        """Bounded overview for early classification; full sections are retrieved later."""
        lines = [f"SQL dialect: {self.dialect}", "Tables:"]
        for table in self.tables.values():
            purpose = re.search(r"\*\*Purpose:\*\*\s*(.+)", table.text)
            grain = re.search(r"\*\*Row grain:\*\*\s*(.+)", table.text)
            columns = ", ".join(sorted(table.columns))
            lines.append(f"- {table.name}: {purpose.group(1) if purpose else ''}; grain: {grain.group(1) if grain else 'unspecified'}; columns: {columns}")
        return "\n".join(lines)[:12000]
