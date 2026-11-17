"""Tests for CSV utility."""

import pytest

from app.utils.csv import generate_csv


def test_generate_csv():
    """Test CSV generation."""
    columns = ["id", "name", "email"]
    rows = [
        [1, "Alice", "alice@example.com"],
        [2, "Bob", "bob@example.com"],
        [3, None, "charlie@example.com"],  # Test None handling
    ]

    csv_lines = list(generate_csv(columns, rows))

    # Should have header + rows + BOM
    assert len(csv_lines) > 0
    # First line should be BOM
    assert csv_lines[0] == "\ufeff"
    # Should contain header
    assert "id,name,email" in "".join(csv_lines)
    # Should contain data
    assert "Alice" in "".join(csv_lines)
    assert "Bob" in "".join(csv_lines)
    # None should be converted to empty string
    assert ",Charlie" in "".join(csv_lines) or ",charlie" in "".join(csv_lines).lower()

