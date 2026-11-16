"""SQL utilities: normalising gold queries, extracting SQL from model output, sandboxed execution and
execution-based comparison."""

from __future__ import annotations

import re
import sqlite3
import time
from collections import Counter
from itertools import permutations
from pathlib import Path
from typing import NamedTuple

_FENCE = re.compile(r"```(?:sql|sqlite)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def _split_outside_quotes(sql: str) -> list[str]:
    """Split on ';' that is not inside a quoted string or identifier."""
    parts, buf, quote = [], [], None
    for ch in sql:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
            buf.append(ch)
        elif ch == ";":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def collapse_whitespace(sql: str) -> str:
    """Collapse runs of whitespace outside string literals (Spider gold SQL has irregular spacing)."""
    out, quote, prev_space = [], None, False
    for ch in sql.strip():
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            prev_space = False
        elif ch.isspace():
            if not prev_space:
                out.append(" ")
            prev_space = True
        else:
            out.append(ch)
            prev_space = False
    return "".join(out).strip()


def normalize_gold(sql: str) -> str:
    return collapse_whitespace(sql).rstrip(";").strip()


def extract_sql(text: str) -> str:
    """Pull a single SQL statement out of a model completion."""
    text = text.strip()
    match = _FENCE.search(text)
    if match:
        text = match.group(1)
    elif text.startswith("```"):  # unterminated fence
        text = text.split("\n", 1)[1] if "\n" in text else ""
    text = re.sub(r"^\s*(sql|sqlite)\s*:\s*", "", text, flags=re.IGNORECASE)
    statements = _split_outside_quotes(text)
    return collapse_whitespace(statements[0]) if statements else ""


class ExecResult(NamedTuple):
    ok: bool
    rows: list[tuple] | None
    error: str | None


def _decode(b: bytes) -> str:
    return b.decode("utf-8", errors="replace")


def execute(db: str | Path, sql: str, timeout_s: float = 10.0, max_rows: int = 100_000) -> ExecResult:
    """Run one query against a read-only SQLite connection with a wall-clock timeout."""
    if not sql.strip():
        return ExecResult(False, None, "EmptyQuery")
    uri = Path(db).resolve().as_uri() + "?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, check_same_thread=False)
    except sqlite3.Error as e:
        return ExecResult(False, None, f"ConnectError: {e}")
    con.text_factory = _decode
    deadline = time.monotonic() + timeout_s
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        rows = con.execute(sql).fetchmany(max_rows + 1)
        if len(rows) > max_rows:
            return ExecResult(False, None, "TooManyRows")
        return ExecResult(True, [tuple(r) for r in rows], None)
    except sqlite3.OperationalError as e:
        msg = "Timeout" if "interrupted" in str(e) else f"OperationalError: {e}"
        return ExecResult(False, None, msg)
    except Exception as e:  # noqa: BLE001 - any failure is a failed prediction
        return ExecResult(False, None, f"{type(e).__name__}: {e}")
    finally:
        con.close()


def _norm_value(v):
    if isinstance(v, float):
        v = round(v, 4)
        return 0.0 if v == 0 else v
    if isinstance(v, str):
        return v.strip()
    return v


def results_match(gold: list[tuple] | None, pred: list[tuple] | None, order_matters: bool) -> bool:
    """Execution match: same rows (as a multiset unless the gold query orders them), column order ignored."""
    if gold is None or pred is None:
        return False
    g = [tuple(_norm_value(v) for v in row) for row in gold]
    p = [tuple(_norm_value(v) for v in row) for row in pred]
    if len(g) != len(p):
        return False
    if not g:
        return True
    width = len(g[0])
    if any(len(row) != width for row in p):
        return False
    orders = permutations(range(width)) if width <= 4 else [tuple(range(width))]
    g_counter = None if order_matters else Counter(g)
    for perm in orders:
        q = [tuple(row[i] for i in perm) for row in p]
        if order_matters:
            if q == g:
                return True
        elif Counter(q) == g_counter:
            return True
    return False


def gold_orders_rows(sql: str) -> bool:
    return "order by" in sql.lower()


def category(sql: str) -> str:
    """Rough difficulty bucket from the gold query's structure."""
    s = f" {sql.lower()} "
    if s.count("select") > 1 or any(k in s for k in (" intersect ", " union ", " except ")):
        return "nested / set ops"
    if " join " in s:
        return "join"
    if "group by" in s or "order by" in s or "having" in s:
        return "group / order"
    return "single table"
