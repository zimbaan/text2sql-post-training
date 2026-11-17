"""Mongo-backed saved connections per user."""

from datetime import datetime
from typing import List, Optional

from app.db.mongo import get_collection
from app.models.account import SavedConnectionCreate, SavedConnectionPublic

COLL = "connections"
_indexes_created = False


async def _ensure_indexes():
    global _indexes_created
    if _indexes_created:
        return
    coll = get_collection(COLL)
    await coll.create_index([("user_id", 1), ("name", 1)], unique=True)
    _indexes_created = True


def _public(doc: dict) -> SavedConnectionPublic:
    return SavedConnectionPublic(
        id=str(doc["_id"]),
        name=doc["name"],
        dialect=doc["dialect"],
        host=doc.get("host"),
        port=doc.get("port"),
        username=doc.get("username"),
        database=doc.get("database"),
        options=doc.get("options") or {},
        created_at=doc.get("created_at"),
        last_used_at=doc.get("last_used_at"),
    )


async def create_saved_connection(user_id: str, payload: SavedConnectionCreate) -> SavedConnectionPublic:
    await _ensure_indexes()
    coll = get_collection(COLL)
    doc = {
        "_id": f"{user_id}:{payload.name}",
        "user_id": user_id,
        "name": payload.name,
        "dialect": payload.dialect,
        "host": payload.host,
        "port": payload.port,
        "username": payload.username,
        "password": payload.password,  # Consider encrypting in production
        "database": payload.database,
        "options": payload.options or {},
        "created_at": datetime.utcnow(),
        "last_used_at": None,
    }
    await coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)
    return _public(doc)


async def list_saved_connections(user_id: str) -> List[SavedConnectionPublic]:
    await _ensure_indexes()
    cursor = get_collection(COLL).find({"user_id": user_id}).sort("created_at", -1)
    return [_public(doc) async for doc in cursor]


async def delete_saved_connection(user_id: str, connection_id: str) -> bool:
    await _ensure_indexes()
    result = await get_collection(COLL).delete_one({"_id": connection_id, "user_id": user_id})
    return result.deleted_count > 0
