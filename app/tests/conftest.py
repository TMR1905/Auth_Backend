"""
conftest.py - Pytest automatically loads this file.
Fixtures defined here are available to ALL test files.
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
from app import models  # noqa: F401 - Load models so Base.metadata knows about them

# WHY in-memory?
# - Fast (no disk I/O)
# - Fresh database each time
# - Disappears after test ends
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """
    Creates a fresh database session for each test.

    WHY a fixture?
    - Runs setup BEFORE each test
    - Runs cleanup AFTER each test
    - Each test gets isolated data (no interference)
    """

    # 1. Create engine (connection to database)
    engine = create_async_engine(TEST_DATABASE_URL)

    # 2. Create all tables (User, OAuthAccount, RefreshToken)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 3. Create session factory
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 4. Create and yield session to test
    async with session_maker() as session:
        yield session  # <-- Test runs here with this session

    # 5. Cleanup: drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
