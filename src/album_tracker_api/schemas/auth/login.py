from album_tracker_api.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    email: str
    password: str


class LoginResponse(BaseSchema):
    token_type: str = "bearer"
    access_token: str
    refresh_token: str
