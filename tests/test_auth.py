from http import HTTPStatus
from uuid import uuid7

from fastapi.security import OAuth2PasswordRequestForm
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from album_tracker_api.handlers import create_token, get_password_hash, verify_password
from album_tracker_api.models import User
from album_tracker_api.schemas import LoginResponse, RegisterRequest, RegisterResponse
from album_tracker_api.schemas.auth.refresh import RefreshRequest


class TestRegister:
    async def test_register_creates_user(self, unauthenticated_client: AsyncClient, session: AsyncSession) -> None:
        request = RegisterRequest(email="newuser@example.com", password="newpassword")
        response = await unauthenticated_client.post("/auth/register", json=request.model_dump())

        assert response.status_code == HTTPStatus.CREATED
        response_data = response.json()
        response = RegisterResponse.model_validate(response_data["data"])

        saved_user = (await session.scalars(select(User).where(User.email == request.email))).one()
        assert saved_user.id == response.user_id
        assert verify_password(saved_user.password_hash, request.password)

    async def test_register_rejects_duplicate_email(self, unauthenticated_client: AsyncClient, test_user: User) -> None:
        request = RegisterRequest(email=test_user.email, password="newpassword")
        response = await unauthenticated_client.post("/auth/register", json=request.model_dump())

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Username or email already exists"

    async def test_register_rejects_missing_email(self, unauthenticated_client: AsyncClient) -> None:
        request = RegisterRequest.model_construct(email="", password="newpassword")
        response = await unauthenticated_client.post("/auth/register", json=request.model_dump())

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_register_rejects_missing_password(self, unauthenticated_client: AsyncClient) -> None:
        request = RegisterRequest.model_construct(email="newuser@example.com", password="")
        response = await unauthenticated_client.post("/auth/register", json=request.model_dump())

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestLogin:
    async def test_login_returns_tokens_for_valid_credentials(
        self,
        unauthenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        request = OAuth2PasswordRequestForm(username=test_user.email, password="testpassword")
        response = await unauthenticated_client.post(
            "/auth/login",
            data={"username": request.username, "password": request.password},
        )

        assert response.status_code == HTTPStatus.OK
        login_response = LoginResponse.model_validate(response.json())
        assert login_response.token_type == "bearer"
        assert login_response.access_token
        assert login_response.refresh_token
        assert login_response.user.id == test_user.id
        assert login_response.user.email == test_user.email

    async def test_login_rejects_unknown_user(self, unauthenticated_client: AsyncClient) -> None:
        request = OAuth2PasswordRequestForm(username="unknown@example.com", password="testpassword")
        response = await unauthenticated_client.post(
            "/auth/login",
            data={"username": request.username, "password": request.password},
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["detail"] == "Invalid username or password"

    async def test_login_rejects_wrong_password(self, unauthenticated_client: AsyncClient, test_user: User) -> None:
        request = OAuth2PasswordRequestForm(username=test_user.email, password="wrongpassword")
        response = await unauthenticated_client.post(
            "/auth/login",
            data={"username": request.username, "password": request.password},
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["detail"] == "Invalid username or password"

    async def test_login_rejects_missing_username(self, unauthenticated_client: AsyncClient) -> None:
        request = OAuth2PasswordRequestForm(username="", password="testpassword")
        response = await unauthenticated_client.post("/auth/login", data={"password": request.password})

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_login_rejects_missing_password(self, unauthenticated_client: AsyncClient, test_user: User) -> None:
        request = OAuth2PasswordRequestForm(username=test_user.email, password="")
        response = await unauthenticated_client.post("/auth/login", data={"username": request.username})

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_login_rejects_json_body(self, unauthenticated_client: AsyncClient, test_user: User) -> None:
        request = OAuth2PasswordRequestForm(username=test_user.email, password="testpassword")
        response = await unauthenticated_client.post(
            "/auth/login",
            json={"username": request.username, "password": request.password},
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestRefresh:
    async def test_refresh_returns_new_tokens_for_valid_refresh_token(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        refresh_token = create_token(test_user, "refresh")
        request = RefreshRequest(refresh_token=refresh_token)
        response = await client.post("/auth/refresh", json=request.model_dump())

        assert response.status_code == HTTPStatus.OK
        login_response = LoginResponse.model_validate(response.json())
        assert login_response.token_type == "bearer"
        assert login_response.access_token
        assert login_response.refresh_token
        assert login_response.user.id == test_user.id
        assert login_response.user.email == test_user.email

    async def test_refresh_rejects_malformed_token(self, client: AsyncClient) -> None:
        request = RefreshRequest(refresh_token="not-a-jwt")
        response = await client.post("/auth/refresh", json=request.model_dump())

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["detail"] == "Could not validate refresh token"

    async def test_refresh_rejects_access_token(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        access_token = create_token(test_user, "access")
        request = RefreshRequest(refresh_token=access_token)
        response = await client.post("/auth/refresh", json=request.model_dump())

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["detail"] == "Could not validate refresh token"

    async def test_refresh_rejects_token_for_missing_user(self, client: AsyncClient) -> None:
        missing_user = User(
            id=uuid7(),
            email="missing@example.com",
            password_hash=get_password_hash("testpassword"),
        )
        refresh_token = create_token(missing_user, "refresh")
        request = RefreshRequest(refresh_token=refresh_token)
        response = await client.post("/auth/refresh", json=request.model_dump())

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["detail"] == "Could not validate refresh token"

    async def test_refresh_rejects_missing_refresh_token(self, client: AsyncClient) -> None:
        request = RefreshRequest.model_construct(refresh_token="")
        response = await client.post("/auth/refresh", json=request.model_dump())

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
