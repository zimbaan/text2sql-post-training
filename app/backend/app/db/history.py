"""Mongo-backed query history."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.db.mongo import get_collection
from app.models.account import QueryHistoryItem

COLL = "query_history"
_indexes_created = False


async def _ensure_indexes():
    global _indexes_created
    if _indexes_created:
        return
    coll = get_collection(COLL)
    await coll.create_index([("user_id", 1), ("created_at", -1)])
    await coll.create_index([("connection_id", 1), ("created_at", -1)])
    _indexes_created = True


async def add_history_entry(user_id: str, entry: Dict[str, Any]) -> str:
    await _ensure_indexes()
    doc = {
        **entry,
        "_id": entry.get("_id") or f"{user_id}:{entry.get('timestamp', datetime.utcnow().timestamp())}",
        "user_id": user_id,
        "created_at": datetime.utcnow(),
    }
    await get_collection(COLL).insert_one(doc)
    return str(doc["_id"])


async def list_history(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    connection_id: Optional[str] = None,
) -> Tuple[List[QueryHistoryItem], int]:
    await _ensure_indexes()
    filter_query = {"user_id": user_id}
    if connection_id:
        filter_query["connection_id"] = connection_id
    coll = get_collection(COLL)
    total = await coll.count_documents(filter_query)
    cursor = (
        coll.find(filter_query)
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    items = [
        QueryHistoryItem(
            id=str(doc["_id"]),
            user_query=doc.get("user_query", ""),
            sql=doc.get("sql", ""),
            database=doc.get("database"),
            schema=doc.get("schema"),
            table_scope=doc.get("table_scope"),
            is_read_only=doc.get("is_read_only", True),
            requires_confirmation=doc.get("requires_confirmation", False),
            execution_skipped=doc.get("execution_skipped", False),
            row_count=doc.get("row_count", 0),
            elapsed_ms=doc.get("elapsed_ms"),
            warnings=doc.get("warnings", []) or [],
            status=doc.get("status", "success"),
            error=doc.get("error"),
            created_at=doc.get("created_at"),
        )
        async for doc in cursor
    ]
    return items, total
