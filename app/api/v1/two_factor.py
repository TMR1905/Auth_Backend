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
from app.services.two_factor_service import (
    setup_2fa,
    enable_2fa,
    disable_2fa,
    get_2fa_status,
)

router = APIRouter(prefix="/auth/2fa", tags=["Two-Factor Authentication"])


@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status_endpoint(
    current_user: User = Depends(get_current_active_user),
):
    """
    Check if 2FA is enabled for the current user.
    """
    enabled = get_2fa_status(current_user)
    return TwoFactorStatusResponse(enabled=enabled)


@router.post("/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Start 2FA setup process.

    Returns a secret key and QR code to scan with an authenticator app.
    The user must verify a code with `/auth/2fa/verify` to complete setup.
    """
    try:
        result = await setup_2fa(db, current_user)
        return TwoFactorSetupResponse(secret=result["secret"], qr_code=result["qr_code"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/verify", response_model=TwoFactorStatusResponse)
async def verify_and_enable_2fa_endpoint(
    code_data: TwoFactorVerify,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Verify 2FA code and enable 2FA.

    Use this after `/auth/2fa/setup` to complete the setup process.

    - **code**: 6-digit code from authenticator app
    """
    try:
        await enable_2fa(db, current_user, code_data.code)
        return TwoFactorStatusResponse(enabled=True)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/disable", response_model=TwoFactorStatusResponse)
async def disable_2fa_endpoint(
    code_data: TwoFactorVerify,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Disable 2FA for the current user.

    Requires a valid 2FA code for security.

    - **code**: 6-digit code from authenticator app
    """
    try:
        await disable_2fa(db, current_user, code_data.code)
        return TwoFactorStatusResponse(enabled=False)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
