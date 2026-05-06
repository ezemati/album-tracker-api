import pprint

from pydantic_settings import BaseSettings, SettingsConfigDict

from ..schemas import BaseSchema


class JwtSettings(BaseSchema):
    access_token_expire_minutes: int = 5
    refresh_token_expire_minutes: int = 60 * 24 * 7
    secret_key: str
    algorithm: str


class DbSettings(BaseSchema):
    connection_string: str
    run_migrations_on_startup: bool = False


class AlbumTrackerSettings(BaseSettings):
    jwt: JwtSettings
    db: DbSettings

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=[".env", ".env.prod"],
    )


settings = AlbumTrackerSettings()  # type: ignore
pprint.pprint(settings.model_dump())
