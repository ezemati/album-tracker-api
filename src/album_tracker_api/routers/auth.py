import json
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from ..handlers import LoginHandler, RefreshHandler, RegisterHandler
from ..schemas import BaseResponse, LoginResponse, RefreshRequest, RegisterRequest, RegisterResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    responses={
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
    "/refresh",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid refresh token"},
    },
)
async def refresh(
    request: RefreshRequest,
    handler: Annotated[RefreshHandler, Depends()],
) -> LoginResponse:
    response = await handler.handle(request)
    return response


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
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
        content=json.loads(BaseResponse(data=response).model_dump_json()),
    )
