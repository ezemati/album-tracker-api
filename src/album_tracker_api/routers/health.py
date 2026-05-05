from fastapi import APIRouter

from album_tracker_api.schemas.health.healthcheck import HealthCheckResponse

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/")
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="ok")
