import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.token import RefreshToken
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.two_factor import verify_totp
from app.services.user_service import get_user_by_email
from app.config import settings


def _hash_token(token: str) -> str:
    """Hash a token for secure storage (we don't store raw tokens)"""
    return hashlib.sha256(token.encode()).hexdigest()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """
    Verify email and password.
    Returns User if valid, None if invalid.
    """
    user = await get_user_by_email(db, email)

    if user is None:
        return None

    if user.hashed_password is None:
        # OAuth user - can't login with password
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


async def create_tokens(db: AsyncSession, user: User) -> dict:
    """
    Create access and refresh tokens for a user.
    Stores refresh token hash in database.
    Returns dict with both tokens.
    """
    # Create access token (short-lived, not stored)
    access_token = create_access_token(subject=user.id)

    # Create refresh token (long-lived, stored in DB)
    refresh_token = create_refresh_token(subject=user.id)

    # Store hash of refresh token in database
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_token = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(refresh_token),
        expires_at=expires_at,
    )
    db.add(db_token)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict | None:
    """
    Use refresh token to get new access token.
    Returns new tokens if valid, None if invalid.
    """
    # Decode and validate the refresh token
    payload = decode_token(refresh_token)
    if payload is None:
        return None

    if payload.get("type") != "refresh":
        return None

    # Find token in database by hash
    token_hash = _hash_token(refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,  # noqa: E712
    )
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()

    if db_token is None:
        return None

    # Check if expired
    if db_token.expires_at < datetime.now(timezone.utc):
        return None

    # Revoke old refresh token (rotation)
    db_token.revoked = True

    # Create new tokens
    user_id = payload.get("sub")
    access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)

    # Store new refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_db_token = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(new_refresh_token),
        expires_at=expires_at,
    )
    db.add(new_db_token)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> bool:
    """
    Revoke a refresh token (logout).
    Returns True if revoked, False if not found.
    """
    token_hash = _hash_token(refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()

    if db_token is None:
        return False

    db_token.revoked = True
    await db.commit()
    return True


async def revoke_all_user_tokens(db: AsyncSession, user_id: str) -> int:
    """
    Revoke all refresh tokens for a user (logout everywhere).
    Returns number of tokens revoked.
    """
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,  # noqa: E712
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()

    for token in tokens:
        token.revoked = True

    await db.commit()
    return len(tokens)


async def verify_2fa_login(
    db: AsyncSession, user: User, code: str
) -> dict | None:
    """
    Complete login for user with 2FA enabled.
    Returns tokens if code is valid, None if invalid.
    """
    if not user.two_factor_enabled or user.two_factor_secret is None:
        return None

    if not verify_totp(user.two_factor_secret, code):
        return None

    return await create_tokens(db, user)


async def get_user_from_token(db: AsyncSession, token: str) -> User | None:
    """
    Get user from access token.
    Used in dependencies to get current user.
    """
    payload = decode_token(token)
    if payload is None:
        return None

    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
