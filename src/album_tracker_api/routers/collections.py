from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from ..dependencies import CurrentUserDep, get_current_user
from ..handlers import UserCollectionHandler
from ..schemas import (
    AdjustCardQuantityRequest,
    BaseResponse,
    SetCardQuantityRequest,
    UserCardResponse,
    UserCollectionDetailResponse,
    UserCollectionSummaryResponse,
)

router = APIRouter(prefix="/collections", tags=["collections"], dependencies=[Depends(get_current_user)])


@router.get("/")
async def list_collections(
    current_user: CurrentUserDep,
    handler: Annotated[UserCollectionHandler, Depends()],
) -> BaseResponse[list[UserCollectionSummaryResponse]]:
    return BaseResponse(data=await handler.list_collections(current_user))


@router.post("/{album_id}")
async def subscribe(
    album_id: UUID,
    current_user: CurrentUserDep,
    handler: Annotated[UserCollectionHandler, Depends()],
) -> BaseResponse[UserCollectionSummaryResponse]:
    return BaseResponse(data=await handler.subscribe(current_user, album_id))


@router.delete("/{user_collection_id}")
async def unsubscribe(
    user_collection_id: UUID,
    current_user: CurrentUserDep,
    handler: Annotated[UserCollectionHandler, Depends()],
) -> BaseResponse[bool]:
    return BaseResponse(data=await handler.unsubscribe(current_user, user_collection_id))


@router.get("/{user_collection_id}")
async def get_collection(
    user_collection_id: UUID,
    current_user: CurrentUserDep,
    handler: Annotated[UserCollectionHandler, Depends()],
) -> BaseResponse[UserCollectionDetailResponse]:
    return BaseResponse(data=await handler.get_collection(current_user, user_collection_id))


@router.get("/{user_collection_id}/missing-cards")
async def get_missing_cards(
    user_collection_id: UUID,
    current_user: CurrentUserDep,
    handler: Annotated[UserCollectionHandler, Depends()],
) -> BaseResponse[list[UserCardResponse]]:
    return BaseResponse(data=await handler.get_missing_cards(current_user, user_collection_id))


@router.get("/{user_collection_id}/tradable-cards")
async def get_tradable_cards(
    user_collection_id: UUID,
    current_user: CurrentUserDep,
    handler: Annotated[UserCollectionHandler, Depends()],
) -> BaseResponse[list[UserCardResponse]]:
    return BaseResponse(data=await handler.get_tradable_cards(current_user, user_collection_id))


@router.put("/{user_collection_id}/cards/{card_id}")
async def set_card_quantity(
    user_collection_id: UUID,
    card_id: UUID,
    request: SetCardQuantityRequest,
    current_user: CurrentUserDep,
    handler: Annotated[UserCollectionHandler, Depends()],
) -> BaseResponse[UserCardResponse]:
    return BaseResponse(data=await handler.set_card_quantity(current_user, user_collection_id, card_id, request))


@router.patch("/{user_collection_id}/cards/{card_id}")
async def adjust_card_quantity(
    user_collection_id: UUID,
    card_id: UUID,
    request: AdjustCardQuantityRequest,
    current_user: CurrentUserDep,
    handler: Annotated[UserCollectionHandler, Depends()],
) -> BaseResponse[UserCardResponse]:
    return BaseResponse(data=await handler.adjust_card_quantity(current_user, user_collection_id, card_id, request))
