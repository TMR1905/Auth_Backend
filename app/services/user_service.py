from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, PasswordChange
from app.core.security import hash_password, verify_password


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Get a user by their ID"""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get a user by their email"""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """
    Create a new user.
    Raises ValueError if email already exists.
    """
    # Check if email already taken
    existing = await get_user_by_email(db, user_data.email)
    if existing:
        raise ValueError("Email already registered")

    # Create user with hashed password
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password)
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, user_data: UserUpdate) -> User:
    """Update user profile fields"""
    if user_data.email is not None:
        # Check if new email is taken by another user
        existing = await get_user_by_email(db, user_data.email)
        if existing and existing.id != user.id:
            raise ValueError("Email already taken")
        user.email = user_data.email

    await db.commit()
    await db.refresh(user)
    return user


async def change_password(db: AsyncSession, user: User, data: PasswordChange) -> bool:
    """
    Change user's password.
    Returns True if successful, raises ValueError if current password is wrong.
    """
    # OAuth users don't have a password
    if user.hashed_password is None:
        raise ValueError("Cannot change password for OAuth accounts")

    if not verify_password(data.current_password, user.hashed_password):
        raise ValueError("Current password is incorrect")

    user.hashed_password = hash_password(data.new_password)
    await db.commit()
    return True


async def delete_user(db: AsyncSession, user: User) -> bool:
    """Delete a user account"""
    await db.delete(user)
    await db.commit()
    return True


async def verify_user_email(db: AsyncSession, user: User) -> User:
    """Mark user's email as verified"""
    user.is_verified = True
    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user: User) -> User:
    """Deactivate a user account"""
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user


async def activate_user(db: AsyncSession, user: User) -> User:
    """Activate a user account"""
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user
