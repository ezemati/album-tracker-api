from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..dependencies import SessionDep
from ..models import Album, AlbumSection, AlbumTrackerBase, Card
from ..schemas import (
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


class AlbumCatalogHandler:
    session: AsyncSession

    def __init__(self, session: SessionDep) -> None:
        self.session = session

    async def list_albums(self) -> list[AlbumSummaryResponse]:
        albums = (await self.session.scalars(select(Album).where(Album.is_active).order_by(Album.name))).all()
        return [AlbumSummaryResponse.from_album(album) for album in albums]

    async def get_album(self, album_id: UUID) -> AlbumDetailResponse:
        album = await self.__get_active_album(album_id, load_sections=True)
        return self.__album_detail_response(album)

    async def __get_active_album(self, album_id: UUID, load_sections: bool = False) -> Album:
        statement = select(Album).where(Album.id == album_id, Album.is_active)
        if load_sections:
            statement = statement.options(selectinload(Album.sections).selectinload(AlbumSection.cards))
        album = (await self.session.scalars(statement)).first()
        if album is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")
        return album

    def __album_detail_response(self, album: Album) -> AlbumDetailResponse:
        return AlbumDetailResponse(
            id=album.id,
            name=album.name,
            slug=album.slug,
            description=album.description,
            year=album.year,
            is_active=album.is_active,
            total_cards=len(album.get_all_cards()),
            sections=[self.__section_response(section) for section in album.sections],
        )

    def __section_response(self, section: AlbumSection) -> AlbumSectionResponse:
        return AlbumSectionResponse(
            id=section.id,
            album_id=section.album_id,
            name=section.name,
            order_index=section.order_index,
            cards=[CardResponse.model_validate(card) for card in section.cards],
        )


class AlbumAdminHandler:
    session: AsyncSession

    def __init__(self, session: SessionDep) -> None:
        self.session = session

    async def create_album(self, request: AlbumCreateRequest) -> AlbumSummaryResponse:
        album = Album(**request.model_dump())
        self.session.add(album)
        await self.__commit_or_conflict("Album data conflicts with an existing album")
        await self.session.refresh(album)
        return AlbumSummaryResponse.from_album(album)

    async def update_album(self, album_id: UUID, request: AlbumUpdateRequest) -> AlbumSummaryResponse:
        album = await self.__get_album(album_id)
        self.__apply_updates(album, request)
        await self.__commit_or_conflict("Album data conflicts with an existing album")
        await self.session.refresh(album)
        return AlbumSummaryResponse.from_album(album)

    async def delete_album(self, album_id: UUID) -> bool:
        album = await self.__get_album(album_id)
        await self.session.delete(album)
        await self.session.commit()
        return True

    async def create_section(self, album_id: UUID, request: AlbumSectionCreateRequest) -> AlbumSectionResponse:
        _ = await self.__get_album(album_id)
        section = AlbumSection(album_id=album_id, **request.model_dump())
        self.session.add(section)
        await self.__commit_or_conflict("Section order already exists in this album")
        await self.session.refresh(section)
        return self.__section_response(section)

    async def update_section(self, section_id: UUID, request: AlbumSectionUpdateRequest) -> AlbumSectionResponse:
        section = await self.__get_section(section_id)
        self.__apply_updates(section, request)
        await self.__commit_or_conflict("Section order already exists in this album")
        await self.session.refresh(section)
        return self.__section_response(section)

    async def delete_section(self, section_id: UUID) -> bool:
        section = await self.__get_section(section_id)
        await self.session.delete(section)
        await self.session.commit()
        return True

    async def create_card(self, album_id: UUID, request: CardCreateRequest) -> CardResponse:
        album = await self.__get_album(album_id)
        if not album.has_section_id(request.section_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Album '{album_id}' doesn't have section '{request.section_id}'",
            )
        card = Card(**request.model_dump())
        self.session.add(card)
        await self.__commit_or_conflict("Card code already exists in this section")
        await self.session.refresh(card)
        return CardResponse.model_validate(card)

    async def create_cards(self, album_id: UUID, request: BulkCardCreateRequest) -> list[CardResponse]:
        if len(request.cards) == 0:
            return []

        section_ids = {card.section_id for card in request.cards}
        valid_section_ids = set(
            (
                await self.session.scalars(
                    select(AlbumSection.id).where(AlbumSection.album_id == album_id, AlbumSection.id.in_(section_ids))
                )
            ).all()
        )
        if valid_section_ids != section_ids:
            missing_section_ids = section_ids.difference(valid_section_ids)
            missing_section_ids = ", ".join(str(id) for id in missing_section_ids)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"The following sections were not found: {missing_section_ids}",
            )

        cards = [Card(**card.model_dump()) for card in request.cards]
        self.session.add_all(cards)
        await self.__commit_or_conflict("One or more card codes already exist in their sections")
        for card in cards:
            await self.session.refresh(card)
        return [CardResponse.model_validate(card) for card in cards]

    async def update_card(self, card_id: UUID, request: CardUpdateRequest) -> CardResponse:
        card = await self.__get_card(card_id)
        if request.section_id is not None:
            section_is_in_same_album = card.section.album.has_section_id(request.section_id)
            if not section_is_in_same_album:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Section '{request.section_id}' isn't part of album {card.section.album.id}",
                )
        self.__apply_updates(card, request)
        await self.__commit_or_conflict("Card data conflicts with an existing card")
        await self.session.refresh(card)
        return CardResponse.model_validate(card)

    async def delete_card(self, card_id: UUID) -> bool:
        card = await self.__get_card(card_id)
        await self.session.delete(card)
        await self.session.commit()
        return True

    async def __get_album(self, album_id: UUID) -> Album:
        album = (await self.session.scalars(select(Album).where(Album.id == album_id))).first()
        if album is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")
        return album

    async def __get_section(self, section_id: UUID) -> AlbumSection:
        section = (await self.session.scalars(select(AlbumSection).where(AlbumSection.id == section_id))).first()
        if section is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
        return section

    async def __get_card(self, card_id: UUID) -> Card:
        card = (await self.session.scalars(select(Card).where(Card.id == card_id))).first()
        if card is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        return card

    def __section_response(self, section: AlbumSection) -> AlbumSectionResponse:
        return AlbumSectionResponse(
            id=section.id,
            album_id=section.album_id,
            name=section.name,
            order_index=section.order_index,
            cards=[],
        )

    async def __commit_or_conflict(self, detail: str) -> None:
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    def __apply_updates(self, model: AlbumTrackerBase, request: BaseModel) -> None:
        for field in request.model_fields_set:
            setattr(model, field, getattr(request, field))
