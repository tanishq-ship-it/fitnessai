from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it"
    DATABASE_URL: str
    DIRECT_URL: str = ""
    OPENAI_API_KEY: str = ""
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = ""
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = ""
    FRONTEND_URL: str = "http://localhost:8081"
    JWT_SECRET: str = ""


settings = Settings()
