"""Database schema introspection using SQLAlchemy Inspector."""

import logging
from typing import Dict, List, Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def get_approximate_row_count(engine: Engine, schema: Optional[str], table_name: str) -> int:
    """Get approximate row count for a table (best effort, fast).

    Args:
        engine: SQLAlchemy engine
        schema: Schema name (optional)
        table_name: Table name

    Returns:
        Approximate row count, 0 on error
    """
    dialect_name = engine.dialect.name

    try:
        with engine.connect() as conn:
            if dialect_name == "postgresql":
                # PostgreSQL: use reltuples from pg_class
                full_table = f"{schema}.{table_name}" if schema else table_name
                query = text(
                    """
                    SELECT reltuples::bigint AS estimate
                    FROM pg_class
                    WHERE oid = :table_name::regclass
                    """
                )
                result = conn.execute(query, {"table_name": full_table})
                row = result.fetchone()
                if row and row[0]:
                    return int(row[0])
            elif dialect_name in ("mysql", "mariadb"):
                # MySQL: use TABLE_ROWS from information_schema
                query = text(
                    """
                    SELECT TABLE_ROWS
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = :schema
                    AND TABLE_NAME = :table_name
                    """
                )
                schema_name = schema or conn.execute(text("SELECT DATABASE()")).scalar()
                result = conn.execute(query, {"schema": schema_name, "table_name": table_name})
                row = result.fetchone()
                if row and row[0]:
                    return int(row[0])
            elif dialect_name == "sqlite":
                # SQLite: use COUNT(*) - this is slower but accurate
                full_table = f"{schema}.{table_name}" if schema else table_name
                query = text(f'SELECT COUNT(*) FROM "{full_table}"')
                result = conn.execute(query)
                row = result.fetchone()
                if row and row[0]:
                    return int(row[0])

            # Fallback: try COUNT(*)
            full_table = f"{schema}.{table_name}" if schema else table_name
            query = text(f'SELECT COUNT(*) FROM "{full_table}"')
            result = conn.execute(query)
            row = result.fetchone()
            if row:
                return int(row[0]) if row[0] else 0
    except Exception as e:
        logger.warning(f"Could not get row count for {table_name}: {e}")

    return 0


def introspect_table(engine: Engine, schema: Optional[str], table_name: str) -> dict:
    """Introspect a single table.

    Args:
        engine: SQLAlchemy engine
        schema: Schema name (optional)
        table_name: Table name

    Returns:
        Dictionary with table metadata
    """
    inspector = inspect(engine)

    # Get columns
    columns_info = inspector.get_columns(table_name, schema=schema)
    columns = [
        {
            "name": col["name"],
            "type": str(col["type"]),
            "nullable": col.get("nullable", True),
            "default": str(col["default"]) if col.get("default") is not None else None,
        }
        for col in columns_info
    ]

    # Get primary key
    pk_constraint = inspector.get_pk_constraint(table_name, schema=schema)
    primary_key = pk_constraint.get("constrained_columns", []) if pk_constraint else []

    # Get foreign keys
    foreign_keys = []
    fks = inspector.get_foreign_keys(table_name, schema=schema)
    for fk in fks:
        constrained_columns = fk.get("constrained_columns", [])
        referred_table = fk.get("referred_table", "")
        referred_columns = fk.get("referred_columns", [])
        if constrained_columns and referred_table:
            # Create entry for each column pair
            for col, ref_col in zip(constrained_columns, referred_columns):
                foreign_keys.append(
                    {
                        "column": col,
                        "ref_table": referred_table,
                        "ref_column": ref_col,
                        "name": fk.get("name"),
                    }
                )

    # Get approximate row count
    approx_row_count = get_approximate_row_count(engine, schema, table_name)

    return {
        "name": table_name,
        "columns": columns,
        "primary_key": primary_key,
        "foreign_keys": foreign_keys,
        "approx_row_count": approx_row_count,
    }


def normalize_table_names(engine: Engine, schema: Optional[str], table_names: List[str]) -> List[str]:
    """Strip the schema prefix the UI adds to table names ("public.orders", "default.singer").

    The UI scopes tables as "<schema>.<table>". For SQLite the schema shows up as "default" (there are no
    schemas) and for MySQL it is the database name, so any of those prefixes is removed.
    """
    prefixes = {"default", "main"}
    if schema:
        prefixes.add(schema.lower())
    if engine.url.database:
        prefixes.add(str(engine.url.database).lower())
    normalized = []
    for name in table_names:
        head, sep, tail = name.partition(".")
        normalized.append(tail if sep and head.lower() in prefixes else name)
    return normalized


def introspect_tables(
    engine: Engine, schema: Optional[str] = None, table_names: Optional[List[str]] = None
) -> List[dict]:
    """Introspect tables in a schema.

    Args:
        engine: SQLAlchemy engine
        schema: Schema name (optional)
        table_names: Optional list of table names to introspect (if None, all tables)

    Returns:
        List of table metadata dictionaries
    """
    inspector = inspect(engine)

    if table_names:
        table_names = normalize_table_names(engine, schema, table_names)

    # Get all tables in schema
    if table_names is None:
        table_names = inspector.get_table_names(schema=schema)

    tables = []
    for table_name in table_names:
        try:
            table_info = introspect_table(engine, schema, table_name)
            tables.append(table_info)
        except Exception as e:
            logger.warning(f"Error introspecting table {table_name}: {e}")
            # Still include basic info
            tables.append({"name": table_name, "error": str(e)})

    return tables


def introspect_schema(engine: Engine, schema_name: Optional[str] = None) -> dict:
    """Introspect a schema (all tables).

    Args:
        engine: SQLAlchemy engine
        schema_name: Schema name (optional, defaults to default schema)

    Returns:
        Dictionary with schema metadata
    """
    tables = introspect_tables(engine, schema_name)

    return {
        "name": schema_name or "default",
        "tables": tables,
    }


def introspect_database(engine: Engine, database_name: str) -> dict:
    """Introspect all schemas in a database.

    Args:
        engine: SQLAlchemy engine
        database_name: Database name

    Returns:
        Dictionary with database metadata
    """
    inspector = inspect(engine)
    dialect_name = engine.dialect.name

    schemas_list = []
    if dialect_name == "postgresql":
        # PostgreSQL: get all schemas
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                    ORDER BY schema_name
                    """
                )
            )
            schema_names = [row[0] for row in result]
    elif dialect_name in ("mysql", "mariadb"):
        # MySQL: use DATABASE() as schema
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DATABASE()"))
            schema_name = result.scalar()
            schema_names = [schema_name] if schema_name else []
    elif dialect_name == "sqlite":
        # SQLite: no schemas, use None
        schema_names = [None]
    else:
        # Default: try to get schemas
        try:
            schema_names = inspector.get_schema_names()
        except Exception:
            schema_names = [None]

    # Introspect each schema
    for schema_name in schema_names:
        try:
            schema_info = introspect_schema(engine, schema_name)
            schemas_list.append(schema_info)
        except Exception as e:
            logger.warning(f"Error introspecting schema {schema_name}: {e}")

    return {
        "name": database_name,
        "schemas": schemas_list,
    }


def get_databases(engine: Engine) -> List[str]:
    """Get list of databases (for dialects that support multiple databases).

    Args:
        engine: SQLAlchemy engine

    Returns:
        List of database names
    """
    dialect_name = engine.dialect.name

    if dialect_name == "postgresql":
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT datname
                    FROM pg_database
                    WHERE datistemplate = false
                    ORDER BY datname
                    """
                )
            )
            return [row[0] for row in result]
    elif dialect_name in ("mysql", "mariadb"):
        with engine.connect() as conn:
            result = conn.execute(text("SHOW DATABASES"))
            return [row[0] for row in result if row[0] not in ("information_schema", "performance_schema", "sys", "mysql")]
    elif dialect_name == "sqlite":
        # SQLite doesn't support multiple databases
        return ["main"]

    return []


def _clean_ddl(sql: str) -> str:
    lines = [line.strip() for line in sql.strip().splitlines() if line.strip()]
    return "\n".join(lines).rstrip(";") + ";"


def format_schema_ddl(
    engine: Engine, schema: Optional[str] = None, table_scope: Optional[List[str]] = None
) -> str:
    """Schema as CREATE TABLE statements: the format the post-trained model was trained on.

    SQLite keeps each table's original DDL, which is used as-is. Other databases get equivalent
    CREATE TABLE statements built from introspection (columns, types, primary and foreign keys).
    """
    scoped = normalize_table_names(engine, schema, table_scope) if table_scope else None
    wanted = {t.lower() for t in scoped} if scoped else None

    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT name, sql FROM sqlite_master WHERE type = 'table' "
                    "AND name NOT LIKE 'sqlite_%' AND sql IS NOT NULL ORDER BY rowid"
                )
            ).fetchall()
        blocks = [_clean_ddl(ddl) for name, ddl in rows if wanted is None or name.lower() in wanted]
        return "\n\n".join(blocks)

    tables = introspect_tables(engine, schema, scoped)
    blocks = []
    for table in tables:
        if "error" in table:
            continue
        lines = []
        for col in table.get("columns", []):
            null = "" if col.get("nullable", True) else " NOT NULL"
            lines.append(f"{col['name']} {col['type']}{null}")
        if table.get("primary_key"):
            lines.append(f"PRIMARY KEY ({', '.join(table['primary_key'])})")
        for fk in table.get("foreign_keys", []):
            lines.append(f"FOREIGN KEY ({fk['column']}) REFERENCES {fk['ref_table']} ({fk['ref_column']})")
        blocks.append(f"CREATE TABLE {table['name']} (\n" + ",\n".join(lines) + "\n);")
    return "\n\n".join(blocks)


def format_schema_summary_for_llm(
    engine: Engine, database: str, schema: Optional[str], table_scope: Optional[List[str]] = None
) -> str:
    """Format schema information as compact text for LLM context.

    Args:
        engine: SQLAlchemy engine
        database: Database name
        schema: Schema name (optional)
        table_scope: Optional list of table names to include

    Returns:
        Formatted text summary
    """
    if table_scope:
        tables = introspect_tables(engine, schema, table_scope)
        schema_info = {"name": schema or "default", "tables": tables}
    else:
        schema_info = introspect_schema(engine, schema)

    lines = [f"Database: {database}", f"Schema: {schema_info['name']}", ""]

    for table in schema_info.get("tables", []):
        if "error" in table:
            lines.append(f"Table: {table['name']} (error: {table['error']})")
            continue

        lines.append(f"Table: {table['name']} (~{table.get('approx_row_count', 0):,} rows)")

        # Columns
        col_names_types = [
            f"{col['name']} ({col['type']})"
            + (" NULL" if col.get("nullable") else " NOT NULL")
            for col in table.get("columns", [])
        ]
        lines.append(f"  Columns: {', '.join(col_names_types)}")

        # Primary key
        if table.get("primary_key"):
            lines.append(f"  Primary Key: {', '.join(table['primary_key'])}")

        # Foreign keys
        if table.get("foreign_keys"):
            fk_strs = [
                f"{fk['column']} -> {fk['ref_table']}.{fk['ref_column']}"
                for fk in table["foreign_keys"]
            ]
            lines.append(f"  Foreign Keys: {', '.join(fk_strs)}")

        lines.append("")

    return "\n".join(lines)

