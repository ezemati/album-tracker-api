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

## Setup

Install dependencies with:

```sh
uv sync
```

Create a local `.env` using `.env.placeholder` as the template. Settings use nested environment variable names such as `DB__USER`, `DB__DATABASE_NAME`, and `JWT__SECRET_KEY`.

If using the included Compose database, PostgreSQL is exposed on host port `5434`, while the container still listens on `5432`.

## Development

Start the development server with:

```sh
mise run start
```

Run verification checks with:

```sh
mise run check
```

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

There is no test task yet; `tests/` currently only contains package scaffolding.

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
