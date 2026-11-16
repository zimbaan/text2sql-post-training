import sqlite3

import pytest

from t2s.prompts import build_messages, schema_text
from t2s.sql import category, collapse_whitespace, execute, extract_sql, normalize_gold, results_match


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "shop.sqlite"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT, city TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL);
        INSERT INTO customer VALUES (1, 'Ana', 'Pune'), (2, 'Bo', 'Delhi'), (3, 'Cy', 'Pune');
        INSERT INTO orders VALUES (1, 1, 10.5), (2, 1, 4.5), (3, 2, 7.0);
        """
    )
    con.commit()
    con.close()
    return path


def test_extract_sql_variants():
    assert extract_sql("```sql\nSELECT name FROM customer;\n```") == "SELECT name FROM customer"
    assert extract_sql("SELECT 1; SELECT 2;") == "SELECT 1"
    assert extract_sql("SQL: SELECT ';' FROM t;") == "SELECT ';' FROM t"
    assert extract_sql("```sql\nSELECT  *\n  FROM t") == "SELECT * FROM t"
    assert extract_sql("") == ""


def test_whitespace_collapse_keeps_literals():
    assert collapse_whitespace("SELECT  a FROM t WHERE x  =  'New  York'") == "SELECT a FROM t WHERE x = 'New  York'"
    assert normalize_gold("SELECT count(*) FROM head WHERE age  >  56 ;") == "SELECT count(*) FROM head WHERE age > 56"


def test_execute_ok_error_and_readonly(db):
    res = execute(db, "SELECT name FROM customer WHERE city = 'Pune' ORDER BY id")
    assert res.ok and res.rows == [("Ana",), ("Cy",)]
    assert not execute(db, "SELECT nope FROM customer").ok
    assert not execute(db, "DELETE FROM customer").ok  # read-only connection
    assert execute(db, "SELECT count(*) FROM customer").rows == [(3,)]


def test_execute_timeout(db):
    slow = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT count(*) FROM c"
    res = execute(db, slow, timeout_s=0.2)
    assert not res.ok and res.error == "Timeout"


def test_results_match_rules():
    assert results_match([(1, "a"), (2, "b")], [(2, "b"), (1, "a")], order_matters=False)
    assert not results_match([(1, "a"), (2, "b")], [(2, "b"), (1, "a")], order_matters=True)
    assert results_match([(1, "a")], [("a", 1)], order_matters=False)  # column order ignored
    assert results_match([(15.0,)], [(15,)], order_matters=False)
    assert results_match([(1 / 3,)], [(0.33333,)], order_matters=False)
    assert not results_match([(1,), (1,)], [(1,)], order_matters=False)  # multiset, not set
    assert not results_match([(1,)], None, order_matters=False)
    assert results_match([], [], order_matters=False)


def test_category():
    assert category("SELECT name FROM customer") == "single table"
    assert category("SELECT city, count(*) FROM customer GROUP BY city") == "group / order"
    assert category("SELECT c.name FROM customer c JOIN orders o ON c.id = o.customer_id") == "join"
    assert category("SELECT name FROM customer WHERE id IN (SELECT customer_id FROM orders)") == "nested / set ops"


def test_schema_and_messages(db):
    text = schema_text(str(db))
    assert "CREATE TABLE customer" in text and "CREATE TABLE orders" in text
    with_rows = schema_text(str(db), 2)
    assert "2 example rows" in with_rows and "Ana" in with_rows
    msgs = build_messages(text, "How many customers?")
    assert msgs[0]["role"] == "system" and msgs[1]["content"].endswith("Question: How many customers?")
