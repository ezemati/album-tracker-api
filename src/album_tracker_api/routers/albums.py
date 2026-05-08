from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from ..dependencies import CurrentAdminUserDep
from ..handlers import AlbumAdminHandler, AlbumCatalogHandler
from ..schemas import (
    AlbumCreateRequest,
    AlbumDetailResponse,
    AlbumSectionCreateRequest,
    AlbumSectionResponse,
    AlbumSectionUpdateRequest,
    AlbumSummaryResponse,
    AlbumUpdateRequest,
    BaseResponse,
    BulkCardCreateRequest,
    CardCreateRequest,
    CardResponse,
    CardUpdateRequest,
)

router = APIRouter(prefix="/albums", tags=["albums"])


@router.get("/")
async def list_albums(handler: Annotated[AlbumCatalogHandler, Depends()]) -> BaseResponse[list[AlbumSummaryResponse]]:
    return BaseResponse(data=await handler.list_albums())


@router.get("/{album_id}")
async def get_album(
    album_id: UUID,
    handler: Annotated[AlbumCatalogHandler, Depends()],
) -> BaseResponse[AlbumDetailResponse]:
    return BaseResponse(data=await handler.get_album(album_id))


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_album(
    request: AlbumCreateRequest,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[AlbumSummaryResponse]:
    return BaseResponse(data=await handler.create_album(request))


@router.patch("/{album_id}")
async def update_album(
    album_id: UUID,
    request: AlbumUpdateRequest,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[AlbumSummaryResponse]:
    return BaseResponse(data=await handler.update_album(album_id, request))


@router.delete("/{album_id}")
async def delete_album(
    album_id: UUID,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[bool]:
    return BaseResponse(data=await handler.delete_album(album_id))


@router.post("/{album_id}/sections", status_code=status.HTTP_201_CREATED)
async def create_section(
    album_id: UUID,
    request: AlbumSectionCreateRequest,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[AlbumSectionResponse]:
    return BaseResponse(data=await handler.create_section(album_id, request))


@router.patch("/{album_id}/sections/{section_id}")
async def update_section(
    _album_id: UUID,
    section_id: UUID,
    request: AlbumSectionUpdateRequest,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[AlbumSectionResponse]:
    return BaseResponse(data=await handler.update_section(section_id, request))


@router.delete("/{album_id}/sections/{section_id}")
async def delete_section(
    _album_id: UUID,
    section_id: UUID,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[bool]:
    return BaseResponse(data=await handler.delete_section(section_id))


@router.post("/{album_id}/cards", status_code=status.HTTP_201_CREATED)
async def create_card(
    album_id: UUID,
    request: CardCreateRequest,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[CardResponse]:
    return BaseResponse(data=await handler.create_card(album_id, request))


@router.post("/{album_id}/cards/bulk", status_code=status.HTTP_201_CREATED)
async def create_cards(
    album_id: UUID,
    request: BulkCardCreateRequest,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[list[CardResponse]]:
    return BaseResponse(data=await handler.create_cards(album_id, request))


@router.patch("/{album_id}/cards/{card_id}")
async def update_card(
    _album_id: UUID,
    card_id: UUID,
    request: CardUpdateRequest,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[CardResponse]:
    return BaseResponse(data=await handler.update_card(card_id, request))


@router.delete("/{album_id}/cards/{card_id}")
async def delete_card(
    _album_id: UUID,
    card_id: UUID,
    handler: Annotated[AlbumAdminHandler, Depends()],
    _admin: CurrentAdminUserDep,
) -> BaseResponse[bool]:
    return BaseResponse(data=await handler.delete_card(card_id))
