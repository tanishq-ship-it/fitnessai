from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "meta-llama/llama-4-maverick"
    DATABASE_URL: str
    FRONTEND_URL: str = "http://localhost:8081"


settings = Settings()
