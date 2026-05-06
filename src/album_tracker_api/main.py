from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from alembic import command, config

from .core import get_project_root_path, settings
from .routers import admin_router, auth_router, health_router, users_router

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
app.include_router(root_router)
app.include_router(admin_router)
app.include_router(auth_router)
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
