from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .album import Album, Card
from .base import AlbumTrackerBase, TimestampMixin
from .user import User


class UserCollection(AlbumTrackerBase, TimestampMixin, kw_only=True):
    """
    A user's personal collection for a specific album.

    Example:
    User John subscribes to FIFA World Cup 2026.
    That creates one UserCollection for John and that Album.
    """

    __table_args__ = (
        # UniqueConstraint("user_id", "album_id", name="uq_user_collection_album"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    album_id: Mapped[UUID] = mapped_column(ForeignKey("album.id", ondelete="CASCADE"), index=True)

    user: Mapped[User] = relationship(lazy="raise", init=False)
    album: Mapped[Album] = relationship(lazy="raise", init=False)
    cards: Mapped[list[UserCard]] = relationship(
        back_populates="user_collection",
        cascade="all, delete-orphan",
        lazy="raise",
        init=False,
    )


class UserCard(AlbumTrackerBase, TimestampMixin, kw_only=True):
    """
    Tracks how many copies of a Card the user has inside a specific UserCollection.

    Examples:
    - Messi quantity = 1
    - Neymar Jr quantity = 2
    - Mbappe quantity = 0 or no row at all
    """

    __table_args__ = (
        UniqueConstraint("user_collection_id", "card_id", name="uq_user_collection_card"),
        CheckConstraint("quantity >= 0", name="ck_user_card_quantity_non_negative"),
    )

    user_collection_id: Mapped[UUID] = mapped_column(ForeignKey("user_collection.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[UUID] = mapped_column(ForeignKey("card.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(default=0)

    user_collection: Mapped[UserCollection] = relationship(back_populates="cards", lazy="raise", init=False)
    card: Mapped[Card] = relationship(lazy="raise", init=False)
