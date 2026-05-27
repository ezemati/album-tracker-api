from http import HTTPStatus
from uuid import uuid7

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from album_tracker_api.handlers import get_password_hash
from album_tracker_api.models import Album, AlbumSection, Card, User, UserCard, UserCollection
from album_tracker_api.schemas import TradeOptionsResponse


async def create_user(
    session: AsyncSession,
    *,
    email: str = "otheruser@example.com",
    password: str = "testpassword",
) -> User:
    user = User(
        id=uuid7(),
        email=email,
        password_hash=get_password_hash(password),
    )
    session.add(user)
    await session.commit()
    return user


async def create_album(
    session: AsyncSession,
    *,
    name: str = "Test Album",
    slug: str = "test-album",
) -> Album:
    album = Album(name=name, slug=slug)
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
    code: str,
    name: str,
    order_index: int,
) -> Card:
    card = Card(section_id=section.id, code=code, name=name, order_index=order_index)
    session.add(card)
    await session.commit()
    return card


async def create_user_collection(session: AsyncSession, user: User, album: Album) -> UserCollection:
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
    card_a = await create_card(session, section, code="A", name="Card A", order_index=1)
    card_b = await create_card(session, section, code="B", name="Card B", order_index=2)
    card_c = await create_card(session, section, code="C", name="Card C", order_index=3)
    return album, card_a, card_b, card_c


class TestGetTradeOptions:
    async def test_get_trade_options_returns_mutual_trade_matches(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card_a, card_b, card_c = await create_album_with_cards(session)
        other_user = await create_user(session)
        current_collection = await create_user_collection(session, test_user, album)
        other_collection = await create_user_collection(session, other_user, album)

        # Current user is missing Card C, other user is missing Card B
        await create_user_card(session, current_collection, card_a, quantity=1)
        await create_user_card(session, current_collection, card_b, quantity=2)
        await create_user_card(session, other_collection, card_a, quantity=1)
        await create_user_card(session, other_collection, card_c, quantity=2)

        response = await client.get(f"/trades/collections/{current_collection.id}/users/{other_user.id}/options")

        assert response.status_code == HTTPStatus.OK
        response = TradeOptionsResponse.model_validate(response.json()["data"])
        assert [card.id for card in response.current_user_needs] == [card_c.id]
        assert [card.id for card in response.other_user_needs] == [card_b.id]

    async def test_get_trade_options_returns_empty_lists_when_no_trade_is_possible(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card_a, card_b, _ = await create_album_with_cards(session)
        other_user = await create_user(session)
        current_collection = await create_user_collection(session, test_user, album)
        other_collection = await create_user_collection(session, other_user, album)

        # Both users have Cards A and B
        await create_user_card(session, current_collection, card_a, quantity=1)
        await create_user_card(session, current_collection, card_b, quantity=1)
        await create_user_card(session, other_collection, card_a, quantity=1)
        await create_user_card(session, other_collection, card_b, quantity=1)

        response = await client.get(f"/trades/collections/{current_collection.id}/users/{other_user.id}/options")

        assert response.status_code == HTTPStatus.OK
        response = TradeOptionsResponse.model_validate(response.json()["data"])
        assert response.current_user_needs == []
        assert response.other_user_needs == []

    async def test_get_trade_options_preserves_album_card_order(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album, card_a, card_b, card_c = await create_album_with_cards(session)
        second_section = await create_section(session, album, name="Second", order_index=2)
        card_d = await create_card(session, second_section, code="D", name="Card D", order_index=1)
        card_e = await create_card(session, second_section, code="E", name="Card E", order_index=2)
        other_user = await create_user(session)
        current_collection = await create_user_collection(session, test_user, album)
        other_collection = await create_user_collection(session, other_user, album)

        # Current user is missing Cards B and D, other user is missing Cards A and E
        await create_user_card(session, current_collection, card_a, quantity=2)
        await create_user_card(session, current_collection, card_c, quantity=1)
        await create_user_card(session, current_collection, card_e, quantity=2)
        await create_user_card(session, other_collection, card_b, quantity=2)
        await create_user_card(session, other_collection, card_c, quantity=1)
        await create_user_card(session, other_collection, card_d, quantity=2)

        response = await client.get(f"/trades/collections/{current_collection.id}/users/{other_user.id}/options")

        assert response.status_code == HTTPStatus.OK
        response = TradeOptionsResponse.model_validate(response.json()["data"])
        assert [card.id for card in response.current_user_needs] == [card_b.id, card_d.id]
        assert [card.id for card in response.other_user_needs] == [card_a.id, card_e.id]

    async def test_get_trade_options_rejects_unknown_current_user_collection(
        self,
        client: AsyncClient,
    ) -> None:
        collection_id = uuid7()
        other_user_id = uuid7()

        response = await client.get(f"/trades/collections/{collection_id}/users/{other_user_id}/options")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"User doesn't have a Collection with id '{collection_id}'"

    async def test_get_trade_options_rejects_other_user_without_matching_collection(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album = await create_album(session)
        other_user = await create_user(session)
        current_collection = await create_user_collection(session, test_user, album)

        response = await client.get(f"/trades/collections/{current_collection.id}/users/{other_user.id}/options")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Other user doesn't have a Collection for this Album"

    async def test_get_trade_options_rejects_other_user_with_multiple_matching_collections(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        album = await create_album(session)
        other_user = await create_user(session)
        current_collection = await create_user_collection(session, test_user, album)
        await create_user_collection(session, other_user, album)
        await create_user_collection(session, other_user, album)

        response = await client.get(f"/trades/collections/{current_collection.id}/users/{other_user.id}/options")

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json()["detail"] == "Other user has multiple Collections for this Album"
