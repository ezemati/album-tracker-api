from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from album_tracker_api.models import Album, AlbumSection
from album_tracker_api.seeders import WorldCup2026File, WorldCup2026Sticker, world_cup_2026_seed_data


async def get_seeded_album(session: AsyncSession) -> Album | None:
    return (
        await session.scalars(
            select(Album)
            .options(selectinload(Album.sections).selectinload(AlbumSection.cards))
            .where(Album.slug == "fifa-world-cup-2026")
        )
    ).one_or_none()


def create_world_cup_file() -> WorldCup2026File:
    return WorldCup2026File(
        edition="Panini FIFA World Cup 2026 - Standard Edition",
        stickers=[
            WorldCup2026Sticker(code="00", name="Panini Logo", team="We Are Panini"),
            WorldCup2026Sticker(code="FWC1", name="Official Emblem1", team="FIFA World Cup 2026"),
            WorldCup2026Sticker(code="MEX1", name="Emblem", team="Mexico"),
            WorldCup2026Sticker(code="MEX2", name="Luis Malagon", team="Mexico"),
        ],
    )


async def test_seed_creates_world_cup_album_sections_and_cards(session: AsyncSession) -> None:
    world_cup_file = create_world_cup_file()

    await world_cup_2026_seed_data(session, world_cup_file)

    album = await get_seeded_album(session)
    assert album is not None
    assert album.name == "FIFA World Cup 2026"
    assert album.description == world_cup_file.edition
    assert album.year == 2026
    assert album.is_active is True
    assert [section.name for section in album.sections] == [
        "We Are Panini",
        "FIFA World Cup 2026",
        "Mexico",
    ]
    assert [section.order_index for section in album.sections] == [1, 2, 3]
    assert [card.code for card in album.sections[2].cards] == ["MEX1", "MEX2"]
    assert [card.name for card in album.sections[2].cards] == ["Emblem", "Luis Malagon"]
    assert [card.order_index for card in album.sections[2].cards] == [1, 2]


async def test_seed_is_idempotent(session: AsyncSession) -> None:
    world_cup_file = create_world_cup_file()

    await world_cup_2026_seed_data(session, world_cup_file)
    await world_cup_2026_seed_data(session, world_cup_file)

    album = await get_seeded_album(session)
    assert album is not None
    assert len(album.sections) == 3
    assert sum(len(section.cards) for section in album.sections) == 4
