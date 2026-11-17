"""Connection management router."""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.db.manager import get_connection_manager
from app.models.dtos import ConnectionRequest, ConnectionResponse, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/connect", tags=["Connection"])


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(request: ConnectionRequest) -> ConnectionResponse:
    """Create a new database connection.

    Args:
        request: Connection request with database credentials

    Returns:
        Connection response with connection_id and capabilities

    Raises:
        HTTPException: If connection fails
    """
    try:
        manager = get_connection_manager()

        # Create connection
        connection_id, engine, capabilities = manager.create_connection(
            dialect=request.dialect,
            username=request.username,
            password=request.password,
            host=request.host,
            port=request.port,
            database=request.database,
            options=request.options or {},
        )

        # Get list of databases (for multi-database dialects)
        from app.db.introspect import get_databases

        databases = get_databases(engine)
        default_database = request.database or (databases[0] if databases else "default")

        return ConnectionResponse(
            connection_id=connection_id,
            databases=databases,
            default_database=default_database,
            capabilities=capabilities,
        )
    except ValueError as e:
        logger.error(f"Connection creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "CONNECTION_FAILED",
                    "message": str(e),
                    "details": None,
                }
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error creating connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to create connection",
                    "details": {"error": str(e)},
                }
            },
        )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_connection(connection_id: str):
    """Close and remove a database connection.

    Args:
        connection_id: Connection identifier

    Raises:
        HTTPException: If connection not found
    """
    manager = get_connection_manager()
    success = manager.close_connection(connection_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CONNECTION_NOT_FOUND",
                    "message": f"Connection {connection_id} not found",
                    "details": None,
                }
            },
        )

