from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import Connection

from alembic import command, config

from .core import get_project_root_path, settings
from .db import engine
from .routers import admin_router, albums_router, auth_router, collections_router, health_router, users_router

root_router = APIRouter()


@root_router.get("/")
def get_root():
    return RedirectResponse(url="/docs")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.db.run_migrations_on_startup:
        alembic_cfg = config.Config(get_project_root_path() / "alembic.ini")

        def run_upgrade(connection: Connection):
            alembic_cfg.attributes["connection"] = connection
            command.upgrade(alembic_cfg, "head")

        async with engine.begin() as connection:
            await connection.run_sync(run_upgrade)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(root_router)
app.include_router(admin_router)
app.include_router(albums_router)
app.include_router(auth_router)
app.include_router(collections_router)
app.include_router(health_router)
app.include_router(users_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
