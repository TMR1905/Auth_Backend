"""
Simple tests to learn async database testing.
"""
import pytest
from sqlalchemy import select

from app.models.user import User


@pytest.mark.asyncio
async def test_create_user(db_session):
    """
    Test: Can we create a user in the database?

    WHY this test?
    - Verifies our User model works
    - Verifies database connection works
    - Verifies table was created correctly
    """
    # 1. Create a user object
    user = User(
        email="test@example.com",
        hashed_password="fake_hashed_password"
    )

    # 2. Add to session and save
    db_session.add(user)
    await db_session.commit()

    # 3. Refresh to get generated fields (id, created_at, etc.)
    await db_session.refresh(user)

    # 4. Assert it worked
    assert user.id is not None  # UUID was generated
    assert user.email == "test@example.com"
    assert user.is_active is True  # Default value
    assert user.is_verified is False  # Default value


@pytest.mark.asyncio
async def test_query_user(db_session):
    """
    Test: Can we query a user from the database?

    WHY this test?
    - Verifies SELECT queries work
    - Verifies data persists within a session
    """
    # 1. Create and save user
    user = User(email="query@example.com", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    # 2. Query it back using SQLAlchemy select
    stmt = select(User).where(User.email == "query@example.com")
    result = await db_session.execute(stmt)
    found_user = result.scalar_one()  # Get single result

    # 3. Assert
    assert found_user.email == "query@example.com"


@pytest.mark.asyncio
async def test_users_are_isolated(db_session):
    """
    Test: Each test gets a fresh database.

    WHY this matters?
    - Tests should NOT affect each other
    - This test proves the user from previous tests doesn't exist
    """
    # Query for users from other tests - should find NONE
    stmt = select(User).where(User.email == "test@example.com")
    result = await db_session.execute(stmt)
    found_user = result.scalar_one_or_none()

    assert found_user is None  # Fresh DB = no leftover data
