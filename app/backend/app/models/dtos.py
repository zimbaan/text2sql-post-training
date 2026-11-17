"""Pydantic models for request/response DTOs."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Connection DTOs
class ConnectionRequest(BaseModel):
    """Request to create a database connection."""

    dialect: str = Field(..., description="Database dialect: postgresql, mysql, or sqlite")
    username: Optional[str] = Field(None, description="Database username (not needed for SQLite)")
    password: Optional[str] = Field(None, description="Database password (not needed for SQLite)")
    host: Optional[str] = Field(None, description="Database host (not needed for SQLite)")
    port: Optional[int] = Field(None, description="Database port (not needed for SQLite)")
    database: str = Field(..., description="Database name or file path (for SQLite)")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional connection options")

    class Config:
        json_schema_extra = {
            "example": {
                "dialect": "postgresql",
                "username": "myuser",
                "password": "mypassword",
                "host": "localhost",
                "port": 5432,
                "database": "mydb",
                "options": {},
            }
        }


class ConnectionResponse(BaseModel):
    """Response from connection creation."""

    connection_id: str = Field(..., description="Unique connection identifier")
    databases: List[str] = Field(default_factory=list, description="List of available databases")
    default_database: str = Field(..., description="Default database name")
    capabilities: Dict[str, Any] = Field(..., description="Connection capabilities")

    class Config:
        json_schema_extra = {
            "example": {
                "connection_id": "550e8400-e29b-41d4-a716-446655440000",
                "databases": ["mydb", "testdb"],
                "default_database": "mydb",
                "capabilities": {"readOnly": True, "dialect": "postgresql"},
            }
        }


# Schema DTOs
class ColumnInfo(BaseModel):
    """Column metadata."""

    name: str
    type: str
    nullable: bool = True
    default: Optional[str] = None


class ForeignKeyInfo(BaseModel):
    """Foreign key metadata."""

    column: str
    ref_table: str
    ref_column: str
    name: Optional[str] = None


class TableInfo(BaseModel):
    """Table metadata."""

    name: str
    columns: List[ColumnInfo]
    primary_key: List[str]
    foreign_keys: List[ForeignKeyInfo]
    approx_row_count: int = 0
    error: Optional[str] = None


class SchemaInfo(BaseModel):
    """Schema metadata."""

    name: str
    tables: List[TableInfo]


class DatabaseInfo(BaseModel):
    """Database metadata."""

    name: str
    schemas: List[SchemaInfo]


class SchemasResponse(BaseModel):
    """Schemas response wrapper to align with frontend expectations."""

    connection_id: str
    databases: List[DatabaseInfo]


# NLQ DTOs
class NLQRequest(BaseModel):
    """Request for natural language query."""

    user_query: str = Field(..., description="Natural language query")
    database: str = Field(..., description="Database name")
    schema: Optional[str] = Field(None, description="Schema name (optional)")
    table_scope: Optional[List[str]] = Field(None, description="Optional list of table names to scope to")
    allow_modification: bool = Field(False, description="Allow DML/DDL operations")
    return_sql_only: bool = Field(False, description="Return SQL without executing")
    confirm_execution: bool = Field(
        False,
        description=(
            "Execute non-read-only statements without additional confirmation. "
            "By default CREATE/UPDATE/DELETE will be returned for review first."
        ),
    )
    llm: Optional[str] = Field(
        None,
        alias="model",
        description=(
            "Model to use: the post-trained text-to-SQL model or one of the provider's models. "
            "Defaults to the server's configured model."
        ),
    )

    class Config:
        populate_by_name = True

        json_schema_extra = {
            "example": {
                "user_query": "Show me top 10 customers by revenue last quarter",
                "database": "appdb",
                "schema": "public",
                "table_scope": ["orders", "order_items", "customers"],
                "allow_modification": False,
                "return_sql_only": False,
                "confirm_execution": False,
                "model": "text2sql-qwen-0.5b-dpo",
            }
        }


class NLQResponse(BaseModel):
    """Response from natural language query."""

    sql: str = Field(..., description="Generated SQL statement")
    original_sql: Optional[str] = Field(None, description="Original SQL before safety modifications")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    reasoning: str = Field(..., description="LLM reasoning for the query")
    is_read_only: bool = Field(..., description="Whether the query is read-only")
    limit_applied: bool = Field(..., description="Whether LIMIT was applied")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    columns: Optional[List[str]] = Field(None, description="Result column names")
    rows: Optional[List[List[Any]]] = Field(None, description="Result rows")
    row_count: Optional[int] = Field(None, description="Number of rows returned")
    truncated: Optional[bool] = Field(None, description="Whether results were truncated")
    elapsed_ms: Optional[float] = Field(None, description="Query execution time in milliseconds")
    execution_error: Optional[str] = Field(None, description="Execution error if any")
    requires_confirmation: bool = Field(
        False,
        description="True when the statement modifies data/schema and needs user confirmation before execution",
    )
    confirmation_reason: Optional[str] = Field(
        None,
        description="Why confirmation is required or execution was skipped",
    )
    execution_skipped: bool = Field(
        False,
        description="True when execution was intentionally skipped (e.g., awaiting confirmation)",
    )
    clarification_needed: bool = Field(
        False,
        description="True when more details are required (e.g., table name/columns for CREATE TABLE)",
    )
    clarification_message: Optional[str] = Field(
        None,
        description="Message describing what details are needed to proceed safely",
    )
    generated_by: Optional[str] = Field(None, description="Model that generated the SQL")


class NLQExplainResponse(BaseModel):
    """Response from explain endpoint (SQL only, no execution)."""

    sql: str
    original_sql: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str
    is_read_only: bool
    limit_applied: bool
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)
    generated_by: Optional[str] = None


class ModelInfo(BaseModel):
    """Model available for SQL generation."""

    name: str
    is_default: bool = False
    is_finetuned: bool = Field(
        False, description="True for the post-trained text-to-SQL model served by this backend"
    )


class ModelsResponse(BaseModel):
    """Response listing available Ollama models."""

    models: List[ModelInfo]
    default_model: str


class QueryHistoryEntry(BaseModel):
    """Single query history entry."""

    timestamp: float
    user_query: str
    sql: str
    row_count: int
    duration_ms: float
    warnings: List[str]
    confidence: float


class QueryHistoryResponse(BaseModel):
    """Response with query history."""

    queries: List[QueryHistoryEntry]


# Visualization DTOs
class VisualizeRequest(BaseModel):
    """Request for visualization data."""

    tables: List[str] = Field(..., description="List of table names to visualize")
    schema: Optional[str] = Field(None, description="Schema name (optional)")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "tables": ["orders", "customers", "order_items"],
                "schema": "public",
            }
        }


class GraphNodeColumn(BaseModel):
    """Column info for graph nodes."""

    name: str
    type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    ref_table: Optional[str] = None
    ref_column: Optional[str] = None


class GraphNode(BaseModel):
    """Graph node for visualization."""

    id: str
    label: str
    columns: List[GraphNodeColumn] = Field(default_factory=list)


class GraphEdge(BaseModel):
    """Graph edge for visualization."""

    source: str
    target: str
    label: str
    source_column: Optional[str] = None
    target_column: Optional[str] = None
    cardinality: Optional[str] = None  # e.g., "N:1"


class VisualizeResponse(BaseModel):
    """Response with visualization graph data."""

    nodes: List[GraphNode]
    edges: List[GraphEdge]


# Export DTOs
class ExportCSVRequest(BaseModel):
    """Request to export query results as CSV."""

    sql: str = Field(..., description="SQL query to execute")
    filename: str = Field(default="report.csv", description="Output filename")

    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT * FROM customers LIMIT 100",
                "filename": "customers.csv",
            }
        }


# Error DTOs
class ErrorDetail(BaseModel):
    """Error detail information."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response model."""

    error: ErrorDetail


# Settings DTOs
class SafeModeRequest(BaseModel):
    """Request to update safe mode flag."""

    enabled: bool = Field(..., description="Whether safe mode (read-only enforcement) is enabled")


class SafeModeResponse(BaseModel):
    """Response with current safe mode flag."""

    enabled: bool = Field(..., description="Safe mode enabled flag")

