"""CSV export router."""

import logging

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.sql_safe import validate_sql
from app.db.manager import get_connection_manager
from app.models.dtos import ExportCSVRequest, ErrorResponse
from app.utils.csv import generate_csv

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/export", tags=["Export"])


@router.post("/csv/{connection_id}")
async def export_csv(connection_id: str, request: ExportCSVRequest) -> StreamingResponse:
    """Export query results as CSV.

    Args:
        connection_id: Connection identifier
        request: Export request with SQL and filename

    Returns:
        Streaming CSV response

    Raises:
        HTTPException: If connection not found, SQL validation fails, or execution fails
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

    # Validate SQL
    validated_sql, warnings, error = validate_sql(
        request.sql,
        allow_modification=False,  # Always read-only for export
        row_limit=settings.query_row_limit,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "SQL_VALIDATION_FAILED",
                    "message": error,
                    "details": {"warnings": warnings},
                }
            },
        )

    # Execute query
    try:
        columns, rows, row_count = manager.execute_query(connection_id, validated_sql)

        # Generate CSV
        csv_generator = generate_csv(columns, rows)

        # Create streaming response
        response = StreamingResponse(
            csv_generator,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{request.filename}"',
            },
        )
        return response
    except ValueError as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "QUERY_EXECUTION_FAILED",
                    "message": str(e),
                    "details": None,
                }
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error exporting CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to export CSV",
                    "details": {"error": str(e)},
                }
            },
        )

