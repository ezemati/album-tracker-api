from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import SessionDep
from ...models import User
from ...schemas import RegisterRequest, RegisterResponse
from .utils import get_password_hash


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
        await self.session.refresh(user)
        return RegisterResponse(user_id=str(user.id))
