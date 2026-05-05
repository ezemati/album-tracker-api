from fastapi import APIRouter

from album_tracker_api.core.config import AlbumTrackerSettings, settings
from album_tracker_api.schemas.base import BaseResponse

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/settings")
async def get_settings() -> BaseResponse[AlbumTrackerSettings]:
    return BaseResponse(data=settings)
