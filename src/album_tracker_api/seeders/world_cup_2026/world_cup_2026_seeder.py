import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core import get_project_root_path
from ...dependencies import get_db
from ...models import Album, AlbumSection, Card
from .models import WorldCup2026File, WorldCup2026Sticker

ALBUM_NAME = "FIFA World Cup 2026"
ALBUM_SLUG = "fifa-world-cup-2026"
ALBUM_YEAR = 2026
WORLD_CUP_2026_JSON_PATH = get_project_root_path() / "static" / "WorldCup2026.json"


async def seed_data(session: AsyncSession, world_cup_2026_file: WorldCup2026File) -> None:
    stickers_by_team: dict[str, list[WorldCup2026Sticker]] = defaultdict(lambda: [])
    for sticker in world_cup_2026_file.stickers:
        stickers_by_team[sticker.team].append(sticker)

    album = (
        await session.scalars(
            select(Album)
            .options(selectinload(Album.sections).selectinload(AlbumSection.cards))
            .where(Album.slug == ALBUM_SLUG)
        )
    ).one_or_none()

    if album is None:
        album = Album(
            name=ALBUM_NAME,
            slug=ALBUM_SLUG,
            description=world_cup_2026_file.edition,
            year=ALBUM_YEAR,
            is_active=True,
        )
        session.add(album)
    else:
        album.name = ALBUM_NAME
        album.description = world_cup_2026_file.edition
        album.year = ALBUM_YEAR
        album.is_active = True

    sections_by_team = {section.name: section for section in album.sections}
    for section_order, (team, team_stickers) in enumerate(stickers_by_team.items(), start=1):
        section = sections_by_team.get(team)
        if section is None:
            section = AlbumSection(album_id=album.id, name=team, code=team, order_index=section_order)
            session.add(section)
            sections_by_team[team] = section

        cards_by_code = {card.code: card for card in section.cards}
        for card_order, sticker in enumerate(team_stickers, start=1):
            if sticker.code not in cards_by_code:
                session.add(
                    Card(
                        section_id=section.id,
                        code=sticker.code,
                        name=sticker.name,
                        order_index=card_order,
                    )
                )

    await session.commit()


async def seed(session: AsyncSession) -> None:
    world_cup_2026_file = WorldCup2026File.model_validate_json(WORLD_CUP_2026_JSON_PATH.read_text("utf-8"))
    await seed_data(session, world_cup_2026_file)


async def _main():
    session_dep = asynccontextmanager(get_db)
    async with session_dep() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(_main())
