from uuid import UUID

from ..base import BaseSchema


class CardCreateRequest(BaseSchema):
    section_id: UUID
    code: str
    name: str
    order_index: int
    image_url: str | None = None


class CardUpdateRequest(BaseSchema):
    section_id: UUID | None = None
    code: str | None = None
    name: str | None = None
    order_index: int | None = None
    image_url: str | None = None


class BulkCardCreateRequest(BaseSchema):
    cards: list[CardCreateRequest]


class CardResponse(BaseSchema):
    id: UUID
    section_id: UUID
    code: str
    name: str
    order_index: int
    image_url: str | None
