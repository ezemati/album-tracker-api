from datetime import datetime
from typing import Literal

from ..base import BaseSchema


class JwtFields(BaseSchema):
    sub: str
    email: str
    exp: datetime
    token_type: Literal["access", "refresh"]
    roles: list[str]
