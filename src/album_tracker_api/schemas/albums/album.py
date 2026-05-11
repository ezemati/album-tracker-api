from typing import Any
from uuid import UUID

from pydantic import Field

from ...models import Album
from ..base import BaseSchema
from .section import AlbumSectionResponse


class AlbumCreateRequest(BaseSchema):
    name: str
    slug: str
    description: str | None = None
    year: int | None = None
    is_active: bool = True


class AlbumUpdateRequest(BaseSchema):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    year: int | None = None
    is_active: bool | None = None


class AlbumSummaryResponse(BaseSchema):
    id: UUID
    name: str
    slug: str
    description: str | None
    year: int | None
    is_active: bool
    total_cards: int

    @staticmethod
    def from_album(album: Album) -> AlbumSummaryResponse:
        data: dict[str, Any] = {}
        for field_name in AlbumSummaryResponse.model_fields:
            if field_name == "total_cards":
                continue
            if hasattr(album, field_name):
                data[field_name] = getattr(album, field_name)
        data["total_cards"] = len(album.get_all_cards())
        return AlbumSummaryResponse.model_validate(data)


class AlbumDetailResponse(AlbumSummaryResponse):
    sections: list[AlbumSectionResponse] = Field(default_factory=list)
