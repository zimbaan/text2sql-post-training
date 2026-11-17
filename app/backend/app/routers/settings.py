"""Runtime settings router (e.g., safe mode toggling)."""

import logging

from fastapi import APIRouter

from app.core.runtime_flags import is_safe_mode_enabled, set_safe_mode
from app.models.dtos import SafeModeRequest, SafeModeResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/safe-mode", response_model=SafeModeResponse)
async def get_safe_mode() -> SafeModeResponse:
    """Return current safe mode state."""
    return SafeModeResponse(enabled=is_safe_mode_enabled())


@router.post("/safe-mode", response_model=SafeModeResponse)
async def update_safe_mode(request: SafeModeRequest) -> SafeModeResponse:
    """Update safe mode flag at runtime."""
    previous = is_safe_mode_enabled()
    current = set_safe_mode(request.enabled)
    logger.info(f"Safe mode changed from {previous} to {current}")
    return SafeModeResponse(enabled=current)
