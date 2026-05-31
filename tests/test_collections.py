from http import HTTPStatus
from uuid import uuid7

from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession

from album_tracker_api.models import Album, AlbumSection, Card, User, UserCard, UserCollection
from album_tracker_api.schemas import (
    AdjustCardQuantityRequest,
    SetCardQuantityRequest,
    SubscribeToAlbumRequest,
    UserCardResponse,
    UserCollectionDetailResponse,
    UserCollectionSummaryResponse,
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
    section = AlbumSection(album_id=album.id, name=name, code=name, order_index=order_index)
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


async def create_user_collection(session: AsyncSession, user: User, album: Album) -> UserCollection:
    # await session.refresh(user)
    user_collection = UserCollection(user_id=user.id, album_id=album.id)
    session.add(user_collection)
    await session.commit()
    return user_collection


async def create_user_card(
    session: AsyncSession,
    user_collection: UserCollection,
    card: Card,
    *,
    quantity: int,
) -> UserCard:
    user_card = UserCard(user_collection_id=user_collection.id, card_id=card.id, quantity=quantity)
    session.add(user_card)
    await session.commit()
    return user_card


async def create_album_with_cards(session: AsyncSession) -> tuple[Album, Card, Card, Card]:
    album = await create_album(session)
    section = await create_section(session, album)
    missing_card = await create_card(session, section, code="001", name="Missing", order_index=1)
    owned_card = await create_card(session, section, code="002", name="Owned", order_index=2)
    tradable_card = await create_card(session, section, code="003", name="Tradable", order_index=3)
    return album, missing_card, owned_card, tradable_card


def as_json(request: BaseModel) -> dict[str, object]:
    return request.model_dump(mode="json", exclude_unset=True)


class TestListCollections:
    async def test_list_collections_returns_empty_list(self, client: AsyncClient) -> None:
        response = await client.get("/collections/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["data"] == []

    async def test_list_collections_returns_user_collections_ordered_by_album_name(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
        admin_user: User,
    ) -> None:
        z_album = await create_album(session, name="Z Album", slug="z-album")
        a_album = await create_album(session, name="A Album", slug="a-album")
        other_album = await create_album(session, name="Other Album", slug="other-album")
        z_collection = await create_user_collection(session, test_user, z_album)
        a_collection = await create_user_collection(session, test_user, a_album)
        other_collection = await create_user_collection(session, admin_user, other_album)

        response = await client.get("/collections/")

        assert response.status_code == HTTPStatus.OK
        collections = [UserCollectionSummaryResponse.model_validate(item) for item in response.json()["data"]]
        assert [collection.id for collection in collections] == [a_collection.id, z_collection.id]
        assert other_collection.id not in [collection.id for collection in collections]

    async def test_list_collections_uses_bounded_summary_queries(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, _, owned_card, tradable_card = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        await create_user_card(session, user_collection, owned_card, quantity=1)
        await create_user_card(session, user_collection, tradable_card, quantity=3)
        session.expunge_all()
        select_count = 0

        def count_selects(*args: object) -> None:
            nonlocal select_count
            statement = str(args[2]).lstrip()
            if statement.upper().startswith("SELECT"):
                select_count += 1

        event.listen(session.bind.sync_engine, "before_cursor_execute", count_selects)
        try:
            response = await client.get("/collections/")
        finally:
            event.remove(session.bind.sync_engine, "before_cursor_execute", count_selects)

        assert response.status_code == HTTPStatus.OK
        collections = [UserCollectionSummaryResponse.model_validate(item) for item in response.json()["data"]]
        assert len(collections) == 1
        assert collections[0].id == user_collection.id
        assert collections[0].owned_cards == 2
        assert collections[0].missing_cards == 1
        assert collections[0].tradable_cards == 1
        assert collections[0].completion_percentage == 66.67
        assert select_count <= 2


class TestSubscribe:
    async def test_subscribe_creates_collection_for_active_album(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album, _, _, _ = await create_album_with_cards(session)
        request = SubscribeToAlbumRequest(album_id=album.id)

        response = await client.post("/collections/", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        collection = UserCollectionSummaryResponse.model_validate(response.json()["data"])
        saved_collection = await session.get(UserCollection, collection.id)
        assert saved_collection is not None
        assert saved_collection.album_id == album.id
        assert collection.album.id == album.id
        assert collection.owned_cards == 0
        assert collection.missing_cards == 3
        assert collection.tradable_cards == 0
        assert collection.completion_percentage == 0

    async def test_subscribe_allows_duplicate_collections_for_same_album(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        album = await create_album(session)
        request = SubscribeToAlbumRequest(album_id=album.id)

        first_response = await client.post("/collections/", json=as_json(request))
        second_response = await client.post("/collections/", json=as_json(request))

        assert first_response.status_code == HTTPStatus.OK
        assert second_response.status_code == HTTPStatus.OK
        first_collection = UserCollectionSummaryResponse.model_validate(first_response.json()["data"])
        second_collection = UserCollectionSummaryResponse.model_validate(second_response.json()["data"])
        assert first_collection.id != second_collection.id

    async def test_subscribe_rejects_unknown_album(self, client: AsyncClient) -> None:
        request = SubscribeToAlbumRequest(album_id=uuid7())

        response = await client.post("/collections/", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_subscribe_rejects_inactive_album(self, client: AsyncClient, session: AsyncSession) -> None:
        album = await create_album(session, is_active=False)
        request = SubscribeToAlbumRequest(album_id=album.id)

        response = await client.post("/collections/", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Album not found"

    async def test_subscribe_rejects_missing_album_id(self, client: AsyncClient) -> None:
        response = await client.post("/collections/", json={})

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestUnsubscribe:
    async def test_unsubscribe_deletes_collection_and_user_cards(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, _, owned_card, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        user_card = await create_user_card(session, user_collection, owned_card, quantity=1)
        collection_id = user_collection.id
        user_card_id = user_card.id

        response = await client.delete(f"/collections/{collection_id}")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.content == b""
        assert await session.get(UserCollection, collection_id) is None
        assert await session.get(UserCard, user_card_id) is None

    async def test_unsubscribe_rejects_unknown_collection(self, client: AsyncClient) -> None:
        collection_id = uuid7()

        response = await client.delete(f"/collections/{collection_id}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"User doesn't have a Collection with id '{collection_id}'"

    async def test_unsubscribe_rejects_collection_owned_by_another_user(
        self,
        client: AsyncClient,
        session: AsyncSession,
        admin_user: User,
    ) -> None:
        album = await create_album(session)
        user_collection = await create_user_collection(session, admin_user, album)
        collection_id = user_collection.id

        response = await client.delete(f"/collections/{collection_id}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"User doesn't have a Collection with id '{collection_id}'"
        assert await session.get(UserCollection, collection_id) is not None


class TestGetCollection:
    async def test_get_collection_returns_summary_and_all_cards(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, missing_card, owned_card, tradable_card = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        await create_user_card(session, user_collection, owned_card, quantity=1)
        await create_user_card(session, user_collection, tradable_card, quantity=3)

        response = await client.get(f"/collections/{user_collection.id}")

        assert response.status_code == HTTPStatus.OK
        collection = UserCollectionDetailResponse.model_validate(response.json()["data"])
        assert collection.id == user_collection.id
        assert collection.album.id == album.id
        assert collection.owned_cards == 2
        assert collection.missing_cards == 1
        assert collection.tradable_cards == 1
        assert collection.completion_percentage == 66.67
        assert [user_card.card.id for user_card in collection.cards] == [
            missing_card.id,
            owned_card.id,
            tradable_card.id,
        ]
        assert [user_card.quantity for user_card in collection.cards] == [0, 1, 3]
        assert [user_card.is_missing for user_card in collection.cards] == [True, False, False]
        assert [user_card.is_tradable for user_card in collection.cards] == [False, False, True]
        assert [user_card.tradable_copies for user_card in collection.cards] == [0, 0, 2]

    async def test_get_collection_returns_zero_summary_for_album_without_cards(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album = await create_album(session)
        user_collection = await create_user_collection(session, test_user, album)

        response = await client.get(f"/collections/{user_collection.id}")

        assert response.status_code == HTTPStatus.OK
        collection = UserCollectionDetailResponse.model_validate(response.json()["data"])
        assert collection.cards == []
        assert collection.owned_cards == 0
        assert collection.missing_cards == 0
        assert collection.tradable_cards == 0
        assert collection.completion_percentage == 0

    async def test_get_collection_rejects_unknown_collection(self, client: AsyncClient) -> None:
        collection_id = uuid7()

        response = await client.get(f"/collections/{collection_id}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"User doesn't have a Collection with id '{collection_id}'"

    async def test_get_collection_rejects_collection_owned_by_another_user(
        self,
        client: AsyncClient,
        session: AsyncSession,
        admin_user: User,
    ) -> None:
        album = await create_album(session)
        user_collection = await create_user_collection(session, admin_user, album)

        response = await client.get(f"/collections/{user_collection.id}")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"User doesn't have a Collection with id '{user_collection.id}'"


class TestGetMissingCards:
    async def test_get_missing_cards_returns_only_missing_cards(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, missing_card, owned_card, tradable_card = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        await create_user_card(session, user_collection, owned_card, quantity=1)
        await create_user_card(session, user_collection, tradable_card, quantity=2)

        response = await client.get(f"/collections/{user_collection.id}/missing-cards")

        assert response.status_code == HTTPStatus.OK
        cards = [UserCardResponse.model_validate(item) for item in response.json()["data"]]
        assert [card.card.id for card in cards] == [missing_card.id]
        assert cards[0].quantity == 0
        assert cards[0].is_missing is True

    async def test_get_missing_cards_returns_empty_list_when_no_cards_are_missing(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, first_card, second_card, third_card = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        await create_user_card(session, user_collection, first_card, quantity=1)
        await create_user_card(session, user_collection, second_card, quantity=1)
        await create_user_card(session, user_collection, third_card, quantity=2)

        response = await client.get(f"/collections/{user_collection.id}/missing-cards")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["data"] == []

    async def test_get_missing_cards_rejects_unknown_collection(self, client: AsyncClient) -> None:
        collection_id = uuid7()

        response = await client.get(f"/collections/{collection_id}/missing-cards")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"User doesn't have a Collection with id '{collection_id}'"


class TestGetTradableCards:
    async def test_get_tradable_cards_returns_only_tradable_cards(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, missing_card, owned_card, tradable_card = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        await create_user_card(session, user_collection, owned_card, quantity=1)
        await create_user_card(session, user_collection, tradable_card, quantity=2)

        response = await client.get(f"/collections/{user_collection.id}/tradable-cards")

        assert response.status_code == HTTPStatus.OK
        cards = [UserCardResponse.model_validate(item) for item in response.json()["data"]]
        assert [card.card.id for card in cards] == [tradable_card.id]
        assert missing_card.id not in [card.card.id for card in cards]
        assert cards[0].quantity == 2
        assert cards[0].is_tradable is True
        assert cards[0].tradable_copies == 1

    async def test_get_tradable_cards_returns_empty_list_when_no_cards_are_tradable(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, _, owned_card, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        await create_user_card(session, user_collection, owned_card, quantity=1)

        response = await client.get(f"/collections/{user_collection.id}/tradable-cards")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["data"] == []

    async def test_get_tradable_cards_rejects_unknown_collection(self, client: AsyncClient) -> None:
        collection_id = uuid7()

        response = await client.get(f"/collections/{collection_id}/tradable-cards")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"User doesn't have a Collection with id '{collection_id}'"


class TestSetCardQuantity:
    async def test_set_card_quantity_creates_user_card(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card, _, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        request = SetCardQuantityRequest(quantity=2)

        response = await client.put(f"/collections/{user_collection.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        user_card = UserCardResponse.model_validate(response.json()["data"])
        saved_user_card = (
            await session.scalars(
                select(UserCard).where(UserCard.user_collection_id == user_collection.id, UserCard.card_id == card.id)
            )
        ).one()
        assert saved_user_card.quantity == 2
        assert user_card.card.id == card.id
        assert user_card.quantity == 2
        assert user_card.is_missing is False
        assert user_card.is_tradable is True
        assert user_card.tradable_copies == 1

    async def test_set_card_quantity_updates_existing_user_card(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card, _, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        user_card = await create_user_card(session, user_collection, card, quantity=1)
        request = SetCardQuantityRequest(quantity=3)

        response = await client.put(f"/collections/{user_collection.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        response_card = UserCardResponse.model_validate(response.json()["data"])
        await session.refresh(user_card)
        assert user_card.quantity == 3
        assert response_card.quantity == 3
        assert response_card.is_tradable is True
        assert response_card.tradable_copies == 2

    async def test_set_card_quantity_allows_zero_quantity(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card, _, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        user_card = await create_user_card(session, user_collection, card, quantity=2)
        request = SetCardQuantityRequest(quantity=0)

        response = await client.put(f"/collections/{user_collection.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        response_card = UserCardResponse.model_validate(response.json()["data"])
        await session.refresh(user_card)
        assert user_card.quantity == 0
        assert response_card.quantity == 0
        assert response_card.is_missing is True
        assert response_card.is_tradable is False
        assert response_card.tradable_copies == 0

    async def test_set_card_quantity_rejects_unknown_collection(self, client: AsyncClient) -> None:
        request = SetCardQuantityRequest(quantity=1)
        collection_id = uuid7()

        response = await client.put(f"/collections/{collection_id}/cards/{uuid7()}", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"User doesn't have a Collection with id '{collection_id}'"

    async def test_set_card_quantity_rejects_negative_quantity(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card, _, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)

        response = await client.put(f"/collections/{user_collection.id}/cards/{card.id}", json={"quantity": -1})

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestAdjustCardQuantity:
    async def test_adjust_card_quantity_creates_user_card_for_positive_delta(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card, _, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        request = AdjustCardQuantityRequest(delta=1)

        response = await client.patch(f"/collections/{user_collection.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        response_card = UserCardResponse.model_validate(response.json()["data"])
        saved_user_card = (
            await session.scalars(
                select(UserCard).where(UserCard.user_collection_id == user_collection.id, UserCard.card_id == card.id)
            )
        ).one()
        assert saved_user_card.quantity == 1
        assert response_card.quantity == 1
        assert response_card.is_missing is False
        assert response_card.is_tradable is False

    async def test_adjust_card_quantity_increments_existing_user_card(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card, _, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        user_card = await create_user_card(session, user_collection, card, quantity=1)
        request = AdjustCardQuantityRequest(delta=2)

        response = await client.patch(f"/collections/{user_collection.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        response_card = UserCardResponse.model_validate(response.json()["data"])
        await session.refresh(user_card)
        assert user_card.quantity == 3
        assert response_card.quantity == 3
        assert response_card.is_tradable is True
        assert response_card.tradable_copies == 2

    async def test_adjust_card_quantity_decrements_existing_user_card(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card, _, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        user_card = await create_user_card(session, user_collection, card, quantity=3)
        request = AdjustCardQuantityRequest(delta=-2)

        response = await client.patch(f"/collections/{user_collection.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.OK
        response_card = UserCardResponse.model_validate(response.json()["data"])
        await session.refresh(user_card)
        assert user_card.quantity == 1
        assert response_card.quantity == 1
        assert response_card.is_tradable is False
        assert response_card.tradable_copies == 0

    async def test_adjust_card_quantity_rejects_negative_result(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card, _, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)
        request = AdjustCardQuantityRequest(delta=-1)

        response = await client.patch(f"/collections/{user_collection.id}/cards/{card.id}", json=as_json(request))

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Card quantity cannot be negative"

    async def test_adjust_card_quantity_rejects_unknown_collection(self, client: AsyncClient) -> None:
        request = AdjustCardQuantityRequest(delta=1)
        collection_id = uuid7()

        response = await client.patch(f"/collections/{collection_id}/cards/{uuid7()}", json=as_json(request))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"User doesn't have a Collection with id '{collection_id}'"

    async def test_adjust_card_quantity_rejects_missing_delta(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card, _, _ = await create_album_with_cards(session)
        user_collection = await create_user_collection(session, test_user, album)

        response = await client.patch(f"/collections/{user_collection.id}/cards/{card.id}", json={})

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
