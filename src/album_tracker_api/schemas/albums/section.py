from uuid import UUID

from pydantic import Field

from ..base import BaseSchema
from .card import CardResponse


class AlbumSectionCreateRequest(BaseSchema):
    name: str
    code: str
    order_index: int


class AlbumSectionUpdateRequest(BaseSchema):
    name: str | None = None
    code: str | None = None
    order_index: int | None = None


class AlbumSectionResponse(BaseSchema):
    id: UUID
    album_id: UUID
    name: str
    code: str
    order_index: int
    cards: list[CardResponse] = Field(default_factory=list)
