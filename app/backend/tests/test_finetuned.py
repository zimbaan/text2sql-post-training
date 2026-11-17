"""Tests for the post-trained model integration: prompt format, schema DDL, and request routing."""

import sqlite3

import pytest
from sqlalchemy import create_engine

from app.core import finetuned as finetuned_mod
from app.core.finetuned import SYSTEM_PROMPT, build_user_prompt, extract_sql
from app.db.introspect import format_schema_ddl, normalize_table_names
from app.db.manager import ConnectionManager
from app.services import nl2sql as nl2sql_mod
from app.services.nl2sql import NL2SQLService


@pytest.fixture()
def concert_db(tmp_path):
    path = tmp_path / "concert.sqlite"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE singer (
            singer_id INTEGER PRIMARY KEY,
            name TEXT,
            country TEXT,
            age INTEGER
        );
        CREATE TABLE concert (concert_id INTEGER PRIMARY KEY, year INTEGER,
            singer_id INTEGER REFERENCES singer(singer_id));
        INSERT INTO singer VALUES (1, 'Ana', 'France', 34), (2, 'Bo', 'Peru', 25), (3, 'Cy', 'France', 41);
        INSERT INTO concert VALUES (1, 2014, 1), (2, 2015, 3);
        """
    )
    con.commit()
    con.close()
    return path


def test_prompt_matches_training_format():
    assert SYSTEM_PROMPT.startswith("You are an expert in SQLite.")
    prompt = build_user_prompt("CREATE TABLE t (a INT);", "How many rows?")
    assert prompt == "Database schema:\nCREATE TABLE t (a INT);\n\nQuestion: How many rows?"


def test_extract_sql():
    assert extract_sql("```sql\nSELECT name FROM singer;\n```") == "SELECT name FROM singer"
    assert extract_sql("SELECT 1; SELECT 2") == "SELECT 1"
    assert extract_sql("SELECT  name\n FROM singer WHERE name = 'A  B'") == "SELECT name FROM singer WHERE name = 'A  B'"
    assert extract_sql("") == ""


def test_normalize_table_names(concert_db):
    engine = create_engine(f"sqlite:///{concert_db}")
    assert normalize_table_names(engine, None, ["default.singer", "main.concert", "singer"]) == [
        "singer",
        "concert",
        "singer",
    ]
    assert normalize_table_names(engine, "public", ["public.orders", "other.orders"]) == [
        "orders",
        "other.orders",
    ]


def test_schema_ddl_sqlite_uses_original_ddl_and_scope(concert_db):
    engine = create_engine(f"sqlite:///{concert_db}")
    full = format_schema_ddl(engine)
    assert full.startswith("CREATE TABLE singer (\nsinger_id INTEGER PRIMARY KEY,")
    assert "CREATE TABLE concert" in full and full.endswith(";")

    scoped = format_schema_ddl(engine, None, ["default.singer"])
    assert "CREATE TABLE singer" in scoped and "concert" not in scoped


class _StubFinetuned:
    name = "text2sql-qwen-0.5b-dpo"

    def __init__(self):
        self.calls = []

    async def generate_sql(self, schema_ddl, question):
        self.calls.append((schema_ddl, question))
        return "SELECT name FROM singer WHERE age > 30 ORDER BY name", "raw", 0.91


def _service_with_db(concert_db, llm_client=None):
    manager = ConnectionManager()
    conn_id, _, _ = manager.create_connection("sqlite", database=str(concert_db))
    return NL2SQLService(llm_client=llm_client or object(), connection_manager=manager), conn_id


@pytest.mark.asyncio
async def test_finetuned_model_is_routed_with_training_prompt(concert_db, monkeypatch):
    stub = _StubFinetuned()
    monkeypatch.setattr(nl2sql_mod, "get_finetuned_model", lambda: stub)
    monkeypatch.setattr(nl2sql_mod, "is_finetuned_model", lambda m: m == stub.name)
    service, conn_id = _service_with_db(concert_db)

    result = await service.generate_sql(
        conn_id,
        "Which singers are older than 30?",
        database="main",
        table_scope=["default.singer"],
        model=stub.name,
    )

    schema_ddl, question = stub.calls[0]
    assert "CREATE TABLE singer" in schema_ddl and "concert" not in schema_ddl
    assert question == "Which singers are older than 30?"
    assert result["generated_by"] == stub.name
    assert result["confidence"] == 0.91
    assert result["is_read_only"] is True
    assert result["rows"] == [["Ana"], ["Cy"]]


@pytest.mark.asyncio
async def test_other_models_use_json_planner_with_selected_model(concert_db, monkeypatch):
    monkeypatch.setattr(nl2sql_mod, "is_finetuned_model", lambda m: False)

    class FakeLLM:
        default_model = "llama3.1"

        def __init__(self):
            self.models = []

        async def generate_json(self, prompt, system_prompt=None, model=None, retry_on_failure=True):
            self.models.append(model)
            return {"sql": "SELECT count(*) FROM singer", "reasoning": "count", "confidence": 0.8}

    llm = FakeLLM()
    service, conn_id = _service_with_db(concert_db, llm)
    result = await service.generate_sql(conn_id, "How many singers?", database="main", model="qwen2.5:7b")

    assert llm.models == ["qwen2.5:7b"]
    assert result["generated_by"] == "qwen2.5:7b"
    assert result["rows"] == [[3]]


def test_finetuned_model_hidden_without_adapter(tmp_path, monkeypatch):
    model = finetuned_mod.FinetunedSQLModel("x", "base", str(tmp_path / "missing"))
    assert model.available is False
