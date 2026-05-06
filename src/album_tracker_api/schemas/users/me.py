from uuid import UUID

from ..base import BaseSchema


class MeResponse(BaseSchema):
    id: UUID
    email: str
