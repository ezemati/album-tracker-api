from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .album import Album, Card
from .base import AlbumTrackerBase
from .user import User


class UserCollection(AlbumTrackerBase):
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    album_id: Mapped[UUID] = mapped_column(ForeignKey("album.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(lazy="joined")
    album: Mapped[Album] = relationship(lazy="joined")
    cards: Mapped[list[UserCard]] = relationship(
        back_populates="user_collection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UserCard(AlbumTrackerBase):
    __table_args__ = (
        UniqueConstraint("user_collection_id", "card_id", name="uq_user_collection_card"),
        CheckConstraint("quantity >= 0", name="ck_user_card_quantity_non_negative"),
    )

    user_collection_id: Mapped[UUID] = mapped_column(ForeignKey("user_collection.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[UUID] = mapped_column(ForeignKey("card.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(default=0)

    user_collection: Mapped[UserCollection] = relationship(back_populates="cards", lazy="joined")
    card: Mapped[Card] = relationship(lazy="joined")
