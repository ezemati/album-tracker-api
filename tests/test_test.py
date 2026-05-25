from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from album_tracker_api.models.user import User


async def test_test(client: TestClient, session: AsyncSession) -> None:
    users = (await session.scalars(select(User))).all()
    assert len(users) > 0
