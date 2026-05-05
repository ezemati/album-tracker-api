from uuid import UUID, uuid7

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class AlbumTrackerBase(Base):
    __abstract__ = True

    id: Mapped[UUID] = mapped_column(primary_key=True)

    def __init__(self, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = uuid7()
        super().__init__(**kwargs)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return pascal_to_snake(cls.__name__)


def pascal_to_snake(text: str) -> str:
    if not text:
        return ""

    chars = []
    for i, char in enumerate(text):
        if i > 0 and char.isupper():
            prev_char = text[i - 1]

            # Look ahead to see if the next character is lowercase
            # (helps split acronyms from standard words, e.g., 'HTTP' and 'Request')
            next_is_lower = i + 1 < len(text) and text[i + 1].islower()

            # Add an underscore if transitioning from lower/digit to upper,
            # or if transitioning out of an acronym into a normal word
            if prev_char.islower() or prev_char.isdigit() or next_is_lower:
                chars.append("_")

        chars.append(char.lower())

    return "".join(chars)
