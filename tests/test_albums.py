from http import HTTPStatus
from uuid import uuid7

from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from album_tracker_api.models import Album, AlbumSection, Card
from album_tracker_api.schemas import (
    AlbumCreateRequest,
    AlbumDetailResponse,
    AlbumSectionCreateRequest,
    AlbumSectionResponse,
    AlbumSectionUpdateRequest,
    AlbumSummaryResponse,
    AlbumUpdateRequest,
    BulkCardCreateRequest,
    CardCreateRequest,
    CardResponse,
    CardUpdateRequest,
)


async def create_album(
    session: AsyncSession,
    *,
    name: str = "Test Album",
    slug: str = "test-album",
    description: str | None = "A test album",
    year: int | None = 2026,
    is_active: bool = True,
) -> Album:
    album = Album(name=name, slug=slug, description=description, year=year, is_active=is_active)
    session.add(album)
    await session.commit()
    return album


async def create_section(
    session: AsyncSession,
    album: Album,
    *,
    name: str = "Base",
    order_index: int = 1,
) -> AlbumSection:
    section = AlbumSection(album_id=album.id, name=name, order_index=order_index)
    session.add(section)
    await session.commit()
    return section


async def create_card(
    session: AsyncSession,
    section: AlbumSection,
    *,
    code: str = "001",
    name: str = "First Card",
    order_index: int = 1,
    image_url: str | None = "https://example.com/card.png",
) -> Card:
    card = Card(section_id=section.id, code=code, name=name, order_index=order_index, image_url=image_url)
    session.add(card)
    await session.commit()
    return card


def as_json(request: BaseModel) -> dict[str, object]:
    return request.model_dump(mode="json", exclude_unset=True)


class TestListAlbums:
    async def test_list_albums_returns_active_albums_ordered_by_name(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        z_album = await create_album(session, name="Z Album", slug="z-album")
        inactive_album = await create_album(session, name="Inactive Album", slug="inactive-album", is_active=False)
        a_album = await create_album(session, name="A Album", slug="a-album")

        response = await client.get("/albums/")

        assert response.status_code == HTTPStatus.OK
        albums = [AlbumSummaryResponse.model_validate(album) for album in response.json()["data"]]
        assert [album.id for album in albums] == [a_album.id, z_album.id]
        assert inactive_album.id not in [album.id for album in albums]

    async def test_list_albums_returns_empty_list(self, client: AsyncClient) -> None:
        response = await client.get("/albums/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["data"] == []


class TestGetAlbum:
    async def test_get_album_returns_album_details_with_sections_and_cards(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        second_section = await create_section(session, album, name="Second", order_index=2)
        first_section = await create_section(session, album, name="First", order_index=1)
        await create_card(session, first_section, code="002", name="Second Card", order_index=2)
        await create_card(session, first_section, code="001", name="First Card", order_index=1)
        await create_card(session, second_section, code="101", name="Other Card", order_index=1)

        response = await client.get(f"/albums/{album.id}")

        assert response.status_code == HTTPStatus.OK
        album_response = AlbumDetailResponse.model_validate(response.json()["data"])
        assert album_response.id == album.id
        assert album_response.total_cards == 3
        assert [section.name for section in album_response.sections] == ["First", "Second"]
        assert [card.code for card in album_response.sections[0].cards] == ["001", "002"]

    async def test_get_album_rejects_unknown_album(self, client: AsyncClient) -> None:
        response = await client.get(f"/albums/{uuid7()}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_get_album_rejects_inactive_album(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session, is_active=False)

        response = await client.get(f"/albums/{album.id}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_get_album_rejects_invalid_album_id(self, client: AsyncClient) -> None:
        response = await client.get("/albums/not-a-uuid")

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestCreateAlbum:
    async def test_create_album_creates_album(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        request = AlbumCreateRequest(name="New Album", slug="new-album", description="New", year=2025)

        response = await admin_client.post("/albums/", json=as_json(request))

        assert response.status_code == HTTPStatus.CREATED
        album_response = AlbumSummaryResponse.model_validate(response.json()["data"])
        saved_album = (await session.scalars(select(Album).where(Album.id == album_response.id))).one()
        assert saved_album.name == request.name
        assert saved_album.slug == request.slug
        assert album_response.total_cards == 0

    async def test_create_album_rejects_unauthenticated_user(self, unauthenticated_client: AsyncClient) -> None:
        request = AlbumCreateRequest(name="New Album", slug="new-album")

        response = await unauthenticated_client.post("/albums/", json=as_json(request))

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    async def test_create_album_rejects_non_admin_user(self, client: AsyncClient) -> None:
        request = AlbumCreateRequest(name="New Album", slug="new-album")

        response = await client.post("/albums/", json=as_json(request))

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json()["detail"] == "You do not have permission to perform this action"

    async def test_create_album_rejects_duplicate_slug(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        await create_album(session, slug="duplicate")
        request = AlbumCreateRequest(name="Duplicate", slug="duplicate")

        response = await admin_client.post("/albums/", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Album data conflicts with an existing album"

    async def test_create_album_rejects_missing_name(self, admin_client: AsyncClient) -> None:
        response = await admin_client.post("/albums/", json={"slug": "missing-name"})

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestUpdateAlbum:
    async def test_update_album_updates_only_provided_fields(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session, name="Old", slug="old", description="Keep", year=1999)
        request = AlbumUpdateRequest(name="New", is_active=False)

        response = await admin_client.patch(f"/albums/{album.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        album_response = AlbumSummaryResponse.model_validate(response.json()["data"])
        await session.refresh(album)
        assert album_response.name == "New"
        assert album_response.slug == "old"
        assert album.description == "Keep"
        assert album.is_active is False

    async def test_update_album_rejects_unknown_album(self, admin_client: AsyncClient) -> None:
        request = AlbumUpdateRequest(name="Missing")

        response = await admin_client.patch(f"/albums/{uuid7()}", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_update_album_rejects_duplicate_slug(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session, slug="first")
        await create_album(session, name="Second", slug="second")
        request = AlbumUpdateRequest(slug="second")

        response = await admin_client.patch(f"/albums/{album.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Album data conflicts with an existing album"

    async def test_update_album_rejects_non_admin_user(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        request = AlbumUpdateRequest(name="New")

        response = await client.patch(f"/albums/{album.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.FORBIDDEN

    async def test_update_album_rejects_invalid_album_id(self, admin_client: AsyncClient) -> None:
        request = AlbumUpdateRequest(name="New")

        response = await admin_client.patch("/albums/not-a-uuid", json=as_json(request))

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestDeleteAlbum:
    async def test_delete_album_deletes_album_and_nested_resources(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        card = await create_card(session, section)
        album_id = album.id
        section_id = section.id
        card_id = card.id

        response = await admin_client.delete(f"/albums/{album_id}")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.content == b""
        assert await session.get(Album, album_id) is None
        assert await session.get(AlbumSection, section_id) is None
        assert await session.get(Card, card_id) is None

    async def test_delete_album_rejects_unknown_album(self, admin_client: AsyncClient) -> None:
        response = await admin_client.delete(f"/albums/{uuid7()}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_delete_album_rejects_non_admin_user(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)

        response = await client.delete(f"/albums/{album.id}")

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestCreateSection:
    async def test_create_section_creates_section(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        request = AlbumSectionCreateRequest(name="Base", order_index=1)

        response = await admin_client.post(f"/albums/{album.id}/sections", json=as_json(request))

        assert response.status_code == HTTPStatus.CREATED
        section_response = AlbumSectionResponse.model_validate(response.json()["data"])
        saved_section = await session.get(AlbumSection, section_response.id)
        assert saved_section is not None
        assert section_response.album_id == album.id
        assert section_response.name == request.name
        assert section_response.cards == []

    async def test_create_section_rejects_unknown_album(self, admin_client: AsyncClient) -> None:
        request = AlbumSectionCreateRequest(name="Base", order_index=1)

        response = await admin_client.post(f"/albums/{uuid7()}/sections", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_create_section_rejects_duplicate_order_index(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        await create_section(session, album, order_index=1)
        request = AlbumSectionCreateRequest(name="Duplicate", order_index=1)

        response = await admin_client.post(f"/albums/{album.id}/sections", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Section order already exists in this album"

    async def test_create_section_rejects_non_admin_user(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        request = AlbumSectionCreateRequest(name="Base", order_index=1)

        response = await client.post(f"/albums/{album.id}/sections", json=as_json(request))

        assert response.status_code == HTTPStatus.FORBIDDEN

    async def test_create_section_rejects_missing_name(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)

        response = await admin_client.post(f"/albums/{album.id}/sections", json={"orderIndex": 1})

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestUpdateSection:
    async def test_update_section_updates_only_provided_fields(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        section = await create_section(session, album, name="Old", order_index=1)
        request = AlbumSectionUpdateRequest(name="New")

        response = await admin_client.patch(f"/albums/{album.id}/sections/{section.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        section_response = AlbumSectionResponse.model_validate(response.json()["data"])
        await session.refresh(section)
        assert section_response.name == "New"
        assert section_response.order_index == 1
        assert section.name == "New"

    async def test_update_section_rejects_unknown_section(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        request = AlbumSectionUpdateRequest(name="Missing")

        response = await admin_client.patch(f"/albums/{album.id}/sections/{uuid7()}", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Section not found"

    async def test_update_section_rejects_section_from_different_album(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session, slug="album")
        other_album = await create_album(session, name="Other", slug="other")
        section = await create_section(session, other_album)
        request = AlbumSectionUpdateRequest(name="Wrong album")

        response = await admin_client.patch(f"/albums/{album.id}/sections/{section.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Section not found"

    async def test_update_section_rejects_duplicate_order_index(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        section = await create_section(session, album, order_index=1)
        await create_section(session, album, name="Second", order_index=2)
        request = AlbumSectionUpdateRequest(order_index=2)

        response = await admin_client.patch(f"/albums/{album.id}/sections/{section.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Section order already exists in this album"

    async def test_update_section_rejects_non_admin_user(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        request = AlbumSectionUpdateRequest(name="New")

        response = await client.patch(f"/albums/{album.id}/sections/{section.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestDeleteSection:
    async def test_delete_section_deletes_section_and_cards(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        card = await create_card(session, section)
        section_id = section.id
        card_id = card.id

        response = await admin_client.delete(f"/albums/{album.id}/sections/{section_id}")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.content == b""
        assert await session.get(AlbumSection, section_id) is None
        assert await session.get(Card, card_id) is None

    async def test_delete_section_rejects_unknown_section(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)

        response = await admin_client.delete(f"/albums/{album.id}/sections/{uuid7()}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Section not found"

    async def test_delete_section_rejects_section_from_different_album(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session, slug="album")
        other_album = await create_album(session, name="Other", slug="other")
        section = await create_section(session, other_album)
        section_id = section.id

        response = await admin_client.delete(f"/albums/{album.id}/sections/{section_id}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Section not found"
        assert await session.get(AlbumSection, section_id) is not None

    async def test_delete_section_rejects_non_admin_user(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)

        response = await client.delete(f"/albums/{album.id}/sections/{section.id}")

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestCreateCard:
    async def test_create_card_creates_card(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        request = CardCreateRequest(section_id=section.id, code="001", name="Card", order_index=1)

        response = await admin_client.post(f"/albums/{album.id}/cards", json=as_json(request))

        assert response.status_code == HTTPStatus.CREATED
        card_response = CardResponse.model_validate(response.json()["data"])
        saved_card = await session.get(Card, card_response.id)
        assert saved_card is not None
        assert card_response.section_id == section.id
        assert card_response.code == request.code

    async def test_create_card_rejects_unknown_album(self, admin_client: AsyncClient) -> None:
        request = CardCreateRequest(section_id=uuid7(), code="001", name="Card", order_index=1)

        response = await admin_client.post(f"/albums/{uuid7()}/cards", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_create_card_rejects_section_from_different_album(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session, slug="album")
        other_album = await create_album(session, name="Other", slug="other")
        other_section = await create_section(session, other_album)
        request = CardCreateRequest(section_id=other_section.id, code="001", name="Card", order_index=1)

        response = await admin_client.post(f"/albums/{album.id}/cards", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"Album '{album.id}' doesn't have section '{other_section.id}'"

    async def test_create_card_rejects_duplicate_code(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        await create_card(session, section, code="001", order_index=1)
        request = CardCreateRequest(section_id=section.id, code="001", name="Duplicate", order_index=2)

        response = await admin_client.post(f"/albums/{album.id}/cards", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Card code already exists in this section"

    async def test_create_card_rejects_duplicate_order_index(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        await create_card(session, section, code="001", order_index=1)
        request = CardCreateRequest(section_id=section.id, code="002", name="Duplicate order", order_index=1)

        response = await admin_client.post(f"/albums/{album.id}/cards", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Card code already exists in this section"

    async def test_create_card_rejects_non_admin_user(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        request = CardCreateRequest(section_id=section.id, code="001", name="Card", order_index=1)

        response = await client.post(f"/albums/{album.id}/cards", json=as_json(request))

        assert response.status_code == HTTPStatus.FORBIDDEN

    async def test_create_card_rejects_missing_code(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)

        response = await admin_client.post(
            f"/albums/{album.id}/cards",
            json={"sectionId": str(section.id), "name": "Card", "orderIndex": 1},
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestCreateCards:
    async def test_create_cards_creates_multiple_cards(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        request = BulkCardCreateRequest(
            cards=[
                CardCreateRequest(section_id=section.id, code="001", name="First", order_index=1),
                CardCreateRequest(section_id=section.id, code="002", name="Second", order_index=2),
            ]
        )

        response = await admin_client.post(f"/albums/{album.id}/cards/bulk", json=as_json(request))

        assert response.status_code == HTTPStatus.CREATED
        cards = [CardResponse.model_validate(card) for card in response.json()["data"]]
        assert [card.code for card in cards] == ["001", "002"]
        saved_cards = (
            await session.scalars(select(Card).where(Card.section_id == section.id).order_by(Card.order_index))
        ).all()
        assert [card.code for card in saved_cards] == ["001", "002"]

    async def test_create_cards_returns_empty_list_for_empty_request(
        self, admin_client: AsyncClient, session: AsyncSession
    ) -> None:
        album = await create_album(session)
        request = BulkCardCreateRequest(cards=[])

        response = await admin_client.post(f"/albums/{album.id}/cards/bulk", json=as_json(request))

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["data"] == []

    async def test_create_cards_rejects_missing_section(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        missing_section_id = uuid7()
        request = BulkCardCreateRequest(
            cards=[CardCreateRequest(section_id=missing_section_id, code="001", name="Card", order_index=1)]
        )

        response = await admin_client.post(f"/albums/{album.id}/cards/bulk", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"The following sections were not found: {missing_section_id}"

    async def test_create_cards_rejects_unknown_album_for_empty_request(self, admin_client: AsyncClient) -> None:
        request = BulkCardCreateRequest(cards=[])

        response = await admin_client.post(f"/albums/{uuid7()}/cards/bulk", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_create_cards_rejects_unknown_album_for_non_empty_request(self, admin_client: AsyncClient) -> None:
        request = BulkCardCreateRequest(
            cards=[CardCreateRequest(section_id=uuid7(), code="001", name="Card", order_index=1)]
        )

        response = await admin_client.post(f"/albums/{uuid7()}/cards/bulk", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_create_cards_rejects_section_from_different_album(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session, slug="album")
        other_album = await create_album(session, name="Other", slug="other")
        other_section = await create_section(session, other_album)
        request = BulkCardCreateRequest(
            cards=[CardCreateRequest(section_id=other_section.id, code="001", name="Card", order_index=1)]
        )

        response = await admin_client.post(f"/albums/{album.id}/cards/bulk", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"The following sections were not found: {other_section.id}"

    async def test_create_cards_rejects_duplicate_existing_code(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        await create_card(session, section, code="001", order_index=1)
        request = BulkCardCreateRequest(
            cards=[CardCreateRequest(section_id=section.id, code="001", name="Duplicate", order_index=2)]
        )

        response = await admin_client.post(f"/albums/{album.id}/cards/bulk", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "One or more card codes already exist in their sections"

    async def test_create_cards_rejects_non_admin_user(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        request = BulkCardCreateRequest(
            cards=[CardCreateRequest(section_id=section.id, code="001", name="Card", order_index=1)]
        )

        response = await client.post(f"/albums/{album.id}/cards/bulk", json=as_json(request))

        assert response.status_code == HTTPStatus.FORBIDDEN

    async def test_create_cards_rejects_invalid_card_payload(
        self, admin_client: AsyncClient, session: AsyncSession
    ) -> None:
        album = await create_album(session)

        response = await admin_client.post(f"/albums/{album.id}/cards/bulk", json={"cards": [{"code": "001"}]})

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestUpdateCard:
    async def test_update_card_updates_only_provided_fields(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        card = await create_card(session, section, code="001", name="Old", order_index=1)
        request = CardUpdateRequest(name="New", image_url=None)

        response = await admin_client.patch(f"/albums/{album.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        card_response = CardResponse.model_validate(response.json()["data"])
        await session.refresh(card)
        assert card_response.name == "New"
        assert card_response.code == "001"
        assert card.image_url is None

    async def test_update_card_moves_card_to_another_section_in_same_album(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        first_section = await create_section(session, album, order_index=1)
        second_section = await create_section(session, album, name="Second", order_index=2)
        card = await create_card(session, first_section)
        request = CardUpdateRequest(section_id=second_section.id)

        response = await admin_client.patch(f"/albums/{album.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        card_response = CardResponse.model_validate(response.json()["data"])
        assert card_response.section_id == second_section.id

    async def test_update_card_rejects_unknown_card(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        request = CardUpdateRequest(name="Missing")

        response = await admin_client.patch(f"/albums/{album.id}/cards/{uuid7()}", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Card not found"

    async def test_update_card_rejects_card_from_different_album(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session, slug="album")
        other_album = await create_album(session, name="Other", slug="other")
        other_section = await create_section(session, other_album)
        card = await create_card(session, other_section)
        request = CardUpdateRequest(name="Wrong album")

        response = await admin_client.patch(f"/albums/{album.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Card not found"

    async def test_update_card_rejects_move_to_section_in_different_album(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session, slug="album")
        section = await create_section(session, album)
        other_album = await create_album(session, name="Other", slug="other")
        other_section = await create_section(session, other_album)
        card = await create_card(session, section)
        request = CardUpdateRequest(section_id=other_section.id)

        response = await admin_client.patch(f"/albums/{album.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == f"Section '{other_section.id}' isn't part of album {album.id}"

    async def test_update_card_rejects_duplicate_code(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        card = await create_card(session, section, code="001", order_index=1)
        await create_card(session, section, code="002", name="Second", order_index=2)
        request = CardUpdateRequest(code="002")

        response = await admin_client.patch(f"/albums/{album.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Card data conflicts with an existing card"

    async def test_update_card_rejects_non_admin_user(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        card = await create_card(session, section)
        request = CardUpdateRequest(name="New")

        response = await client.patch(f"/albums/{album.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestDeleteCard:
    async def test_delete_card_deletes_card(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        card = await create_card(session, section)

        response = await admin_client.delete(f"/albums/{album.id}/cards/{card.id}")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.content == b""
        assert await session.get(Card, card.id) is None

    async def test_delete_card_rejects_unknown_card(self, admin_client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)

        response = await admin_client.delete(f"/albums/{album.id}/cards/{uuid7()}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Card not found"

    async def test_delete_card_rejects_card_from_different_album(
        self,
        admin_client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session, slug="album")
        other_album = await create_album(session, name="Other", slug="other")
        other_section = await create_section(session, other_album)
        card = await create_card(session, other_section)
        card_id = card.id

        response = await admin_client.delete(f"/albums/{album.id}/cards/{card_id}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Card not found"
        assert await session.get(Card, card_id) is not None

    async def test_delete_card_rejects_non_admin_user(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session)
        section = await create_section(session, album)
        card = await create_card(session, section)

        response = await client.delete(f"/albums/{album.id}/cards/{card.id}")

        assert response.status_code == HTTPStatus.FORBIDDEN
