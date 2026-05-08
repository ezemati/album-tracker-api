from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AlbumTrackerBase


class Album(AlbumTrackerBase):
    name: Mapped[str] = mapped_column()
    slug: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str | None] = mapped_column(default=None)
    year: Mapped[int | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)

    sections: Mapped[list[AlbumSection]] = relationship(
        back_populates="album",
        cascade="all, delete-orphan",
        order_by="AlbumSection.order_index",
    )

    def get_all_cards(self) -> list[Card]:
        return [card for section in self.sections for card in section.cards]


class AlbumSection(AlbumTrackerBase):
    __table_args__ = (UniqueConstraint("album_id", "order_index", name="uq_section_album_order"),)

    album_id: Mapped[UUID] = mapped_column(ForeignKey("album.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column()
    order_index: Mapped[int] = mapped_column()

    album: Mapped[Album] = relationship(back_populates="sections")
    cards: Mapped[list[Card]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="Card.order_index",
    )


class Card(AlbumTrackerBase):
    __table_args__ = (
        UniqueConstraint("section_id", "code", name="uq_card_section_code"),
        UniqueConstraint("section_id", "order_index", name="uq_card_section_order"),
    )

    section_id: Mapped[UUID] = mapped_column(ForeignKey("album_section.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()
    order_index: Mapped[int] = mapped_column()
    image_url: Mapped[str | None] = mapped_column(default=None)

    section: Mapped[AlbumSection] = relationship(back_populates="cards")
