"""MongoDB client helpers using Motor (async)."""

from functools import lru_cache
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings


@lru_cache()
def _get_client() -> AsyncIOMotorClient:
    settings = get_settings()
    return AsyncIOMotorClient(settings.mongo_uri)


def get_db() -> AsyncIOMotorDatabase:
    """Return Motor database handle."""
    settings = get_settings()
    client = _get_client()
    return client[settings.mongo_db_name]


def get_collection(name: str):
    """Helper to fetch a collection by name."""
    return get_db()[name]

