import json
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ...core import settings
from ...models import User
from ...schemas import JwtFields

password_hasher = PasswordHasher()


def verify_password(hashed_password: str, plain_password: str) -> bool:
    try:
        _ = password_hasher.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def get_password_hash(plain_password: str):
    return password_hasher.hash(plain_password)


def create_token(user: User, token_type: Literal["access", "refresh"]):
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


def create_access_token(user: User):
    return create_token(user, "access")


def create_refresh_token(user: User):
    return create_token(user, "refresh")
