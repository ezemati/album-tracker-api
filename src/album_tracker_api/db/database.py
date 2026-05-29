from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ..core import settings

engine = create_async_engine(
    settings.db.get_connection_string(),
    echo=True,
    connect_args={
        # "check_same_thread": True,
        # "check_same_thread": False,
    },
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    # autoflush=True,
)
