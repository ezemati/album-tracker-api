import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .dependencies import get_db
from .models import Album, AlbumSection, Card
from .seeders import world_cup_2026_seed


async def seed_albums(session: AsyncSession) -> None:
    async def argentina(album: Album) -> None:
        section_argentina = next((s for s in album.sections if s.name == "Argentina"), None)
        if section_argentina is None:
            section_argentina = AlbumSection(album_id=album.id, name="Argentina", code="ARG", order_index=1)
            session.add(section_argentina)

        card_messi = next((c for c in section_argentina.cards if c.name == "Lionel Messi"), None)
        if card_messi is None:
            card_messi = Card(section_id=section_argentina.id, code="ARG 01", name="Lionel Messi", order_index=1)
            session.add(card_messi)

        card_dimaria = next((c for c in section_argentina.cards if c.name == "Angel Di Maria"), None)
        if card_dimaria is None:
            card_dimaria = Card(section_id=section_argentina.id, code="ARG 02", name="Angel Di Maria", order_index=2)
            session.add(card_dimaria)

    async def brazil(album: Album) -> None:
        section_brazil = next((s for s in album.sections if s.name == "Brazil"), None)
        if section_brazil is None:
            section_brazil = AlbumSection(album_id=album.id, name="Brazil", code="BRA", order_index=2)
            session.add(section_brazil)

        card_neymar = next((c for c in section_brazil.cards if c.name == "Neymar JR"), None)
        if card_neymar is None:
            card_neymar = Card(section_id=section_brazil.id, code="BRA 01", name="Neymar JR", order_index=1)
            session.add(card_neymar)

        card_vinicius = next((c for c in section_brazil.cards if c.name == "Vinicius JR"), None)
        if card_vinicius is None:
            card_vinicius = Card(section_id=section_brazil.id, code="BRA 02", name="Vinicius JR", order_index=2)
            session.add(card_vinicius)

    async def seed_world_cup_2026() -> None:
        world_cup_album = (
            await session.scalars(select(Album).where(Album.slug == "fake-world-cup-2026"))
        ).one_or_none()
        if world_cup_album is None:
            world_cup_album = Album(
                name="FAKE World Cup 2026",
                slug="fake-world-cup-2026",
                description="FAKE - FIFA World Cup 2026 Album",
                year=2026,
                is_active=True,
            )
            session.add(world_cup_album)

        await argentina(world_cup_album)
        await brazil(world_cup_album)
        await session.commit()

    await seed_world_cup_2026()


async def seed(session: AsyncSession) -> None:
    await seed_albums(session)
    await world_cup_2026_seed(session)


async def main():
    session_dep = asynccontextmanager(get_db)
    async with session_dep() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
