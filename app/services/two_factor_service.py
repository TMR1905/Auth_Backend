from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.two_factor import (
    generate_totp_secret,
    get_totp_uri,
    generate_qr_code,
    verify_totp,
)


async def setup_2fa(db: AsyncSession, user: User) -> dict:
    """
    Start 2FA setup for a user.

    - Generates a new TOTP secret
    - Saves it to the user (but doesn't enable 2FA yet)
    - Returns the secret and QR code for the authenticator app

    Args:
        db: Database session
        user: User object (must not have 2FA enabled already)

    Returns:
        dict with 'secret' and 'qr_code' keys

    Raises:
        ValueError: If 2FA is already enabled
    """
    if user.two_factor_enabled:
        raise ValueError("2FA is already enabled")

    # Generate new secret
    secret = generate_totp_secret()

    # Store secret temporarily (not enabled yet - user must verify first)
    user.two_factor_secret = secret
    await db.commit()

    # Generate QR code for authenticator app
    uri = get_totp_uri(secret, user.email)
    qr_code = generate_qr_code(uri)

    return {
        "secret": secret,
        "qr_code": qr_code,
    }


async def enable_2fa(db: AsyncSession, user: User, code: str) -> bool:
    """
    Verify TOTP code and enable 2FA for the user.

    Called after setup_2fa() - user provides the code from their
    authenticator app to prove they set it up correctly.

    Args:
        db: Database session
        user: User object (must have called setup_2fa first)
        code: 6-digit code from authenticator app

    Returns:
        True if 2FA was enabled successfully

    Raises:
        ValueError: If 2FA already enabled, setup not started, or invalid code
    """
    if user.two_factor_enabled:
        raise ValueError("2FA is already enabled")

    if user.two_factor_secret is None:
        raise ValueError("2FA setup not started. Call setup_2fa first")

    # Verify the code matches the secret
    if not verify_totp(user.two_factor_secret, code):
        raise ValueError("Invalid 2FA code")

    # Enable 2FA
    user.two_factor_enabled = True
    await db.commit()

    return True


async def disable_2fa(db: AsyncSession, user: User, code: str) -> bool:
    """
    Disable 2FA for a user (requires valid code for security).

    Args:
        db: Database session
        user: User object (must have 2FA enabled)
        code: 6-digit code from authenticator app

    Returns:
        True if 2FA was disabled successfully

    Raises:
        ValueError: If 2FA not enabled, no secret found, or invalid code
    """
    if not user.two_factor_enabled:
        raise ValueError("2FA is not enabled")

    if user.two_factor_secret is None:
        raise ValueError("2FA secret not found")

    # Verify the code (security: prevent unauthorized disable)
    if not verify_totp(user.two_factor_secret, code):
        raise ValueError("Invalid 2FA code")

    # Disable 2FA and clear the secret
    user.two_factor_enabled = False
    user.two_factor_secret = None
    await db.commit()

    return True


def get_2fa_status(user: User) -> bool:
    """
    Check if 2FA is enabled for a user.

    Args:
        user: User object

    Returns:
        True if 2FA is enabled, False otherwise
    """
    return user.two_factor_enabled
