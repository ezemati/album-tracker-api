from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import settings
from ..dependencies import SessionDep
from ..models import User
from ..schemas import JwtFields, LoginResponse, MeResponse, RefreshRequest, RegisterRequest, RegisterResponse


class AuthHandler:
    session: AsyncSession
    password_hasher: PasswordHasher

    def __init__(self, session: SessionDep) -> None:
        self.session = session
        self.password_hasher = PasswordHasher()

    async def handle_login(self, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> LoginResponse:
        user = await self.__authenticate_user(form_data.username, form_data.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        return LoginResponse(
            access_token=self.__create_token(user, "access"),
            refresh_token=self.__create_token(user, "refresh"),
            user=self.__create_user_info_response(user),
        )

    async def handle_register(self, request: RegisterRequest) -> RegisterResponse:
        existing_user = (await self.session.scalars(select(User).where(User.email == request.email))).first()
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists",
            )

        user = User(email=request.email, password_hash=self.password_hasher.hash(request.password))
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return RegisterResponse(user_id=user.id)

    async def handle_refresh(self, request: RefreshRequest) -> LoginResponse:
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
            access_token=self.__create_token(user, "access"),
            refresh_token=self.__create_token(user, "refresh"),
            user=self.__create_user_info_response(user),
        )

    async def __authenticate_user(self, email: str, password: str) -> User | None:
        user = (await self.session.scalars(select(User).where(User.email == email))).first()
        if user is None:
            return None
        if not self.__verify_password(user.password_hash, password):
            return None
        return user

    def __verify_password(self, hashed_password: str, plain_password: str) -> bool:
        try:
            _ = self.password_hasher.verify(hashed_password, plain_password)
            return True
        except VerifyMismatchError:
            return False

    def __create_token(self, user: User, token_type: Literal["access", "refresh"]) -> str:
        expire_minutes = (
            settings.jwt.access_token_expire_minutes
            if token_type == "access"
            else settings.jwt.refresh_token_expire_minutes
        )
        exp = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
        data = JwtFields(
            sub=str(user.id),
            email=user.email,
            exp=exp,
            token_type=token_type,
            roles=["ADMIN"] if user.is_admin else [],
        )
        return jwt.encode(
            data.model_dump(),
            settings.jwt.secret_key,
            settings.jwt.algorithm,
        )

    def __create_user_info_response(self, user: User) -> MeResponse:
        return MeResponse(id=user.id, email=user.email)
