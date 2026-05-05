from contextlib import asynccontextmanager

import uvicorn
from alembic import command, config
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from album_tracker_api.core.config import settings
from album_tracker_api.core.project_root_path import get_project_root_path

from .routers import admin, auth, health

root_router = APIRouter()


@root_router.get("/")
def get_root():
    return RedirectResponse(url="/docs")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.db.run_migrations_on_startup:
        alembic_cfg = config.Config(get_project_root_path() / "alembic.ini")
        command.upgrade(alembic_cfg, "head")
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(root_router)


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
