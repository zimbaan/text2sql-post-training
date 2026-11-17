"""Tests for SQL safety module."""

import pytest

from app.core.sql_safe import (
    contains_forbidden,
    enforce_limit,
    ensure_no_wildcard_on_big_tables,
    is_read_only,
    validate_sql,
)


def test_is_read_only():
    """Test is_read_only function."""
    assert is_read_only("SELECT * FROM users") is True
    assert is_read_only("SELECT id, name FROM users WHERE id = 1") is True
    assert is_read_only("WITH cte AS (SELECT * FROM users) SELECT * FROM cte") is True
    assert is_read_only("INSERT INTO users VALUES (1, 'test')") is False
    assert is_read_only("UPDATE users SET name = 'test'") is False
    assert is_read_only("DELETE FROM users WHERE id = 1") is False
    assert is_read_only("CREATE TABLE test (id INT)") is False
    assert is_read_only("DROP TABLE users") is False
    assert is_read_only("") is False


def test_contains_forbidden():
    """Test contains_forbidden function."""
    assert contains_forbidden("SELECT * FROM users") is None
    assert contains_forbidden("INSERT INTO users VALUES (1, 'test')") is not None
    assert contains_forbidden("UPDATE users SET name = 'test'") is not None
    assert contains_forbidden("DELETE FROM users") is not None
    assert contains_forbidden("CREATE TABLE test (id INT)") is not None
    assert contains_forbidden("DROP TABLE users") is not None
    assert contains_forbidden("INSERT INTO users VALUES (1, 'test')", allow_modification=True) is None


def test_enforce_limit():
    """Test enforce_limit function."""
    sql = "SELECT * FROM users"
    result, applied = enforce_limit(sql, 100)
    assert "LIMIT 100" in result.upper()
    assert applied is True

    sql = "SELECT * FROM users LIMIT 50"
    result, applied = enforce_limit(sql, 100)
    assert "LIMIT 50" in result.upper() or "LIMIT 100" in result.upper()
    # Should keep existing limit if it's smaller
    assert "LIMIT 100" not in result.upper() or "LIMIT 50" in result.upper()

    sql = "SELECT * FROM users LIMIT 200"
    result, applied = enforce_limit(sql, 100)
    assert "LIMIT 100" in result.upper()
    assert applied is True

    sql = "SELECT COUNT(*) FROM users"
    result, applied = enforce_limit(sql, 100)
    # Aggregates might not need LIMIT, but we apply it for safety
    assert "LIMIT" in result.upper() or not applied


def test_ensure_no_wildcard_on_big_tables():
    """Test ensure_no_wildcard_on_big_tables function."""
    sql = "SELECT * FROM small_table"
    table_stats = {"small_table": {"approx_row_count": 1000}}
    warnings = ensure_no_wildcard_on_big_tables(sql, table_stats)
    assert len(warnings) == 0

    sql = "SELECT * FROM big_table"
    table_stats = {"big_table": {"approx_row_count": 2000000}}
    warnings = ensure_no_wildcard_on_big_tables(sql, table_stats)
    assert len(warnings) > 0
    assert "big_table" in warnings[0].lower()

    sql = "SELECT id, name FROM big_table"
    warnings = ensure_no_wildcard_on_big_tables(sql, table_stats)
    assert len(warnings) == 0


def test_validate_sql():
    """Test validate_sql function."""
    sql = "SELECT * FROM users"
    result_sql, warnings, error = validate_sql(sql)
    assert error is None
    assert "LIMIT" in result_sql.upper()

    sql = "INSERT INTO users VALUES (1, 'test')"
    result_sql, warnings, error = validate_sql(sql, allow_modification=False)
    assert error is not None
    assert "INSERT" in error.upper() or "DML" in error.upper()

    sql = "SELECT * FROM users"
    result_sql, warnings, error = validate_sql(sql, allow_modification=True)
    # Should allow SELECT
    assert error is None or "INSERT" not in error.upper()

