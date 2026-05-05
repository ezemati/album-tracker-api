from fastapi import APIRouter, Depends

from album_tracker_api.dependencies.user import CurrentUserDep, get_current_user
from album_tracker_api.schemas.base import BaseResponse
from album_tracker_api.schemas.users.me import MeResponse

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/me")
async def me(current_user: CurrentUserDep) -> BaseResponse[MeResponse]:
    return BaseResponse(
        data=MeResponse(
            id=current_user.id,
            email=current_user.email,
        )
    )
