# Album Tracker API

Album Tracker API is a FastAPI backend for tracking collectible card albums across multiple collections, such as a World Cup sticker album. Users can subscribe to a collection, maintain their own album for that collection, and record how many copies they own of each card.

The API is designed to answer album-management questions such as which cards a user is missing and which cards are tradable because the user has more than one copy.

## Core Concepts

- A `Collection` represents a catalog of collectible cards.
- A `Card` belongs to a collection and can be organized into album sections.
- A user-owned `Album` is the user's instance of a collection.
- User/card records track ownership counts, including missing cards and duplicate cards available for trade.

## Stack

- Python `3.14`, managed with `uv` and pinned in `.python-version` and `mise.toml`.
- FastAPI with the app entrypoint at `album_tracker_api.main:app`.
- Async SQLAlchemy with PostgreSQL through `asyncpg`.
- Alembic for database migrations.
- Pydantic settings and schemas with camelCase API aliases.
- Ruff for formatting and linting, and `ty` for type checking.
- Pytest, pytest-asyncio, pytest-cov, and testcontainers for integration tests.

## Project Structure

- `src/album_tracker_api/main.py` creates the FastAPI app, redirects `/` to `/docs`, and includes all routers.
- `src/album_tracker_api/routers/` defines the HTTP API endpoints.
- `src/album_tracker_api/handlers/` contains the business logic used by the routers.
- `src/album_tracker_api/models/` contains async SQLAlchemy models.
- `src/album_tracker_api/schemas/` contains Pydantic request and response schemas. Standard responses use `BaseResponse[T]`; OAuth token responses intentionally stay unwrapped and snake_case.
- `src/album_tracker_api/dependencies/` contains database and authentication dependencies.
- `alembic/` contains database migrations.
- `tests/` contains integration tests that exercise the FastAPI app through real HTTP clients and a real PostgreSQL database started with testcontainers.
- `.github/workflows/ci.yml` runs checks and integration tests in GitHub Actions.

## Setup

Install dependencies with:

```sh
uv sync
```

Create a local `.env` using `.env.placeholder` as the template. Settings use nested environment variable names such as `DB__USER`, `DB__DATABASE_NAME`, and `JWT__SECRET_KEY`.

If using the included Compose database, PostgreSQL is exposed on host port `5434`, while the container still listens on `5432`. For a local app connecting to the Compose database, set `DB__HOST=localhost` and `DB__PORT=5434`. For the API container connecting to the database container, set `DB__HOST=album_tracker_db` and `DB__PORT=5432`.

Start the Compose services with:

```sh
docker compose up --build
```

## Development

Start the development server with:

```sh
mise run start
```

Run verification checks with:

```sh
mise run check
```

This runs formatting, linting, and type checking. It does not run tests.

Focused checks are also available:

```sh
mise run format-check
mise run lint
mise run typecheck
```

Format the code with:

```sh
mise run format
```

Run tests with:

```sh
mise run test
```

The test suite uses pytest with async fixtures and integration tests against `album_tracker_api.main:app`. `tests/conftest.py` starts a session-scoped `PostgresContainer("postgres:alpine")`, so Docker must be available when running tests. The tests still require a `.env` file or equivalent environment variables for settings and JWT values, even though the database connection is overridden by testcontainers.

Every pytest run includes application coverage for `album_tracker_api`, with line and branch coverage enabled. The terminal output shows missing lines, `htmlcov/index.html` provides an interactive HTML report, and `coverage.xml` is generated for CI or other reporting tools.

## API Overview

- `GET /` redirects to the generated FastAPI documentation at `/docs`.
- `/auth` handles registration, login, and refresh tokens.
- `/albums` exposes the album catalog. Read endpoints are public; write endpoints require an admin user.
- `/collections` lets authenticated users subscribe to albums, view their collections, and track card quantities.
- `/users/me` returns the authenticated user's profile.
- `/admin/settings` returns app settings and requires an admin user.
- `/health/` returns a basic health check response.

## Database Migrations

Generate a new Alembic migration with:

```sh
mise run alembic:generate "migration name"
```

Apply all pending migrations with:

```sh
mise run alembic:migrate
```

Migration generation uses Alembic autogenerate, so it requires database connectivity and all mapped models must be imported from `src/album_tracker_api/models/__init__.py`.

The app only runs `alembic upgrade head` during startup when `DB__RUN_MIGRATIONS_ON_STARTUP=true`. Otherwise, run `mise run alembic:migrate` explicitly.

## Continuous Integration

GitHub Actions runs `.github/workflows/ci.yml` on pull requests to `master`, pushes to `master`, and manual workflow dispatches. The workflow copies `.env.ci` to `.env`, installs tools with mise, syncs dependencies with `uv sync --locked --all-groups`, runs `mise run check`, and then runs `mise run test`.
