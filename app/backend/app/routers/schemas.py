"""Schema introspection router."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.db.introspect import introspect_database, introspect_tables
from app.db.manager import get_connection_manager
from app.models.dtos import DatabaseInfo, ErrorResponse, SchemasResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schemas", tags=["Schemas"])


@router.get("/{connection_id}", response_model=SchemasResponse)
async def get_schemas(connection_id: str) -> SchemasResponse:
    """Get all databases, schemas, and tables for a connection.

    Args:
        connection_id: Connection identifier

    Returns:
        Database metadata with schemas and tables

    Raises:
        HTTPException: If connection not found or introspection fails
    """
    manager = get_connection_manager()
    conn_info = manager.get_connection(connection_id)

    if not conn_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CONNECTION_NOT_FOUND",
                    "message": f"Connection {connection_id} not found or expired",
                    "details": None,
                }
            },
        )

    try:
        # Get default database
        from app.db.introspect import get_databases

        databases = get_databases(conn_info.engine)
        database_name = databases[0] if databases else conn_info.database

        # Introspect database
        db_info = introspect_database(conn_info.engine, database_name)

        database_payload = {
            "name": db_info["name"],
            "schemas": [
                {
                    "name": schema["name"],
                    "tables": [
                        {
                            "name": table["name"],
                            "columns": [
                                {
                                    "name": col["name"],
                                    "type": col["type"],
                                    "nullable": col.get("nullable", True),
                                    "default": col.get("default"),
                                }
                                for col in table.get("columns", [])
                            ],
                            "primary_key": table.get("primary_key", []),
                            "foreign_keys": [
                                {
                                    "column": fk["column"],
                                    "ref_table": fk["ref_table"],
                                    "ref_column": fk["ref_column"],
                                    "name": fk.get("name"),
                                }
                                for fk in table.get("foreign_keys", [])
                            ],
                            "approx_row_count": table.get("approx_row_count", 0),
                        }
                        for table in schema.get("tables", [])
                    ],
                }
                for schema in db_info.get("schemas", [])
            ],
        }

        # Wrap to align with frontend (expects { connection_id, databases: [...] })
        return SchemasResponse(connection_id=connection_id, databases=[database_payload])
    except Exception as e:
        logger.error(f"Schema introspection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTROSPECTION_FAILED",
                    "message": f"Failed to introspect database: {e}",
                    "details": None,
                }
            },
        )


@router.get("/{connection_id}/tables", response_model=List[dict])
async def get_tables(
    connection_id: str,
    tables: Optional[str] = Query(None, description="Comma-separated list of table names"),
    schema: Optional[str] = Query(None, description="Schema name"),
) -> List[dict]:
    """Get metadata for specific tables.

    Args:
        connection_id: Connection identifier
        tables: Comma-separated list of table names (optional, returns all if not provided)
        schema: Schema name (optional)

    Returns:
        List of table metadata dictionaries

    Raises:
        HTTPException: If connection not found or introspection fails
    """
    manager = get_connection_manager()
    conn_info = manager.get_connection(connection_id)

    if not conn_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CONNECTION_NOT_FOUND",
                    "message": f"Connection {connection_id} not found or expired",
                    "details": None,
                }
            },
        )

    try:
        # Parse table names
        table_names = None
        if tables:
            table_names = [t.strip() for t in tables.split(",")]

        # Introspect tables
        tables_info = introspect_tables(conn_info.engine, schema, table_names)

        # Format response
        return [
            {
                "name": table["name"],
                "columns": [
                    {
                        "name": col["name"],
                        "type": col["type"],
                        "nullable": col.get("nullable", True),
                        "default": col.get("default"),
                    }
                    for col in table.get("columns", [])
                ],
                "primary_key": table.get("primary_key", []),
                "foreign_keys": [
                    {
                        "column": fk["column"],
                        "ref_table": fk["ref_table"],
                        "ref_column": fk["ref_column"],
                        "name": fk.get("name"),
                    }
                    for fk in table.get("foreign_keys", [])
                ],
                "approx_row_count": table.get("approx_row_count", 0),
                "error": table.get("error"),
            }
            for table in tables_info
        ]
    except Exception as e:
        logger.error(f"Table introspection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTROSPECTION_FAILED",
                    "message": f"Failed to introspect tables: {e}",
                    "details": None,
                }
            },
        )

