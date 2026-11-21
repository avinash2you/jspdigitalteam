from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "JSP Digital Intelligence Platform API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Adapter backend configurations
    STORAGE_BACKEND: str = "mock"
    OCR_BACKEND: str = "mock"
    SEARCH_BACKEND: str = "mock"
    AI_BACKEND: str = "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
