from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from album_tracker_api.models import Album, User
from album_tracker_api.schemas import AlbumSummaryResponse, MeResponse


async def test_client_uses_test_database(client: AsyncClient, session: AsyncSession) -> None:
    new_album = Album(name="Test Album", slug="test-album")
    session.add(new_album)
    await session.commit()

    response = await client.get("/albums/")

    assert response.status_code == 200
    response_data = response.json()
    albums = [AlbumSummaryResponse.model_validate(album) for album in response_data["data"]]
    assert len(albums) == 1
    album = albums[0]
    assert album.id == new_album.id
    assert album.name == new_album.name
    assert album.slug == new_album.slug

    users = (await session.scalars(select(User))).all()
    assert len(users) > 0


async def test_database_is_clean_for_each_test(client: AsyncClient) -> None:
    response = await client.get("/albums/")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 0


async def test_authenticated_client_uses_test_user(client: AsyncClient, session: AsyncSession, test_user: User) -> None:
    saved_user = (await session.scalars(select(User).where(User.id == test_user.id))).one()

    response = await client.get("/users/me")

    assert response.status_code == 200
    response_data = response.json()
    me_response = MeResponse.model_validate(response_data["data"])
    assert me_response.id == saved_user.id
    assert me_response.email == saved_user.email
