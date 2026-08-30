from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(description="Token issued by @BotFather")
    private_channel_id: int = Field(description="Numeric id of the private channel, usually negative")
    admin_user_ids: list[int] = Field(default_factory=list, description="Telegram user ids allowed to run admin commands")
    database_url: str = Field(default="sqlite+aiosqlite:///./stylebot.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
