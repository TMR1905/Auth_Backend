from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

# Password hashing context - bcrypt is secure and widely used
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============ PASSWORD FUNCTIONS ============

def hash_password(password: str) -> str:
    """
    Hash a plain text password.
    Used when: user registers or changes password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if plain password matches the hashed one.
    Used when: user logs in.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============ JWT TOKEN FUNCTIONS ============

def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    Create a short-lived access token.

    Args:
        subject: Usually user_id - what the token identifies
        expires_delta: How long until token expires

    Used when: user logs in, token refresh
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),  # subject - who this token is for
        "exp": expire,        # expiration time
        "type": "access"      # token type
    }

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    Create a long-lived refresh token.
    Used to get new access tokens without re-login.

    Used when: user logs in (given alongside access token)
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh"
    }

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.
    Returns payload if valid, None if invalid/expired.

    Used when: protecting routes, validating requests
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
