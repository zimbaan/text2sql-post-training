"""Account-level endpoints (saved connections, history)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_active_user
from app.db.history import list_history
from app.db.saved_connections import (
    create_saved_connection,
    delete_saved_connection,
    list_saved_connections,
)
from app.models.account import QueryHistoryResponse, SavedConnectionCreate, SavedConnectionPublic
from app.models.user import UserInDB

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/connections", response_model=list[SavedConnectionPublic])
async def get_saved_connections(
    current_user: UserInDB = Depends(get_current_active_user),
):
    """List saved connections for the current user."""
    return await list_saved_connections(current_user.id)


@router.post("/connections", response_model=SavedConnectionPublic, status_code=status.HTTP_201_CREATED)
async def save_connection(
    payload: SavedConnectionCreate,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Create or overwrite a saved connection for the current user."""
    return await create_saved_connection(current_user.id, payload)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_connection(
    connection_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Delete a saved connection."""
    deleted = await delete_saved_connection(current_user.id, connection_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")


@router.get("/history", response_model=QueryHistoryResponse)
async def get_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    connection_id: str | None = None,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Fetch paginated query history for the current user."""
    items, total = await list_history(
        current_user.id,
        limit=limit,
        offset=offset,
        connection_id=connection_id,
    )
    return QueryHistoryResponse(items=items, total=total)
