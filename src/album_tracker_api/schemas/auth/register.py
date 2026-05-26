from uuid import UUID

from pydantic import EmailStr, Field

from ..base import BaseSchema


class RegisterRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterResponse(BaseSchema):
    user_id: UUID
