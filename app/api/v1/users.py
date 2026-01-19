from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.user import UserResponse, UserDetailResponse, UserUpdate, PasswordChange
from app.services.user_service import update_user, change_password, delete_user
from app.services.auth_service import revoke_all_user_tokens

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current user's profile information.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update current user's profile.

    - **email**: New email address (optional, must be unique)
    """
    try:
        updated_user = await update_user(db, current_user, user_data)
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_user_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Change current user's password.

    - **current_password**: Current password for verification
    - **new_password**: New password to set
    """
    try:
        await change_password(db, current_user, password_data)
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete current user's account.

    This action is irreversible. All associated data will be deleted.
    """
    # Revoke all tokens first
    await revoke_all_user_tokens(db, current_user.id)
    # Delete the user
    await delete_user(db, current_user)
    return None
