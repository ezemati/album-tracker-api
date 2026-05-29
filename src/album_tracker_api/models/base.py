from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    declared_attr,
    mapped_column,
)


class Base(AsyncAttrs, MappedAsDataclass, DeclarativeBase):
    pass


class AlbumTrackerBase(Base, kw_only=True):
    __abstract__ = True

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid7)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return pascal_to_snake(cls.__name__)


class TimestampMixin(MappedAsDataclass):
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), init=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        init=False,
    )


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
