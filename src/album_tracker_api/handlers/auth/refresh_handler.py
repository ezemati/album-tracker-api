from uuid import UUID

import jwt
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core import settings
from ...dependencies import SessionDep
from ...models import User
from ...schemas import JwtFields, LoginResponse, RefreshRequest
from .utils import create_access_token, create_refresh_token


class RefreshHandler:
    session: AsyncSession

    def __init__(self, session: SessionDep) -> None:
        self.session = session

    async def handle(self, request: RefreshRequest) -> LoginResponse:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(request.refresh_token, settings.jwt.secret_key, [settings.jwt.algorithm])
            token_data = JwtFields.model_validate(payload)
        except jwt.InvalidTokenError, ValidationError:
            raise credentials_exception

        if token_data.token_type != "refresh":
            raise credentials_exception

        user_id = UUID(token_data.sub)
        user = (await self.session.scalars(select(User).where(User.id == user_id))).first()
        if user is None:
            raise credentials_exception

        return LoginResponse(
            access_token=create_access_token(user),
            refresh_token=create_refresh_token(user),
        )
