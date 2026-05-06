from pydantic import BaseModel

from ..base import BaseSchema


class LoginRequest(BaseSchema):
    email: str
    password: str


class LoginResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    refresh_token: str
