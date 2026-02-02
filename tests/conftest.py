from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import current_active_user
from app.database import Base, get_async_session
from app.main import app
from app.models.user import User

# Use SQLite for tests (faster, no external dependencies)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


app.dependency_overrides[get_async_session] = override_get_async_session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Direct database session for test setup."""
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def test_user() -> User:
    """A test user for authenticated endpoints."""
    return User(id=uuid4(), email="test@example.com", hashed_password="fake")


@pytest.fixture
def other_user() -> User:
    """A second test user for isolation tests."""
    return User(id=uuid4(), email="other@example.com", hashed_password="fake")


@pytest.fixture
def admin_user() -> User:
    """A user with the admin role."""
    return User(id=uuid4(), email="admin@example.com", hashed_password="fake", role="admin")


@pytest.fixture
def superuser() -> User:
    """A superuser (bypasses role checks)."""
    return User(id=uuid4(), email="super@example.com", hashed_password="fake", is_superuser=True)


@pytest.fixture
async def auth_client(client: AsyncClient, test_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Client that authenticates as test_user via dependency override."""
    app.dependency_overrides[current_active_user] = lambda: test_user
    try:
        yield client
    finally:
        app.dependency_overrides.pop(current_active_user, None)


@pytest.fixture
async def admin_client(client: AsyncClient, admin_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Client that authenticates as admin_user via dependency override."""
    app.dependency_overrides[current_active_user] = lambda: admin_user
    try:
        yield client
    finally:
        app.dependency_overrides.pop(current_active_user, None)
