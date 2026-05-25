# Agent Notes

## Commands
- Use `uv sync` to install/sync dependencies; Python is pinned to `3.14` in `.python-version` and `mise.toml`.
- Start the dev server with `mise run start` (`uv run fastapi dev --entrypoint album_tracker_api.main:app`). Do not rely on guessing the FastAPI module path.
- Run focused checks with `mise run format-check`, `mise run lint`, and `mise run typecheck`; `mise run check` runs those three. There is no test task yet, and `tests/` only contains `__init__.py`.
- Format with `mise run format` (`ruff format .`); lint uses `ruff check .`; typing uses `ty check`.
- Generate migrations with `mise run alembic:generate "migration name"`; it uses Alembic `--autogenerate` and needs DB connectivity. Apply migrations with `mise run alembic:migrate`.

## App Wiring
- The FastAPI app object is `album_tracker_api.main:app`; `main.py` includes routers from `src/album_tracker_api/routers/__init__.py`.
- Routers stay thin and delegate behavior to handler classes injected with `Depends()`; database sessions come from `SessionDep` in `dependencies/db.py`.
- Settings load from `.env`, `.env.dev`, and `.env.prod` with nested names like `DB__USER` and `JWT__SECRET_KEY`; `.env.placeholder` documents required keys.

## Database And Migrations
- SQLAlchemy is async (`create_async_engine`) and currently logs SQL with `echo=True`.
- `AlbumTrackerBase` assigns UUIDv7 IDs and derives table names from class names; add new mapped models to `src/album_tracker_api/models/__init__.py` so Alembic autogenerate sees them.
- Alembic reads the database URL from `settings.db.get_connection_string()` in `alembic/env.py`; CLI migration commands therefore require the same env vars as app startup.
- `compose.yml` exposes Postgres on host port `5434` and reads the same `.env` file; account for the host/port difference when running the app locally against the Compose DB.

## API Conventions
- Pydantic schemas inherit from `BaseSchema`, which uses camelCase aliases, validates by field name and alias, and enables `from_attributes`.
- Standard response wrappers use `BaseResponse[T]` from `schemas/base.py`.
