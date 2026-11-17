"""MongoDB-backed user store."""

import logging
import uuid
from datetime import datetime
from typing import Optional

from app.core.auth import generate_api_key, get_password_hash
from app.db.mongo import get_collection
from app.models.user import UserCreate, UserInDB

logger = logging.getLogger(__name__)

USERS_COLLECTION = "users"
_indexes_created = False


async def _ensure_indexes():
    """Create necessary indexes once."""
    global _indexes_created
    if _indexes_created:
        return
    coll = get_collection(USERS_COLLECTION)
    await coll.create_index("username", unique=True)
    await coll.create_index("email", unique=True, sparse=True)
    await coll.create_index("api_key", unique=True, sparse=True)
    _indexes_created = True


def _user_from_doc(doc: dict) -> UserInDB:
    return UserInDB(
        id=str(doc["_id"]),
        username=doc["username"],
        email=doc.get("email"),
        full_name=doc.get("full_name"),
        hashed_password=doc["hashed_password"],
        api_key=doc.get("api_key"),
        is_active=doc.get("is_active", True),
        is_admin=doc.get("is_admin", False),
        created_at=doc.get("created_at"),
        last_login=doc.get("last_login"),
    )


async def create_user(user_create: UserCreate) -> UserInDB:
    await _ensure_indexes()
    coll = get_collection(USERS_COLLECTION)

    username = user_create.username.lower()
    email = user_create.email.lower() if user_create.email else None

    # Uniqueness checks
    existing = await coll.find_one({"$or": [{"username": username}, {"email": email}] if email else [{"username": username}]})
    if existing:
        if existing["username"] == username:
            raise ValueError(f"Username '{username}' already exists")
        if email and existing.get("email") == email:
            raise ValueError(f"Email '{email}' already exists")

    user_id = str(uuid.uuid4())
    api_key = generate_api_key()

    doc = {
        "_id": user_id,
        "username": username,
        "full_name": user_create.full_name,
        "hashed_password": get_password_hash(user_create.password),
        "api_key": api_key,
        "is_active": True,
        "is_admin": False,
        "created_at": datetime.utcnow(),
        "last_login": None,
    }
    # Only store email when given: the unique index is sparse, which skips missing fields but not nulls, so
    # storing email=None would let only one user ever sign up without an email.
    if email:
        doc["email"] = email

    await coll.insert_one(doc)
    logger.info("Created user %s", username)
    return _user_from_doc(doc)


async def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    await _ensure_indexes()
    doc = await get_collection(USERS_COLLECTION).find_one({"_id": user_id})
    return _user_from_doc(doc) if doc else None


async def get_user_by_username(username: str) -> Optional[UserInDB]:
    await _ensure_indexes()
    doc = await get_collection(USERS_COLLECTION).find_one({"username": username.lower()})
    return _user_from_doc(doc) if doc else None


async def get_user_by_api_key(api_key: str) -> Optional[UserInDB]:
    await _ensure_indexes()
    doc = await get_collection(USERS_COLLECTION).find_one({"api_key": api_key})
    return _user_from_doc(doc) if doc else None


async def update_user(user_id: str, user_update: dict) -> Optional[UserInDB]:
    await _ensure_indexes()
    coll = get_collection(USERS_COLLECTION)

    update_doc: dict = {}
    if "email" in user_update and user_update["email"] is not None:
        update_doc["email"] = user_update["email"].lower()
    if "full_name" in user_update:
        update_doc["full_name"] = user_update["full_name"]
    if "password" in user_update and user_update["password"]:
        update_doc["hashed_password"] = get_password_hash(user_update["password"])
    if "api_key" in user_update and user_update["api_key"] is not None:
        update_doc["api_key"] = user_update["api_key"]
    if "is_admin" in user_update:
        update_doc["is_admin"] = bool(user_update["is_admin"])
    if "is_active" in user_update:
        update_doc["is_active"] = bool(user_update["is_active"])

    if not update_doc:
        doc = await coll.find_one({"_id": user_id})
        return _user_from_doc(doc) if doc else None

    result = await coll.find_one_and_update(
        {"_id": user_id},
        {"$set": update_doc},
        return_document=True,
    )
    return _user_from_doc(result) if result else None


async def update_last_login(user_id: str):
    await _ensure_indexes()
    await get_collection(USERS_COLLECTION).update_one(
        {"_id": user_id},
        {"$set": {"last_login": datetime.utcnow()}},
    )


async def delete_user(user_id: str) -> bool:
    await _ensure_indexes()
    result = await get_collection(USERS_COLLECTION).delete_one({"_id": user_id})
    return result.deleted_count > 0


async def list_users() -> list[UserInDB]:
    await _ensure_indexes()
    docs = get_collection(USERS_COLLECTION).find({})
    return [_user_from_doc(doc) async for doc in docs]


async def get_user_count() -> int:
    await _ensure_indexes()
    return await get_collection(USERS_COLLECTION).count_documents({})
