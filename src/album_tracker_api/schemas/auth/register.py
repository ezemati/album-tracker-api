from uuid import UUID

from album_tracker_api.schemas.base import BaseSchema


class RegisterRequest(BaseSchema):
    email: str
    password: str


class RegisterResponse(BaseSchema):
    user_id: UUID
