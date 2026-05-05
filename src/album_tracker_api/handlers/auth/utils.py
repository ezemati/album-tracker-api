from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from album_tracker_api.core.config import settings
from album_tracker_api.models.user import User
from album_tracker_api.schemas.auth.common import JwtFields

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
        sub=user.id,
        email=user.email,
        exp=exp,
        roles=["ADMIN"] if user.is_admin else [],
    )
    return jwt.encode(
        data.model_dump(),
        settings.jwt.secret_key,
        settings.jwt.algorithm,
    )
