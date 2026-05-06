from fastapi import APIRouter, Depends

from ..dependencies import CurrentUserDep, get_current_user
from ..schemas import BaseResponse, MeResponse

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
