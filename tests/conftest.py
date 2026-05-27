from collections.abc import AsyncGenerator, Generator
from uuid import uuid7

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from album_tracker_api.dependencies import get_db
from album_tracker_api.handlers import create_token, get_password_hash
from album_tracker_api.main import app
from album_tracker_api.models import AlbumTrackerBase, User


@pytest.fixture(scope="session")
def pg_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:alpine") as postgres:
        yield postgres


@pytest.fixture
async def engine(pg_container: PostgresContainer) -> AsyncGenerator[AsyncEngine]:
    connection_url = pg_container.get_connection_url().replace("psycopg2", "asyncpg")  # Use AsyncEngine
    engine = create_async_engine(
        connection_url,
        # echo=True,
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(AlbumTrackerBase.metadata.create_all)
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(AlbumTrackerBase.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncGenerator[AsyncConnection]:
    async with engine.connect() as connection:
        yield connection


@pytest.fixture
async def session(connection: AsyncConnection) -> AsyncGenerator[AsyncSession]:
    transaction = await connection.begin()
    try:
        async with AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        ) as session:
            yield session
    finally:
        # Rollback changes after every test (so that tests don't interfere with one another)
        await transaction.rollback()


@pytest.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        id=uuid7(),
        email="testuser@example.com",
        password_hash=get_password_hash("testpassword"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def admin_user(session: AsyncSession) -> User:
    user = User(
        id=uuid7(),
        email="admin@example.com",
        password_hash=get_password_hash("adminpassword"),
        is_admin=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def unauthenticated_client(session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def client(unauthenticated_client: AsyncClient, test_user: User) -> AsyncGenerator[AsyncClient]:
    authenticated_client = unauthenticated_client
    access_token = create_token(test_user, "access")
    authenticated_client.headers["Authorization"] = f"Bearer {access_token}"
    yield authenticated_client


@pytest.fixture
async def admin_client(unauthenticated_client: AsyncClient, admin_user: User) -> AsyncGenerator[AsyncClient]:
    authenticated_client = unauthenticated_client
    access_token = create_token(admin_user, "access")
    authenticated_client.headers["Authorization"] = f"Bearer {access_token}"
    yield authenticated_client
