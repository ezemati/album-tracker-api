from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import SessionDep
from ..models import Album, AlbumSection, Card, User, UserCard, UserCollection
from ..schemas import (
    AdjustCardQuantityRequest,
    AlbumSummaryResponse,
    CardResponse,
    SetCardQuantityRequest,
    UserCardResponse,
    UserCollectionDetailResponse,
    UserCollectionSummaryResponse,
)


class UserCollectionHandler:
    session: AsyncSession

    def __init__(self, session: SessionDep) -> None:
        self.session = session

    async def list_collections(self, user: User) -> list[UserCollectionSummaryResponse]:
        user_collections = (
            await self.session.scalars(
                select(UserCollection)
                .join(Album, UserCollection.album_id == Album.id)
                .where(UserCollection.user_id == user.id)
                .order_by(Album.name)
            )
        ).all()
        return [await self.__build_summary(collection) for collection in user_collections]

    async def subscribe(self, user: User, album_id: UUID) -> UserCollectionSummaryResponse:
        # ! Allow users to subscribe to the same Album more than once
        # ! (e.g. if they want to have two Collections of the same Album)
        # existing_user_collection = await self.__get_user_collection(user, album_id, required=False)
        # if existing_user_collection is not None:
        #     return await self.__build_summary(existing_user_collection)

        album = (await self.session.scalars(select(Album).where(Album.id == album_id, Album.is_active))).first()
        if album is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

        user_collection = UserCollection(user_id=user.id, album_id=album_id)
        self.session.add(user_collection)
        await self.session.commit()
        await self.session.refresh(user_collection)
        return await self.__build_summary(user_collection)

    async def unsubscribe(self, user: User, user_collection_id: UUID) -> bool:
        user_collection = await self.__get_user_collection_or_none(user, user_collection_id)
        await self.session.delete(user_collection)
        await self.session.commit()
        return True

    async def get_collection(self, user: User, user_collection_id: UUID) -> UserCollectionDetailResponse:
        user_collection = await self.__get_user_collection_or_raise(user, user_collection_id)
        album = await self.__get_album(user_collection.album_id)
        cards = await self.__get_collection_cards(user_collection)
        return UserCollectionDetailResponse(
            **self.__summary_from_cards(user_collection, album, cards).model_dump(),
            cards=cards,
        )

    async def get_missing_cards(self, user: User, user_collection_id: UUID) -> list[UserCardResponse]:
        collection = await self.get_collection(user, user_collection_id)
        return [card for card in collection.cards if card.is_missing]

    async def get_tradable_cards(self, user: User, user_collection_id: UUID) -> list[UserCardResponse]:
        collection = await self.get_collection(user, user_collection_id)
        return [card for card in collection.cards if card.is_tradable]

    async def set_card_quantity(
        self,
        user: User,
        user_collection_id: UUID,
        card_id: UUID,
        request: SetCardQuantityRequest,
    ) -> UserCardResponse:
        user_collection = await self.__get_user_collection_or_raise(user, user_collection_id)
        user_card = await self.__set_quantity(user_collection, card_id, request.quantity)
        await self.session.commit()
        await self.session.refresh(user_card)
        return self.__user_card_response(user_card.card, user_card.quantity)

    async def adjust_card_quantity(
        self,
        user: User,
        user_collection_id: UUID,
        card_id: UUID,
        request: AdjustCardQuantityRequest,
    ) -> UserCardResponse:
        user_collection = await self.__get_user_collection_or_raise(user, user_collection_id)
        user_card = await self.__get_user_card(user_collection.id, card_id)
        current_quantity = user_card.quantity if user_card is not None else 0
        new_quantity = current_quantity + request.delta
        if new_quantity < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Card quantity cannot be negative")
        user_card = await self.__set_quantity(user_collection, card_id, new_quantity)
        await self.session.commit()
        await self.session.refresh(user_card)
        return self.__user_card_response(user_card.card, new_quantity)

    async def __get_user_collection_or_raise(self, user: User, user_collection_id: UUID) -> UserCollection:
        user_collection = await self.__get_user_collection_or_none(user, user_collection_id)
        if user_collection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User doesn't have a Collection with id '{user_collection_id}'",
            )
        return user_collection

    async def __get_user_collection_or_none(self, user: User, user_collection_id: UUID) -> UserCollection | None:
        user_collection = (
            await self.session.scalars(
                select(UserCollection).where(UserCollection.user_id == user.id, UserCollection.id == user_collection_id)
            )
        ).first()
        return user_collection

    async def __get_album(self, album_id: UUID) -> Album:
        album = (await self.session.scalars(select(Album).where(Album.id == album_id))).first()
        if album is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")
        return album

    async def __get_user_card(self, user_collection_id: UUID, card_id: UUID) -> UserCard | None:
        return (
            await self.session.scalars(
                select(UserCard).where(UserCard.user_collection_id == user_collection_id, UserCard.card_id == card_id)
            )
        ).first()

    async def __set_quantity(
        self,
        user_collection: UserCollection,
        card_id: UUID,
        quantity: int,
    ) -> UserCard:
        user_card = await self.__get_user_card(user_collection.id, card_id)
        if user_card is None:
            user_card = UserCard(user_collection_id=user_collection.id, card_id=card_id, quantity=quantity)
            self.session.add(user_card)
        else:
            user_card.quantity = quantity

        # TODO: remove UserCard object if quantity == 0
        # if quantity == 0:
        #     if user_card is not None:
        #         await self.session.delete(user_card)
        #     return

        return user_card

    async def __get_collection_cards(self, user_collection: UserCollection) -> list[UserCardResponse]:
        rows = (
            await self.session.execute(
                select(Card, func.coalesce(UserCard.quantity, 0))
                .join(AlbumSection, Card.section_id == AlbumSection.id)
                .outerjoin(
                    UserCard,
                    and_(UserCard.card_id == Card.id, UserCard.user_collection_id == user_collection.id),
                )
                .where(AlbumSection.album_id == user_collection.album_id)
                .order_by(AlbumSection.order_index, Card.order_index)
            )
        ).all()
        rows = [r.tuple() for r in rows]
        return [self.__user_card_response(card, quantity) for card, quantity in rows]

    async def __build_summary(self, user_collection: UserCollection) -> UserCollectionSummaryResponse:
        album = await self.__get_album(user_collection.album_id)
        cards = await self.__get_collection_cards(user_collection)
        return self.__summary_from_cards(user_collection, album, cards)

    def __summary_from_cards(
        self,
        user_collection: UserCollection,
        album: Album,
        cards: list[UserCardResponse],
    ) -> UserCollectionSummaryResponse:
        total_cards = len(cards)
        owned_cards = len([card for card in cards if card.quantity > 0])
        missing_cards = total_cards - owned_cards
        tradable_cards = len([card for card in cards if card.quantity >= 2])
        completion_percentage = round((owned_cards / total_cards) * 100, 2) if total_cards else 0
        return UserCollectionSummaryResponse(
            id=user_collection.id,
            album=AlbumSummaryResponse.from_album(album),
            created_at=user_collection.created_at,
            owned_cards=owned_cards,
            missing_cards=missing_cards,
            tradable_cards=tradable_cards,
            completion_percentage=completion_percentage,
        )

    def __user_card_response(self, card: Card, quantity: int) -> UserCardResponse:
        return UserCardResponse(
            card=CardResponse.model_validate(card),
            quantity=quantity,
            is_missing=quantity == 0,
            is_tradable=quantity >= 2,
            tradable_copies=max(quantity - 1, 0),
        )
