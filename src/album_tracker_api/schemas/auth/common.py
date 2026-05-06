from datetime import datetime
from uuid import UUID

from ..base import BaseSchema


class JwtFields(BaseSchema):
    sub: UUID
    email: str
    exp: datetime
    roles: list[str]
