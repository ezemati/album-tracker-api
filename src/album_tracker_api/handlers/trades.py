from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import SessionDep
from ..models import AlbumSection, Card, User, UserCard, UserCollection
from ..schemas import CardResponse, TradeOptionsResponse, UserCardResponse


class TradeHandler:
    session: AsyncSession

    def __init__(self, session: SessionDep) -> None:
        self.session = session

    async def get_trade_options(
        self,
        user: User,
        user_collection_id: UUID,
        other_user_id: UUID,
    ) -> TradeOptionsResponse:
        current_collection = await self.__get_user_collection_or_raise(user, user_collection_id)
        other_collection = await self.__get_other_user_collection_or_raise(other_user_id, current_collection.album_id)

        current_cards = await self.__get_collection_cards(current_collection)
        other_cards = await self.__get_collection_cards(other_collection)
        other_quantities = {user_card.card.id: user_card.quantity for user_card in other_cards}

        current_user_needs = [
            user_card.card
            for user_card in current_cards
            if user_card.quantity == 0 and other_quantities.get(user_card.card.id, 0) >= 2
        ]
        other_user_needs = [
            user_card.card
            for user_card in current_cards
            if user_card.quantity >= 2 and other_quantities.get(user_card.card.id, 0) == 0
        ]

        return TradeOptionsResponse(
            current_user_needs=current_user_needs,
            other_user_needs=other_user_needs,
        )

    async def __get_user_collection_or_raise(self, user: User, user_collection_id: UUID) -> UserCollection:
        user_collection = (
            await self.session.scalars(
                select(UserCollection).where(UserCollection.user_id == user.id, UserCollection.id == user_collection_id)
            )
        ).first()
        if user_collection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User doesn't have a Collection with id '{user_collection_id}'",
            )
        return user_collection

    async def __get_other_user_collection_or_raise(self, other_user_id: UUID, album_id: UUID) -> UserCollection:
        user_collections = (
            await self.session.scalars(
                select(UserCollection)
                .where(UserCollection.user_id == other_user_id, UserCollection.album_id == album_id)
                .limit(2)
            )
        ).all()
        if len(user_collections) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Other user doesn't have a Collection for this Album",
            )
        if len(user_collections) > 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Other user has multiple Collections for this Album",
            )
        return user_collections[0]

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
        rows = [row._tuple() for row in rows]
        return [self.__user_card_response(card, quantity) for card, quantity in rows]

    def __user_card_response(self, card: Card, quantity: int) -> UserCardResponse:
        return UserCardResponse(
            card=CardResponse.model_validate(card),
            quantity=quantity,
            is_missing=quantity == 0,
            is_tradable=quantity >= 2,
            tradable_copies=max(quantity - 1, 0),
        )
