from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from album_tracker_api.dependencies.db import SessionDep
from album_tracker_api.handlers.auth.utils import get_password_hash
from album_tracker_api.models.user import User
from album_tracker_api.schemas.auth.register import RegisterRequest, RegisterResponse


class RegisterHandler:
    session: AsyncSession

    def __init__(self, session: SessionDep) -> None:
        self.session = session

    async def handle(self, request: RegisterRequest) -> RegisterResponse:
        existing_user = (await self.session.scalars(select(User).where(User.email == request.email))).first()
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists",
            )

        user = User(email=request.email, password_hash=get_password_hash(request.password))
        self.session.add(user)
        await self.session.commit()
        return RegisterResponse(user_id=user.id)
