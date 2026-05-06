from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy import select

from ..core import settings
from ..dependencies import SessionDep
from ..models import User
from ..schemas import JwtFields

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", refreshUrl="/auth/refresh")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt.secret_key, [settings.jwt.algorithm])
        token_data = JwtFields.model_validate(payload)
    except jwt.InvalidTokenError, ValidationError:
        raise credentials_exception
    user = (await session.scalars(select(User).where(User.id == token_data.sub))).first()
    if user is None:
        raise credentials_exception
    return user


type CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_admin_user(user: CurrentUserDep) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action",
        )
    return user


type CurrentAdminUserDep = Annotated[User, Depends(get_current_admin_user)]
