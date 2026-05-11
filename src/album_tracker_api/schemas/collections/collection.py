from datetime import datetime
from uuid import UUID

from pydantic import Field

from ..albums import AlbumSummaryResponse, CardResponse
from ..base import BaseSchema


class UserCollectionSummaryResponse(BaseSchema):
    id: UUID
    album: AlbumSummaryResponse
    created_at: datetime
    owned_cards: int
    missing_cards: int
    tradable_cards: int
    completion_percentage: float


class UserCardResponse(BaseSchema):
    card: CardResponse
    quantity: int
    is_missing: bool
    is_tradable: bool
    tradable_copies: int


class UserCollectionDetailResponse(UserCollectionSummaryResponse):
    cards: list[UserCardResponse]


class SubscribeToAlbumRequest(BaseSchema):
    album_id: UUID


class AdjustCardQuantityRequest(BaseSchema):
    delta: int


class SetCardQuantityRequest(BaseSchema):
    quantity: int = Field(ge=0)
