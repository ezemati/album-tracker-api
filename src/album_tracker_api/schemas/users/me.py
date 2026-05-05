from uuid import UUID

from album_tracker_api.schemas.base import BaseSchema


class MeResponse(BaseSchema):
    id: UUID
    email: str
