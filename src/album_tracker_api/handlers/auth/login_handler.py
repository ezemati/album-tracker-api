from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from album_tracker_api.dependencies.db import SessionDep
from album_tracker_api.handlers.auth.utils import create_access_token, verify_password
from album_tracker_api.models.user import User
from album_tracker_api.schemas.auth.login import LoginResponse


class LoginHandler:
    session: AsyncSession

    def __init__(self, session: SessionDep) -> None:
        self.session = session

    async def handle(self, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> LoginResponse:
        user = await self.__authenticate_user(form_data.username, form_data.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        return LoginResponse(access_token=create_access_token(user), refresh_token="fakerefreshtoken")

    async def __authenticate_user(self, email: str, password: str) -> User | None:
        user = (await self.session.scalars(select(User).where(User.email == email))).first()
        if user is None:
            return None
        if not verify_password(user.password_hash, password):
            return None
        return user
