from fastapi import APIRouter

from album_tracker_api.core.config import AlbumTrackerSettings, settings

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/settings")
async def get_settings() -> AlbumTrackerSettings:
    return settings
