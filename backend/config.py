from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it"
    OPENROUTER_VISION_MODEL: str = "google/gemma-4-26b-a4b-it"
    OPENROUTER_PLANNER_MODEL: str = ""
    OPENROUTER_EXTRACTION_MODEL: str = ""
    DATABASE_URL: str
    DIRECT_URL: str = ""
    OPENAI_API_KEY: str = ""
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = ""
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = ""
    FRONTEND_URL: str = "http://localhost:8081"
    JWT_SECRET: str = ""
    CHAT_HISTORY_WINDOW: int = 12
    CHAT_MEMORIES_LIMIT: int = 6
    CHAT_EVENTS_LIMIT: int = 6
    CHAT_RESPONSE_MAX_TOKENS: int = 260
    CHAT_ARTIFACT_MAX_TOKENS: int = 900
    CHAT_PLANNER_MAX_TOKENS: int = 220
    CHAT_EXTRACTION_MAX_TOKENS: int = 700
    CHAT_ENABLE_MEMORY_RERANK: bool = True


settings = Settings()
