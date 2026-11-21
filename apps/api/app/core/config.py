from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "JSP Digital Intelligence Platform API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database configuration (PostgreSQL 16 + pgvector)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jsp_intel"

    # Clerk Authentication
    CLERK_SECRET_KEY: str = "sk_test_placeholder_secret_key_32bytes_long"
    CLERK_PUBLISHABLE_KEY: str = "pk_test_placeholder_publishable_key"
    CLERK_JWT_ISSUER: str = "https://example.clerk.accounts.dev"

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
