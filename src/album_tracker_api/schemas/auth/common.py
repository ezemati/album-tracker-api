from datetime import datetime

from ..base import BaseSchema


class JwtFields(BaseSchema):
    sub: str
    email: str
    exp: datetime
    roles: list[str]
