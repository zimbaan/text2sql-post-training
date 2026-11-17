"""Natural Language to SQL service using a configurable LLM provider."""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.core.finetuned import get_finetuned_model, is_finetuned_model
from app.core.llm import BaseLLMClient, get_llm_client
from app.core.runtime_flags import is_safe_mode_enabled
from app.core.sql_safe import is_read_only, validate_sql
from app.db.introspect import format_schema_ddl, format_schema_summary_for_llm
from app.db.manager import ConnectionManager, get_connection_manager

logger = logging.getLogger(__name__)
settings = get_settings()


# Few-shot examples for LLM prompts
POSTGRESQL_EXAMPLES = """
Example 1:
User: "Show me top 10 customers by revenue last quarter"
JSON: {
  "sql": "SELECT c.customer_id, c.name, SUM(oi.quantity * oi.price) as revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id WHERE o.order_date >= DATE_TRUNC('quarter', CURRENT_DATE) - INTERVAL '3 months' AND o.order_date < DATE_TRUNC('quarter', CURRENT_DATE) GROUP BY c.customer_id, c.name ORDER BY revenue DESC LIMIT 10",
  "parameters": {},
  "reasoning": "Joins customers, orders, and order_items. Filters for last quarter using DATE_TRUNC. Groups and sums revenue.",
  "is_read_only": true,
  "limit_applied": true,
  "confidence": 0.9
}

Example 2:
User: "Count orders by status"
JSON: {
  "sql": "SELECT status, COUNT(*) as order_count FROM orders GROUP BY status",
  "parameters": {},
  "reasoning": "Simple aggregation by status column.",
  "is_read_only": true,
  "limit_applied": false,
  "confidence": 0.95
}

Example 3:
User: "Find customers who placed orders in the last 30 days"
JSON: {
  "sql": "SELECT DISTINCT c.customer_id, c.name, c.email FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_date >= CURRENT_DATE - INTERVAL '30 days' LIMIT 1000",
  "parameters": {},
  "reasoning": "Joins customers and orders, filters by date, uses DISTINCT to avoid duplicates.",
  "is_read_only": true,
  "limit_applied": true,
  "confidence": 0.85
}
"""

MYSQL_EXAMPLES = """
Example:
User: "Get first 20 products sorted by price"
JSON: {
  "sql": "SELECT product_id, name, price FROM products ORDER BY price ASC LIMIT 20",
  "parameters": {},
  "reasoning": "Simple SELECT with ORDER BY and LIMIT. MySQL uses LIMIT not FETCH FIRST.",
  "is_read_only": true,
  "limit_applied": true,
  "confidence": 0.9
}
"""

SQLITE_EXAMPLES = """
Example:
User: "List all employees"
JSON: {
  "sql": "SELECT employee_id, name, department FROM employees LIMIT 1000",
  "parameters": {},
  "reasoning": "Simple SELECT with LIMIT for safety.",
  "is_read_only": true,
  "limit_applied": true,
  "confidence": 0.95
}
"""


def get_examples_for_dialect(dialect: str) -> str:
    """Get few-shot examples for dialect.

    Args:
        dialect: Database dialect

    Returns:
        Examples string
    """
    if dialect in ("postgresql", "postgres"):
        return POSTGRESQL_EXAMPLES
    elif dialect in ("mysql", "mariadb"):
        return MYSQL_EXAMPLES
    elif dialect == "sqlite":
        return SQLITE_EXAMPLES
    else:
        return POSTGRESQL_EXAMPLES  # Default


def build_system_prompt(
    dialect: str,
    database: str,
    schema: Optional[str],
    table_overview: str,
    limit: int,
) -> str:
    """Build system prompt for LLM.

    Args:
        dialect: Database dialect
        database: Database name
        schema: Schema name (optional)
        table_overview: Formatted table overview text
        limit: Row limit to apply

    Returns:
        System prompt string
    """
    prompt = f"""You are a meticulous NL->SQL planner for a relational database.

CONTEXT:
- Dialect: {dialect} ({dialect})
- Database: {database}
- Schema: {schema or 'default'}

- Table overview:
{table_overview}

RULES:
1) Always include a FROM clause using only the tables listed in the scope/overview. Never emit SQL without FROM.
2) If the table is unclear, default to the first table in the provided scope and state the assumption in reasoning.
3) Use ONLY columns listed in the overview; never invent column names. If the user asks for a field not present, choose the closest matching existing column (e.g., name/full_name) and note the assumption in reasoning.
4) Build joins using the foreign keys provided in the overview. If no FK is listed, join on matching key columns (e.g., ride_id, driver_id, customer_id) between scoped tables. Avoid Cartesian products.
5) When the requested fields are on related tables (e.g., customer or driver info for payments), traverse the FK chain instead of inventing columns on the base table. Example: payments -> rides (ride_id) -> customers (customer_id), payments -> rides (ride_id) -> drivers (driver_id).
5) Produce a SINGLE, SAFE SQL statement that answers the user question.
6) Prefer explicit column lists over SELECT *.
7) Always include a LIMIT {limit} for SELECT unless an aggregate returns exactly 1 row.
8) NEVER use DDL or DML unless allow_modification=true.
9) Use dialect-correct date/time/window/limit syntax.
10) If ambiguity exists, pick a reasonable assumption and note it in reasoning.
11) Use COALESCE for nullable measures when needed; cast types safely.
12) Return STRICT JSON ONLY with keys:
   - sql: string
   - parameters: object (key:string -> value:literal)
   - reasoning: string (concise)
   - is_read_only: boolean
   - limit_applied: boolean
   - confidence: number between 0 and 1

No prose outside JSON.

{get_examples_for_dialect(dialect)}
"""
    return prompt


def build_user_prompt(
    user_query: str,
    table_scope: Optional[List[str]],
    safe_mode: bool,
    timezone: Optional[str] = None,
    extra_hint: Optional[str] = None,
) -> str:
    """Build user prompt for LLM.

    Args:
        user_query: User's natural language query
        table_scope: Optional list of table names to scope to
        safe_mode: Whether safe mode is enabled
        timezone: Optional timezone hint

    Returns:
        User prompt string
    """
    table_hint = ", ".join(table_scope) if table_scope else "all tables"
    tz_hint = timezone or "UTC"
    extra = f"\n- {extra_hint}" if extra_hint else ""
    prompt = f"""User request:

{user_query}

Additional hints:
- Table scope: {table_hint}
- You must pick tables ONLY from the scope above and include them in a FROM clause. If unsure, default to the first scoped table and note the assumption.
- Use ONLY the columns listed in the overview; do not invent new columns. If a requested field is not present, use the closest matching existing column (e.g., name/full_name) and state the assumption.
- Use the foreign keys listed in the overview to form joins. If none are listed, join on matching *_id keys between the scoped tables and note the assumption.
- If you need customer/driver details for payments, join payments -> rides on ride_id, then rides -> customers on customer_id and rides -> drivers on driver_id instead of assuming those columns exist on payments.
- Timezone: {tz_hint}
- Safe mode: {safe_mode}
{extra}

Return STRICT JSON only.
"""
    return prompt


class NL2SQLService:
    """Service for converting natural language to SQL."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None, connection_manager: Optional[ConnectionManager] = None):
        """Initialize NL2SQL service.

        Args:
            llm_client: LLM client (defaults to global instance based on provider)
            connection_manager: Connection manager (defaults to global instance)
        """
        self.llm_client = llm_client or get_llm_client()
        self.connection_manager = connection_manager or get_connection_manager()
        self.query_history: Dict[str, List[dict]] = {}  # connection_id -> list of queries

    async def generate_sql(
        self,
        connection_id: str,
        user_query: str,
        database: str,
        schema: Optional[str] = None,
        table_scope: Optional[List[str]] = None,
        allow_modification: bool = False,
        return_sql_only: bool = False,
        confirm_execution: bool = False,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate SQL from natural language query.

        Args:
            connection_id: Connection identifier
            user_query: User's natural language query
            database: Database name
            schema: Schema name (optional)
            table_scope: Optional list of table names to scope to
            allow_modification: Whether to allow DML/DDL
            return_sql_only: If True, return SQL without executing
            confirm_execution: Execute non-read-only statements immediately when True
            user_id: Optional user identifier to persist history
            model: Model to use; the post-trained text-to-SQL model or one of the provider's models.
                Defaults to the provider's configured model.

        Returns:
            Dictionary with SQL, execution results, or error

        Raises:
            ValueError: If connection not found or LLM fails
        """
        start_time = time.time()

        # Get connection
        conn_info = self.connection_manager.get_connection(connection_id)
        if not conn_info:
            raise ValueError(f"Connection {connection_id} not found or expired")

        # SQLite does not use schemas; avoid passing a schema name
        effective_schema = None if conn_info.dialect == "sqlite" else schema
        safe_mode_enabled = is_safe_mode_enabled()

        use_finetuned = is_finetuned_model(model)
        system_prompt = user_prompt = ""

        if use_finetuned:
            # The post-trained model sees the schema as CREATE TABLE statements, exactly as in training,
            # and answers with plain SQL.
            finetuned = get_finetuned_model()
            schema_ddl = format_schema_ddl(conn_info.engine, effective_schema, table_scope)
            try:
                sql, _raw, finetuned_confidence = await finetuned.generate_sql(schema_ddl, user_query)
            except Exception as e:
                logger.error(f"Fine-tuned model generation failed: {e}")
                raise ValueError(f"Failed to generate SQL from query: {e}") from e
            parameters = {}
            reasoning = (
                "Generated by the post-trained text-to-SQL model (Qwen2.5-Coder-0.5B with SFT + DPO), "
                "from the CREATE TABLE statements of the tables in scope."
            )
            if conn_info.dialect != "sqlite":
                reasoning += " It was trained on SQLite, so check dialect-specific syntax."
            is_read_only_flag = True
            limit_applied = False
            confidence = round(finetuned_confidence, 3) if finetuned_confidence is not None else 0.0
        else:
            # Get schema overview
            table_overview = format_schema_summary_for_llm(
                conn_info.engine, database, effective_schema, table_scope
            )

            # Build prompts
            system_prompt = build_system_prompt(
                conn_info.dialect,
                database,
                effective_schema,
                table_overview,
                settings.query_row_limit,
            )
            user_prompt = build_user_prompt(
                user_query,
                table_scope,
                safe_mode_enabled and not allow_modification,
            )

            # Call LLM
            try:
                planner_result = await self.llm_client.generate_json(
                    user_prompt, system_prompt=system_prompt, model=model
                )
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                raise ValueError(f"Failed to generate SQL from query: {e}") from e

            # Extract SQL and metadata
            sql = planner_result.get("sql", "")
            parameters = planner_result.get("parameters", {})
            reasoning = planner_result.get("reasoning", "")
            is_read_only_flag = planner_result.get("is_read_only", True)
            limit_applied = planner_result.get("limit_applied", False)
            confidence = planner_result.get("confidence", 0.0)

        if not sql:
            raise ValueError("LLM did not return SQL statement")

        # Validate and sanitize SQL
        table_stats = {}
        if table_scope:
            # Build table stats for warnings (simplified)
            from app.db.introspect import introspect_tables
            tables_info = introspect_tables(conn_info.engine, effective_schema, table_scope)
            table_stats = {
                table["name"].lower(): {
                    "approx_row_count": table.get("approx_row_count", 0),
                    "columns": {col["name"].lower() for col in table.get("columns", [])},
                }
                for table in tables_info
                if "error" not in table
            }

        def run_validation(candidate_sql: str):
            return validate_sql(
                candidate_sql,
                allow_modification=allow_modification or not safe_mode_enabled,
                row_limit=settings.query_row_limit,
                table_stats=table_stats if table_stats else None,
            )

        validated_sql, warnings, error = run_validation(sql)

        # If the LLM forgot a FROM clause, retry once with a hard hint
        if not use_finetuned and error and "missing a from clause" in str(error).lower():
            retry_hint = ""
            if table_scope:
                retry_hint = (
                    f"Your previous output lacked a FROM clause. Use a FROM with the scoped tables: {', '.join(table_scope)}. "
                    "Join via FKs if needed; do NOT invent columns or tables."
                )
            retry_user_prompt = build_user_prompt(
                user_query,
                table_scope,
                safe_mode_enabled and not allow_modification,
                extra_hint=retry_hint or "Your last attempt had no FROM. Include a FROM with scoped tables."
            )
            try:
                planner_retry = await self.llm_client.generate_json(
                    retry_user_prompt, system_prompt=system_prompt, model=model
                )
                retry_sql = planner_retry.get("sql", "")
                if retry_sql:
                    sql = retry_sql
                    parameters = planner_retry.get("parameters", parameters)
                    reasoning = planner_retry.get("reasoning", reasoning)
                    is_read_only_flag = planner_retry.get("is_read_only", is_read_only_flag)
                    limit_applied = planner_retry.get("limit_applied", limit_applied)
                    confidence = planner_retry.get("confidence", confidence)
                    validated_sql, warnings, error = run_validation(sql)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Retry after missing FROM failed: {e}")

        if error:
            raise ValueError(f"SQL validation failed: {error}")

        # Build result
        result = {
            "sql": validated_sql,
            "original_sql": sql,
            "parameters": parameters,
            "reasoning": reasoning,
            "is_read_only": is_read_only_flag,
            "limit_applied": limit_applied,
            "confidence": confidence,
            "warnings": warnings,
            "requires_confirmation": False,
            "confirmation_reason": None,
            "execution_skipped": False,
            "clarification_needed": False,
            "clarification_message": None,
            "generated_by": model if use_finetuned else (model or getattr(self.llm_client, "default_model", None)),
        }

        query_read_only = is_read_only(validated_sql)
        result["is_read_only"] = query_read_only if use_finetuned else is_read_only_flag
        clarification_message = None

        if not query_read_only:
            result["requires_confirmation"] = True
            result["confirmation_reason"] = (
                "This statement modifies data or schema. Confirm execution to proceed."
            )
            lower_query = user_query.lower()
            if "create table" in lower_query:
                clarification_message = (
                    "Provide the target table name and the full column list with data types. "
                    "If unsure, suggest the column names, data types, and primary key."
                )
            elif any(keyword in lower_query for keyword in ["update", "delete", "drop"]):
                clarification_message = (
                    "Double-check affected tables, filters/WHERE clause, and expected row counts "
                    "before confirming execution."
                )

        if clarification_message:
            result["clarification_needed"] = True
            result["clarification_message"] = clarification_message

        # Execute query if requested
        if not return_sql_only and (query_read_only or confirm_execution):
            try:
                exec_start = time.time()
                columns, rows, row_count = self.connection_manager.execute_query(
                    connection_id, validated_sql, parameters
                )
                exec_elapsed = (time.time() - exec_start) * 1000  # ms

                result.update({
                    "columns": columns,
                    "rows": rows,
                    "row_count": row_count,
                    "truncated": row_count >= settings.query_row_limit,
                    "elapsed_ms": round(exec_elapsed, 2),
                })
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                result["execution_error"] = str(e)
                result["columns"] = []
                result["rows"] = []
                result["row_count"] = 0
        elif not return_sql_only:
            # Modification statement without explicit confirmation
            result["execution_skipped"] = True
            result["execution_error"] = None
            result["columns"] = []
            result["rows"] = []
            result["row_count"] = 0

        # Store in history
        elapsed_ms = (time.time() - start_time) * 1000
        self.add_to_history(
            connection_id,
            {
                "timestamp": time.time(),
                "user_query": user_query,
                "sql": validated_sql,
                "row_count": result.get("row_count", 0),
                "duration_ms": round(elapsed_ms, 2),
                "warnings": warnings,
                "confidence": confidence,
                "requires_confirmation": result.get("requires_confirmation", False),
                "execution_skipped": result.get("execution_skipped", False),
                "model": result.get("generated_by"),
            },
            user_id=user_id,
        )

        return result

    def add_to_history(self, connection_id: str, query_info: dict, user_id: Optional[str] = None):
        """Add query to history.

        Args:
            connection_id: Connection identifier
            query_info: Query information dictionary
        """
        if connection_id not in self.query_history:
            self.query_history[connection_id] = []

        self.query_history[connection_id].append(query_info)

        # Keep only last 50 queries
        if len(self.query_history[connection_id]) > 50:
            self.query_history[connection_id] = self.query_history[connection_id][-50:]

        # Persist to Mongo if a user is provided
        if user_id:
            from app.db.history import add_history_entry
            # Fire and forget; caller can await if desired
            import asyncio

            asyncio.create_task(
                add_history_entry(
                    user_id,
                    {
                        **query_info,
                        "connection_id": connection_id,
                        "user_query": query_info.get("user_query"),
                        "sql": query_info.get("sql"),
                        "warnings": query_info.get("warnings", []),
                        "row_count": query_info.get("row_count", 0),
                        "elapsed_ms": query_info.get("duration_ms"),
                        "status": "success",
                    },
                )
            )

    def get_history(self, connection_id: str) -> List[dict]:
        """Get query history for a connection.

        Args:
            connection_id: Connection identifier

        Returns:
            List of query history entries
        """
        return self.query_history.get(connection_id, [])


# Global service instance
_nl2sql_service: Optional[NL2SQLService] = None


def get_nl2sql_service() -> NL2SQLService:
    """Get or create global NL2SQL service instance."""
    global _nl2sql_service
    if _nl2sql_service is None:
        _nl2sql_service = NL2SQLService()
    return _nl2sql_service

