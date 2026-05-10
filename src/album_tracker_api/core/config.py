import pprint

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from ..schemas import BaseSchema


class JwtSettings(BaseSchema):
    access_token_expire_minutes: int = 5
    refresh_token_expire_minutes: int = 60 * 24 * 7
    secret_key: str
    algorithm: str


class DbSettings(BaseSchema):
    user: str
    password: str
    host: str
    port: int
    database_name: str
    run_migrations_on_startup: bool = False

    def get_connection_string(self) -> URL:
        return URL.create("postgresql+asyncpg", self.user, self.password, self.host, self.port, self.database_name)


class AlbumTrackerSettings(BaseSettings):
    jwt: JwtSettings
    db: DbSettings

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=[".env", ".env.dev", ".env.prod"],
    )


settings = AlbumTrackerSettings()  # type: ignore
pprint.pprint(settings.model_dump())
