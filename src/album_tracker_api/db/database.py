from sqlalchemy.ext.asyncio import create_async_engine

from album_tracker_api.core.config import settings

engine = create_async_engine(
    settings.db.connection_string,
    echo=True,
    connect_args={
        # "check_same_thread": True,
        # "check_same_thread": False,
    },
)
