from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import (
    limiter,
    RATE_LIMIT_LOGIN,
    RATE_LIMIT_REGISTER,
    RATE_LIMIT_2FA,
    RATE_LIMIT_REFRESH,
)

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
from app.services.oauth_service import (
    get_google_login_url,
    exchange_code_for_tokens,
    get_google_user_info,
    get_or_create_oauth_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT_REGISTER)
async def register(
    request: Request,
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
@limiter.limit(RATE_LIMIT_LOGIN)
async def login(
    request: Request,
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
@limiter.limit(RATE_LIMIT_LOGIN)
async def login_oauth2(
    request: Request,
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
@limiter.limit(RATE_LIMIT_2FA)
async def login_2fa(
    request: Request,
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
@limiter.limit(RATE_LIMIT_REFRESH)
async def refresh(
    request: Request,
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


# ============ GOOGLE OAUTH ============


@router.get("/google/login")
async def google_login():
    """
    Redirect user to Google's login page.

    After login, Google will redirect back to /google/callback with an auth code.
    """
    login_url = get_google_login_url()
    return RedirectResponse(url=login_url)


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback.

    Google redirects here with either:
    - ?code=xxx (success) - exchange for tokens
    - ?error=xxx (failure) - user denied access
    """
    if error:
        # User denied access or other error
        return RedirectResponse(url=f"/?error={error}")

    if not code:
        return RedirectResponse(url="/?error=no_code")

    # Exchange code for Google tokens
    token_data = await exchange_code_for_tokens(code)
    if not token_data:
        return RedirectResponse(url="/?error=token_exchange_failed")

    # Get user info from Google
    google_access_token = token_data.get("access_token")
    if not google_access_token:
        return RedirectResponse(url="/?error=no_access_token")

    user_info = await get_google_user_info(google_access_token)
    if not user_info:
        return RedirectResponse(url="/?error=failed_to_get_user_info")

    # Get or create user in our database
    user = await get_or_create_oauth_user(
        db=db,
        provider="google",
        provider_user_id=user_info["id"],
        email=user_info["email"],
    )

    if not user.is_active:
        return RedirectResponse(url="/?error=account_deactivated")

    # Create our JWT tokens
    tokens = await create_tokens(db, user)

    # Redirect to frontend with tokens
    # In production, you might want to use a more secure method (like setting HTTP-only cookies)
    return RedirectResponse(
        url=f"/?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
    )
