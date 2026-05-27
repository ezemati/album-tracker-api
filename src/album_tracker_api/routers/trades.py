from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from ..dependencies import CurrentUserDep, get_current_user
from ..handlers import TradeHandler
from ..schemas import BaseResponse, TradeOptionsResponse

router = APIRouter(prefix="/trades", tags=["trades"], dependencies=[Depends(get_current_user)])


@router.get("/collections/{user_collection_id}/users/{other_user_id}/options")
async def get_trade_options(
    user_collection_id: UUID,
    other_user_id: UUID,
    current_user: CurrentUserDep,
    handler: Annotated[TradeHandler, Depends()],
) -> BaseResponse[TradeOptionsResponse]:
    return BaseResponse(data=await handler.get_trade_options(current_user, user_collection_id, other_user_id))
