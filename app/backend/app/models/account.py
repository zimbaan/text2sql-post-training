"""Account-related models for saved connections and history."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SavedConnectionCreate(BaseModel):
    """Request to save a reusable database connection."""

    name: str = Field(..., description="Friendly name for this connection")
    dialect: str = Field(..., description="Database dialect")
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class SavedConnectionPublic(BaseModel):
    """Saved connection returned to clients (secrets masked)."""

    id: str
    name: str
    dialect: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    database: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    last_used_at: Optional[datetime] = None


class QueryHistoryItem(BaseModel):
    """Single history record."""

    id: str
    user_query: str
    sql: str
    database: Optional[str] = None
    schema: Optional[str] = None
    table_scope: Optional[List[str]] = None
    is_read_only: bool = True
    requires_confirmation: bool = False
    execution_skipped: bool = False
    row_count: int = 0
    elapsed_ms: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    status: str = "success"
    error: Optional[str] = None
    created_at: datetime


class QueryHistoryResponse(BaseModel):
    """Paginated history response."""

    items: List[QueryHistoryItem]
    total: int
