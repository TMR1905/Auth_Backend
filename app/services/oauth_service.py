from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.oauth import OAuthAccount


# Google OAuth URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Redirect URI - must match what you set in Google Console
GOOGLE_REDIRECT_URI = "http://localhost:8000/api/v1/auth/google/callback"


def get_google_login_url(state: str | None = None) -> str:
    """
    Build the URL to redirect users to Google's login page.

    Args:
        state: Optional state parameter for CSRF protection

    Returns:
        URL string to redirect user to
    """
    params = {
        "client_id": settings.GOOGLE_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "email profile",
        "access_type": "offline",  # Get refresh token
    }

    if state:
        params["state"] = state

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict | None:
    """
    Exchange the authorization code for access tokens.

    Args:
        code: The authorization code from Google callback

    Returns:
        Token response dict or None if failed
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_ID,
                "client_secret": settings.GOOGLE_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            },
        )

        if response.status_code != 200:
            return None

        return response.json()


async def get_google_user_info(access_token: str) -> dict | None:
    """
    Get user info from Google using the access token.

    Args:
        access_token: Google access token

    Returns:
        User info dict with id, email, name, picture or None if failed
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            return None

        return response.json()


async def get_or_create_oauth_user(
    db: AsyncSession,
    provider: str,
    provider_user_id: str,
    email: str,
) -> User:
    """
    Find existing user by OAuth account or email, or create new user.

    Flow:
    1. Check if OAuth account exists -> return linked user
    2. Check if user with email exists -> link OAuth account and return user
    3. Create new user and OAuth account

    Args:
        db: Database session
        provider: OAuth provider name (e.g., "google")
        provider_user_id: User ID from the provider
        email: User's email from the provider

    Returns:
        User object (existing or newly created)
    """
    # 1. Check if OAuth account already exists
    stmt = select(OAuthAccount).where(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id,
    )
    result = await db.execute(stmt)
    oauth_account = result.scalar_one_or_none()

    if oauth_account:
        # User already linked with this OAuth account
        stmt = select(User).where(User.id == oauth_account.user_id)
        result = await db.execute(stmt)
        return result.scalar_one()

    # 2. Check if user with this email exists
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # Link OAuth account to existing user
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
        )
        db.add(oauth_account)
        await db.commit()
        return user

    # 3. Create new user and OAuth account
    user = User(
        email=email,
        hashed_password=None,  # OAuth users don't have passwords
        is_verified=True,  # Email verified by Google
    )
    db.add(user)
    await db.flush()  # Get user.id

    oauth_account = OAuthAccount(
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
    )
    db.add(oauth_account)
    await db.commit()

    return user
