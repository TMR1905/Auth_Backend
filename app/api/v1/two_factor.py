from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.two_factor import (
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    TwoFactorVerify,
)
from app.core.two_factor import (
    generate_totp_secret,
    get_totp_uri,
    generate_qr_code,
    verify_totp,
)

router = APIRouter(prefix="/auth/2fa", tags=["Two-Factor Authentication"])


@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_active_user),
):
    """
    Check if 2FA is enabled for the current user.
    """
    return TwoFactorStatusResponse(enabled=current_user.two_factor_enabled)


@router.post("/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Start 2FA setup process.

    Returns a secret key and QR code to scan with an authenticator app.
    The user must verify a code with `/auth/2fa/verify` to complete setup.
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled",
        )

    # Generate new secret
    secret = generate_totp_secret()

    # Store secret temporarily (not enabled yet)
    current_user.two_factor_secret = secret
    await db.commit()

    # Generate QR code
    uri = get_totp_uri(secret, current_user.email)
    qr_code = generate_qr_code(uri)

    return TwoFactorSetupResponse(secret=secret, qr_code=qr_code)


@router.post("/verify", response_model=TwoFactorStatusResponse)
async def verify_and_enable_2fa(
    code_data: TwoFactorVerify,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Verify 2FA code and enable 2FA.

    Use this after `/auth/2fa/setup` to complete the setup process.

    - **code**: 6-digit code from authenticator app
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled",
        )

    if current_user.two_factor_secret is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not started. Call /auth/2fa/setup first",
        )

    # Verify the code
    if not verify_totp(current_user.two_factor_secret, code_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code",
        )

    # Enable 2FA
    current_user.two_factor_enabled = True
    await db.commit()

    return TwoFactorStatusResponse(enabled=True)


@router.post("/disable", response_model=TwoFactorStatusResponse)
async def disable_2fa(
    code_data: TwoFactorVerify,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Disable 2FA for the current user.

    Requires a valid 2FA code for security.

    - **code**: 6-digit code from authenticator app
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )

    if current_user.two_factor_secret is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA secret not found",
        )

    # Verify the code
    if not verify_totp(current_user.two_factor_secret, code_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code",
        )

    # Disable 2FA
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    await db.commit()

    return TwoFactorStatusResponse(enabled=False)
