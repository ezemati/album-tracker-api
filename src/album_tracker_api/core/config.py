from pydantic_settings import BaseSettings, SettingsConfigDict


class AlbumTrackerSettings(BaseSettings):
    db_connection_url: str

    model_config = SettingsConfigDict(
        env_file=[".env", ".env.prod"],
    )


settings = AlbumTrackerSettings()  # type: ignore
