from fastapi import APIRouter

from ..core import AlbumTrackerSettings, settings
from ..schemas import BaseResponse

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/settings")
async def get_settings() -> BaseResponse[AlbumTrackerSettings]:
    return BaseResponse(data=settings)
