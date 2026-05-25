from typing import Any, AsyncGenerator, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from album_tracker_api.dependencies import get_current_user, get_db
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
    engine = create_async_engine(connection_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(AlbumTrackerBase.metadata.create_all)
        yield engine
        await conn.run_sync(AlbumTrackerBase.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        # Rollback changes after every test (so that tests don't interfere with one another)
        await transaction.rollback()


@pytest.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email="testuser@example.com",
        password_hash=get_password_hash("testpassword"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    return create_token(test_user, "access")


@pytest.fixture
async def unauthenticated_client(session: AsyncSession) -> AsyncGenerator[TestClient]:
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def client(
    unauthenticated_client: TestClient,
    test_user: User,
    auth_token: str,
) -> Generator[TestClient, Any, None]:
    authenticated_client = unauthenticated_client

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    authenticated_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    yield authenticated_client
