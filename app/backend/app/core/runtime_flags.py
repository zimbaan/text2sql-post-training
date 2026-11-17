"""Runtime flags that can be toggled without restarting the service."""

import threading

from app.core.config import get_settings

_settings = get_settings()
_lock = threading.Lock()
_safe_mode_enabled = bool(_settings.execution_safe_mode)


def is_safe_mode_enabled() -> bool:
    """Return current safe mode state."""
    with _lock:
        return _safe_mode_enabled


def set_safe_mode(enabled: bool) -> bool:
    """Set safe mode state. Returns the updated value."""
    global _safe_mode_enabled
    with _lock:
        _safe_mode_enabled = bool(enabled)
        return _safe_mode_enabled


def toggle_safe_mode() -> bool:
    """Toggle safe mode and return the new value."""
    with _lock:
        _safe_mode_enabled = not _safe_mode_enabled  # noqa: PLW0603
        return _safe_mode_enabled
