from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from album_tracker_api.db.database import engine


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    async with AsyncSession(engine) as session:
        yield session


type SessionDep = Annotated[AsyncSession, Depends(get_db)]
