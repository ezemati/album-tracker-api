from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from album_tracker_api.handlers.auth.login_handler import LoginHandler
from album_tracker_api.handlers.auth.register_handler import RegisterHandler
from album_tracker_api.schemas.auth.login import LoginResponse
from album_tracker_api.schemas.auth.register import RegisterRequest, RegisterResponse
from album_tracker_api.schemas.base import BaseResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    responses={
        status.HTTP_200_OK: {"description": "Login successful"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid credentials"},
    },
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    handler: Annotated[LoginHandler, Depends()],
) -> LoginResponse:
    response = await handler.handle(form_data)
    return response


@router.post(
    "/register",
    responses={
        status.HTTP_201_CREATED: {
            "description": "User registered successfully",
            "model": BaseResponse[RegisterResponse],
        },
        status.HTTP_400_BAD_REQUEST: {"description": "Username or email already exists"},
    },
)
async def register(
    request: RegisterRequest,
    handler: Annotated[RegisterHandler, Depends()],
) -> JSONResponse:
    response = await handler.handle(request)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=BaseResponse(data=response).model_dump_json(),
    )
