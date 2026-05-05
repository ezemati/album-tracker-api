from datetime import datetime
from uuid import UUID

from album_tracker_api.schemas.base import BaseSchema


class JwtFields(BaseSchema):
    sub: UUID
    email: str
    exp: datetime
    roles: list[str]
