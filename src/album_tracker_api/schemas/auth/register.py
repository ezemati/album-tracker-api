from ..base import BaseSchema


class RegisterRequest(BaseSchema):
    email: str
    password: str


class RegisterResponse(BaseSchema):
    user_id: str
