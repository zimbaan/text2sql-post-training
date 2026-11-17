"""Password hashing works with current bcrypt (5.x raises on >72-byte input instead of truncating)."""

import bcrypt

from app.core.auth import get_password_hash, verify_password


def test_hash_and_verify():
    hashed = get_password_hash("correct horse battery")
    assert hashed.startswith("$2b$")
    assert verify_password("correct horse battery", hashed)
    assert not verify_password("wrong password", hashed)


def test_long_password_is_truncated_not_rejected():
    long_password = "a" * 100
    assert verify_password(long_password, get_password_hash(long_password))


def test_existing_and_malformed_hashes():
    legacy = bcrypt.hashpw(b"legacy-pass", bcrypt.gensalt(prefix=b"2a")).decode()
    assert verify_password("legacy-pass", legacy)
    assert not verify_password("anything", "not-a-bcrypt-hash")
