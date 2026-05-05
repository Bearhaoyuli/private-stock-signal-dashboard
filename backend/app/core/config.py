from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_service_role_key: str | None = Field(
        default=None,
        alias="SUPABASE_SERVICE_ROLE_KEY",
    )
    allowed_user_email: str | None = Field(default=None, alias="ALLOWED_USER_EMAIL")

    enable_reddit_live: bool = Field(default=False, alias="ENABLE_REDDIT_LIVE")
    enable_translation: bool = Field(default=True, alias="ENABLE_TRANSLATION")
    enable_llm_summary: bool = Field(default=False, alias="ENABLE_LLM_SUMMARY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    reddit_client_id: str | None = Field(default=None, alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = Field(
        default=None,
        alias="REDDIT_CLIENT_SECRET",
    )
    reddit_username: str | None = Field(default=None, alias="REDDIT_USERNAME")
    reddit_password: str | None = Field(default=None, alias="REDDIT_PASSWORD")
    reddit_user_agent: str | None = Field(default=None, alias="REDDIT_USER_AGENT")

    subreddits_raw: str = Field(
        default="stocks,investing,StockMarket,wallstreetbets,pennystocks,ValueInvesting,美股,港美股",
        alias="SUBREDDITS",
    )
    snapshot_path: str = "backend/app/data/runtime/snapshot.json"
    cors_origins: str = "*"

    @property
    def subreddits(self) -> list[str]:
        return [item.strip() for item in self.subreddits_raw.split(",") if item.strip()]

    @property
    def has_reddit_credentials(self) -> bool:
        required = (
            self.reddit_client_id,
            self.reddit_client_secret,
            self.reddit_username,
            self.reddit_password,
            self.reddit_user_agent,
        )
        return all(required)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

