from fastapi import APIRouter

from album_tracker_api.schemas.base import BaseResponse
from album_tracker_api.schemas.health.healthcheck import HealthCheckResponse

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/")
async def health_check() -> BaseResponse[HealthCheckResponse]:
    return BaseResponse(data=HealthCheckResponse(status="ok"))
