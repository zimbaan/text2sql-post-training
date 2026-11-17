"""SQL safety checks and transformations."""

import logging
import re
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import sqlparse

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# SQL keywords that indicate modifications
DDL_KEYWORDS = {"CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME"}
DML_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "MERGE", "REPLACE"}


def is_read_only(sql_text: str) -> bool:
    """Check if SQL statement is read-only (SELECT only).

    Args:
        sql_text: SQL statement to check

    Returns:
        True if the statement is read-only (SELECT), False otherwise
    """
    if not sql_text or not sql_text.strip():
        return False

    try:
        parsed = sqlparse.parse(sql_text)
        if not parsed:
            return False

        for statement in parsed:
            # Get first token (should be the statement type)
            first_token = statement.token_first()
            if first_token:
                token_type = first_token.ttype
                token_value = str(first_token.value).upper().strip()

                # Check for DDL/DML keywords
                if token_value in DDL_KEYWORDS or token_value in DML_KEYWORDS:
                    return False
                # WITH clause can precede SELECT, UPDATE, DELETE, INSERT
                if token_value == "WITH":
                    # Look for the actual statement after WITH
                    for token in statement.flatten():
                        if token.ttype is None and token.value.upper().strip() in {
                            "SELECT",
                            "UPDATE",
                            "DELETE",
                            "INSERT",
                        }:
                            token_value = token.value.upper().strip()
                            if token_value == "SELECT":
                                continue
                            if token_value in DML_KEYWORDS or token_value in DDL_KEYWORDS:
                                return False
                            break

                # Allow SELECT and WITH ... SELECT
                if token_value == "SELECT" or (token_value == "WITH" and "SELECT" in sql_text.upper()):
                    # Additional check: ensure no UPDATE/DELETE/INSERT in subqueries
                    upper_sql = sql_text.upper()
                    # Simple heuristic: if we see UPDATE/DELETE/INSERT not in comments
                    if re.search(r"\b(UPDATE|DELETE|INSERT)\b", upper_sql):
                        # Check if it's in a comment or string literal
                        # This is a simple check; for production, use proper parser
                        return False
                    return True

        return False
    except Exception as e:
        logger.warning(f"Error parsing SQL for read-only check: {e}")
        # On error, assume unsafe
        return False


def contains_forbidden(sql_text: str, allow_modification: bool = False) -> Optional[str]:
    """Check if SQL contains forbidden DDL/DML operations.

    Args:
        sql_text: SQL statement to check
        allow_modification: If True, allow DML/DDL

    Returns:
        Error message if forbidden operation found, None otherwise
    """
    if allow_modification:
        return None

    if not sql_text or not sql_text.strip():
        return None

    upper_sql = sql_text.upper()

    # Check for DDL
    for keyword in DDL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            return f"Forbidden DDL keyword detected: {keyword}"

    # Check for DML
    for keyword in DML_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            return f"Forbidden DML keyword detected: {keyword}"

    return None


def enforce_limit(sql_text: str, limit: int) -> Tuple[str, bool]:
    """Enforce LIMIT clause on SELECT statements.

    Args:
        sql_text: SQL statement
        limit: Maximum number of rows

    Returns:
        Tuple of (modified_sql, limit_was_applied)
    """
    if not sql_text or not sql_text.strip():
        return sql_text, False

    # Check if it's a SELECT statement
    if not is_read_only(sql_text):
        return sql_text, False

    upper_sql = sql_text.upper()

    # Check if LIMIT already exists
    if re.search(r"\bLIMIT\s+\d+", upper_sql, re.IGNORECASE):
        # Extract existing limit
        limit_match = re.search(r"\bLIMIT\s+(\d+)\b", upper_sql, re.IGNORECASE)
        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit <= limit:
                return sql_text, False
            # Replace with smaller limit
            return re.sub(
                r"\bLIMIT\s+\d+\b",
                f"LIMIT {limit}",
                sql_text,
                flags=re.IGNORECASE,
                count=1,
            ), True

    # Check if it's an aggregate that returns one row (GROUP BY with no LIMIT needed)
    # This is a heuristic - we'll still add LIMIT for safety unless explicitly single-row
    has_aggregate = re.search(r"\b(COUNT|SUM|AVG|MAX|MIN|GROUP\s+BY)\b", upper_sql)

    # Add LIMIT before semicolon or at end
    # Find the end of the statement (before semicolon or at end)
    sql_clean = sql_text.rstrip().rstrip(";")

    # Check if ORDER BY exists - if so, add LIMIT after it
    if re.search(r"\bORDER\s+BY\b", upper_sql):
        # Add LIMIT after ORDER BY clause
        # This regex finds ORDER BY ... and adds LIMIT after it
        pattern = r"(\bORDER\s+BY\b[^;]+?)(\s*;?\s*)$"
        match = re.search(pattern, sql_clean, re.IGNORECASE | re.DOTALL)
        if match:
            modified = re.sub(pattern, rf"\1\nLIMIT {limit}\2", sql_clean, flags=re.IGNORECASE)
            return modified, True

    # Otherwise, append LIMIT at the end
    return f"{sql_clean}\nLIMIT {limit}", True


def ensure_no_wildcard_on_big_tables(
    sql_text: str, table_stats: Dict[str, Dict[str, Any]]
) -> List[str]:
    """Check for SELECT * on large tables and return warnings.

    Args:
        sql_text: SQL statement
        table_stats: Dictionary mapping table names to stats like {'approx_row_count': int}

    Returns:
        List of warning messages
    """
    warnings = []

    if not sql_text or not sql_text.strip():
        return warnings

    upper_sql = sql_text.upper()

    # Check for SELECT *
    if re.search(r"\bSELECT\s+\*", upper_sql, re.IGNORECASE):
        # Try to extract table names (simple heuristic)
        # Look for FROM table_name or JOIN table_name
        from_match = re.search(r"\bFROM\s+(\w+)", upper_sql, re.IGNORECASE)
        if from_match:
            table_name = from_match.group(1).lower()
            if table_name in table_stats:
                row_count = table_stats[table_name].get("approx_row_count", 0)
                if row_count > 1000000:  # More than 1M rows
                    warnings.append(
                        f"SELECT * on large table '{table_name}' (~{row_count:,} rows). "
                        "Consider selecting specific columns for better performance."
                    )

    return warnings


def check_unknown_columns(sql_text: str, table_stats: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Check for references to columns not present in provided table stats.

    This is a best-effort heuristic using simple regex parsing of FROM/JOIN aliases.
    """
    if not sql_text or not sql_text.strip() or not table_stats:
        return None

    sql_lower = sql_text.lower()

    # Basic sanity: SELECT should have a FROM clause
    if "select" in sql_lower and " from " not in sql_lower:
        return "Query is missing a FROM clause. Please include the source table(s)."

    # Build alias -> table map from FROM/JOIN clauses
    alias_map: Dict[str, str] = {}
    import re

    # Matches patterns like "from schema.table alias" or "join table t"
    for match in re.finditer(r"\b(from|join)\s+([`.\w]+)(?:\s+as)?\s+([`\w]+)", sql_lower, re.IGNORECASE):
        table_token = match.group(2).strip("`")
        alias_token = match.group(3).strip("`")
        # Strip schema if present
        if "." in table_token:
            table_token = table_token.split(".")[-1]
        alias_map[alias_token] = table_token
        # Also map table name to itself if not already
        alias_map.setdefault(table_token, table_token)

    if not alias_map:
        # If there are alias.column references but no FROM/JOIN, flag it
        if re.search(r"[`\w]+\.[`\w]+", sql_lower):
            return "Table aliases are used but no FROM/JOIN clause was found. Please include tables."
        return None

    # Find alias.column references
    for match in re.finditer(r"([`\w]+)\.([`\w]+)", sql_lower):
        alias = match.group(1).strip("`")
        col = match.group(2).strip("`")
        if alias in alias_map:
            table_name = alias_map[alias]
            table_info = table_stats.get(table_name)
            if table_info:
                columns = table_info.get("columns") or set()
                if columns and col not in columns:
                    return f"Column '{col}' not found in table '{table_name}'. Please adjust the query."

    return None


def parameterize_literals(sql_text: str) -> Tuple[str, dict[str, any]]:
    """Simple parameterization helper - identify literal values for potential parameterization.

    Note: This is a simplified implementation. For production, use a proper SQL parser.

    Args:
        sql_text: SQL statement

    Returns:
        Tuple of (sql_with_placeholders, parameters_dict)
    """
    # This is a placeholder - full implementation would parse and replace literals
    # For now, return as-is with empty params
    return sql_text, {}


def validate_sql(
    sql_text: str,
    allow_modification: bool = False,
    row_limit: Optional[int] = None,
    table_stats: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[str, List[str], Optional[str]]:
    """Comprehensive SQL validation and transformation.

    Args:
        sql_text: SQL statement to validate
        allow_modification: If True, allow DML/DDL
        row_limit: Maximum rows (None to use default from settings)
        table_stats: Table statistics for warnings

    Returns:
        Tuple of (validated_sql, warnings, error_message)

        - validated_sql: Potentially modified SQL with LIMIT applied
        - warnings: List of warning messages
        - error_message: Error message if validation failed, None otherwise
    """
    if not sql_text or not sql_text.strip():
        return sql_text, [], "Empty SQL statement"

    warnings = []
    validated_sql = sql_text

    # Check for forbidden operations
    forbidden_error = contains_forbidden(validated_sql, allow_modification)
    if forbidden_error:
        return validated_sql, warnings, forbidden_error

    # Enforce LIMIT for SELECT statements
    limit = row_limit or settings.query_row_limit
    if is_read_only(validated_sql):
        validated_sql, limit_applied = enforce_limit(validated_sql, limit)
        if limit_applied:
            warnings.append(f"Applied LIMIT {limit} to query")

        # Check for wildcard on big tables and unknown columns
        if table_stats:
            wildcard_warnings = ensure_no_wildcard_on_big_tables(validated_sql, table_stats)
            warnings.extend(wildcard_warnings)

            # Validate referenced columns against known schema (best effort)
            column_error = check_unknown_columns(validated_sql, table_stats)
            if column_error:
                return validated_sql, warnings, column_error

    return validated_sql, warnings, None

