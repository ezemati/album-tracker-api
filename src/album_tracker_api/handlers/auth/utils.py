from datetime import datetime, timedelta, timezone

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


def create_access_token(user: User):
    exp_minutes = timedelta(minutes=settings.jwt.access_token_expire_minutes)
    exp = datetime.now(timezone.utc) + exp_minutes
    data = JwtFields(
        sub=str(user.id),
        email=user.email,
        exp=exp,
        roles=["ADMIN"] if user.is_admin else [],
    )
    return jwt.encode(
        data.model_dump(),
        settings.jwt.secret_key,
        settings.jwt.algorithm,
    )
