"""User creation without an email must not store email=None (the sparse unique index treats nulls as values)."""

import pytest

import app.db.users as users
from app.models.user import UserCreate


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def create_index(self, *args, **kwargs):
        pass

    async def find_one(self, query):
        return None

    async def insert_one(self, doc):
        self.docs.append(doc)


@pytest.mark.asyncio
async def test_email_omitted_when_not_given(monkeypatch):
    coll = FakeCollection()
    monkeypatch.setattr(users, "get_collection", lambda name: coll)
    monkeypatch.setattr(users, "_indexes_created", False)

    await users.create_user(UserCreate(username="first", password="password-one"))
    await users.create_user(UserCreate(username="second", password="password-two", email="Second@Example.com"))

    assert "email" not in coll.docs[0]
    assert coll.docs[1]["email"] == "second@example.com"
