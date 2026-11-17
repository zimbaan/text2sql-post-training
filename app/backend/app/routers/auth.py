"""Authentication and user management router."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    verify_password,
)
from app.core.dependencies import get_current_active_user, get_current_admin_user
from app.db.users import (
    create_user,
    get_user_by_username,
    update_last_login,
    update_user,
    get_user_count,
)
from app.models.user import (
    Token,
    TokenData,
    UserCreate,
    UserInDB,
    UserPublic,
    UserUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

security = HTTPBearer()


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate) -> UserPublic:
    """Register a new user.

    Args:
        user_create: User registration data

    Returns:
        Created user (public info only)

    Raises:
        HTTPException: If registration fails
    """
    try:
        # Check if this is the first user (make them admin)
        is_first_user = await get_user_count() == 0

        user = await create_user(user_create)

        # Make first user admin
        if is_first_user:
            await update_user(user.id, {"is_admin": True})

        return UserPublic(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...),
) -> Token:
    """Login and get access token.

    Args:
        username: Username
        password: Password

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If login fails
    """
    user = await get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Update last login
    await update_last_login(user.id)

    # Create tokens
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
    refresh_token = create_refresh_token(data={"sub": user.username, "user_id": user.id})

    logger.info(f"User logged in: {user.username} (ID: {user.id})")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=60 * 24 * 60,  # 24 hours in seconds
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
) -> Token:
    """Refresh access token using refresh token.

    Args:
        refresh_token: Refresh token

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh fails
    """
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: Optional[str] = payload.get("sub")
    user_id: Optional[str] = payload.get("user_id")

    if not username and not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Get user
    if user_id:
        from app.db.users import get_user_by_id
        user = await get_user_by_id(user_id)
    else:
        user = await get_user_by_username(username)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.username, "user_id": user.id})

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=60 * 24 * 60,
    )


@router.get("/me", response_model=UserPublic)
async def get_current_user_profile(
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserPublic:
    """Get current user's profile.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user's public profile
    """
    return UserPublic(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.put("/me", response_model=UserPublic)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserPublic:
    """Update current user's profile.

    Args:
        user_update: User update data
        current_user: Current authenticated user

    Returns:
        Updated user's public profile

    Raises:
        HTTPException: If update fails
    """
    try:
        update_data = user_update.model_dump(exclude_unset=True)
        updated_user = await update_user(current_user.id, update_data)

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserPublic(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            full_name=updated_user.full_name,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at,
            last_login=updated_user.last_login,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed",
        )


@router.post("/me/api-key", response_model=dict)
async def regenerate_api_key(
    current_user: UserInDB = Depends(get_current_active_user),
) -> dict:
    """Regenerate API key for current user.

    Args:
        current_user: Current authenticated user

    Returns:
        Dictionary with new API key
    """
    new_api_key = generate_api_key()
    await update_user(current_user.id, {"api_key": new_api_key})

    logger.info(f"API key regenerated for user: {current_user.username}")

    return {
        "api_key": new_api_key,
        "message": "API key regenerated successfully",
    }


@router.get("/me/api-key", response_model=dict)
async def get_api_key(
    current_user: UserInDB = Depends(get_current_active_user),
) -> dict:
    """Get current user's API key.

    Args:
        current_user: Current authenticated user

    Returns:
        Dictionary with API key
    """
    if not current_user.api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found. Please regenerate it.",
        )

    return {
        "api_key": current_user.api_key,
    }

