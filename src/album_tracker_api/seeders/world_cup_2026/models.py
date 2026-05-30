from pydantic import BaseModel


class WorldCup2026File(BaseModel):
    edition: str
    stickers: list[WorldCup2026Sticker]


class WorldCup2026Sticker(BaseModel):
    code: str
    name: str
    team: str
