"""Authentication and authorization utilities."""

import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
JWT_ALGORITHM = "HS256"
_default_jwt_secret: Optional[str] = None  # Will be generated on first use


def get_jwt_secret() -> str:
    """Get JWT secret key from settings or generate one."""
    global _default_jwt_secret
    # Try to get from settings first
    jwt_secret = getattr(settings, "jwt_secret_key", None)
    if jwt_secret:
        return jwt_secret
    # Generate and cache a default secret
    if _default_jwt_secret is None:
        _default_jwt_secret = secrets.token_urlsafe(32)
    return _default_jwt_secret


def get_jwt_access_token_expire_minutes() -> int:
    """Get JWT access token expiration time in minutes."""
    return getattr(settings, "jwt_access_token_expire_minutes", 60 * 24)


def get_jwt_refresh_token_expire_days() -> int:
    """Get JWT refresh token expiration time in days."""
    return getattr(settings, "jwt_refresh_token_expire_days", 7)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in token (e.g., {"sub": "username"})
        expires_delta: Expiration time delta (defaults to 24 hours)

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=get_jwt_access_token_expire_minutes())
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token.

    Args:
        data: Data to encode in token

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=get_jwt_refresh_token_expire_days())
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def generate_api_key() -> str:
    """Generate a secure API key.

    Returns:
        API key string
    """
    return f"sk_{secrets.token_urlsafe(32)}"

