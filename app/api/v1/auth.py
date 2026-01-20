from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token, TokenRefresh, LoginRequest
from app.schemas.two_factor import TwoFactorVerify
from app.services.user_service import create_user, get_user_by_id
from app.services.auth_service import (
    authenticate_user,
    create_tokens,
    refresh_access_token,
    revoke_refresh_token,
    verify_2fa_login,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.

    - **email**: Valid email address (must be unique)
    - **password**: User's password
    """
    try:
        user = await create_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=Token | dict)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password.

    Returns access and refresh tokens if successful.
    If 2FA is enabled, returns `requires_2fa: true` and `user_id` instead.
    """
    user = await authenticate_user(db, login_data.email, login_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Check if 2FA is required
    if user.two_factor_enabled:
        return {
            "requires_2fa": True,
            "user_id": user.id,
            "message": "2FA verification required",
        }

    # No 2FA - issue tokens directly
    tokens = await create_tokens(db, user)
    return tokens


@router.post("/token", response_model=Token | dict)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 compatible login endpoint (for Swagger UI "Authorize" button).

    Use email as username. This endpoint is equivalent to /login but uses
    OAuth2 form format instead of JSON.
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    if user.two_factor_enabled:
        return {
            "requires_2fa": True,
            "user_id": user.id,
            "message": "2FA verification required",
        }

    tokens = await create_tokens(db, user)
    return tokens


@router.post("/login/2fa", response_model=Token)
async def login_2fa(
    user_id: str,
    code_data: TwoFactorVerify,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete login with 2FA code.

    Use this endpoint after `/login` returns `requires_2fa: true`.

    - **user_id**: User ID returned from login
    - **code**: 6-digit code from authenticator app
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this user",
        )

    tokens = await verify_2fa_login(db, user, code_data.code)
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code",
        )

    return tokens


@router.post("/refresh", response_model=Token)
async def refresh(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    The old refresh token is revoked and a new one is issued (token rotation).
    """
    tokens = await refresh_access_token(db, token_data.refresh_token)
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    """
    Logout by revoking the refresh token.

    The access token will remain valid until it expires (short-lived).
    """
    revoked = await revoke_refresh_token(db, token_data.refresh_token)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )
    return None
