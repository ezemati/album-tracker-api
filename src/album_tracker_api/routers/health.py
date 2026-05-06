from fastapi import APIRouter

from ..schemas import BaseResponse, HealthCheckResponse

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/")
async def health_check() -> BaseResponse[HealthCheckResponse]:
    return BaseResponse(data=HealthCheckResponse(status="ok"))
