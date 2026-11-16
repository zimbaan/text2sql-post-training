"""Prompt construction: the database schema (as CREATE TABLE statements) plus the question."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

SYSTEM_PROMPT = (
    "You are an expert in SQLite. Given a database schema and a question, write one SQLite query that "
    "answers the question. Reply with only the SQL query and no explanation."
)


def _clean_ddl(sql: str) -> str:
    lines = [line.strip() for line in sql.strip().splitlines() if line.strip()]
    return "\n".join(lines).rstrip(";") + ";"


def _cell(v, width: int = 32) -> str:
    s = "NULL" if v is None else str(v).replace("\n", " ")
    return s if len(s) <= width else s[: width - 1] + "…"


@lru_cache(maxsize=512)
def schema_text(db: str, sample_rows: int = 0) -> str:
    """CREATE TABLE statements for every table, optionally followed by a few example rows."""
    uri = Path(db).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.text_factory = lambda b: b.decode("utf-8", errors="replace")
    try:
        tables = con.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "AND sql IS NOT NULL ORDER BY rowid"
        ).fetchall()
        blocks = []
        for name, ddl in tables:
            block = _clean_ddl(ddl)
            if sample_rows > 0:
                cur = con.execute(f'SELECT * FROM "{name}" LIMIT {int(sample_rows)}')
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                if rows:
                    body = "\n".join(" | ".join(_cell(v) for v in row) for row in rows)
                    block += f"\n/* {len(rows)} example rows:\n{' | '.join(cols)}\n{body}\n*/"
            blocks.append(block)
        return "\n\n".join(blocks)
    finally:
        con.close()


def build_messages(schema: str, question: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Database schema:\n{schema}\n\nQuestion: {question}"},
    ]


def messages_for(root: Path, example, sample_rows: int = 0) -> list[dict]:
    from .spider import db_file

    return build_messages(schema_text(str(db_file(root, example.db_id)), sample_rows), example.question)
