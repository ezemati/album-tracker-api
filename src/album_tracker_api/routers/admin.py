from fastapi import APIRouter, Depends

from ..core import AlbumTrackerSettings, settings
from ..dependencies import get_current_admin_user
from ..schemas import BaseResponse

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin_user)])


@router.get("/settings")
async def get_settings() -> BaseResponse[AlbumTrackerSettings]:
    return BaseResponse(data=settings)
