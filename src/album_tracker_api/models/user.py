from sqlalchemy.orm import Mapped, mapped_column

from album_tracker_api.models.base import AlbumTrackerBase


class User(AlbumTrackerBase):
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str] = mapped_column()
    is_admin: Mapped[bool] = mapped_column(default=False)
