"""Core application configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields from .env
    )

    # API Configuration
    API_TITLE: str = "Azure AI POC API"
    API_VERSION: str = Field(default="latest", alias="IMAGE_TAG")
    PORT: int = Field(default=3001, alias="PORT")

    # Security Configuration
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS Configuration
    CORS_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Rate Limiting Configuration
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=30, alias="RATE_LIMIT_MAX_REQUESTS")
    RATE_LIMIT_TTL: int = Field(default=60000, alias="RATE_LIMIT_TTL")  # milliseconds

    # Azure OpenAI Configuration
    AZURE_OPENAI_LLM_ENDPOINT: str = Field(alias="AZURE_OPENAI_LLM_ENDPOINT")
    AZURE_OPENAI_EMBEDDING_ENDPOINT: str = Field(alias="AZURE_OPENAI_EMBEDDING_ENDPOINT")
    AZURE_OPENAI_API_KEY: str | None = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_LLM_DEPLOYMENT_NAME: str = Field(alias="AZURE_OPENAI_LLM_DEPLOYMENT_NAME")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME: str = Field(
        alias="AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"
    )

    # Cosmos DB Configuration
    COSMOS_DB_ENDPOINT: str = Field(alias="COSMOS_DB_ENDPOINT")
    COSMOS_DB_KEY: str | None = Field(default=None, alias="COSMOS_DB_KEY")
    COSMOS_DB_DATABASE_NAME: str = Field(default="azure-ai-poc", alias="COSMOS_DB_DATABASE_NAME")
    COSMOS_DB_CONTAINER_NAME: str = Field(default="documents", alias="COSMOS_DB_CONTAINER_NAME")

    # Azure AI Search Configuration
    AZURE_SEARCH_ENDPOINT: str | None = Field(default=None, alias="AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_API_KEY: str | None = Field(default=None, alias="AZURE_SEARCH_API_KEY")
    AZURE_SEARCH_INDEX_NAME: str = Field(default="documents-index", alias="AZURE_SEARCH_INDEX_NAME")

    # Keycloak Configuration
    KEYCLOAK_URL: str | None = Field(default=None, alias="KEYCLOAK_URL")
    KEYCLOAK_REALM: str | None = Field(default=None, alias="KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID: str | None = Field(default=None, alias="KEYCLOAK_CLIENT_ID")

    # JWT Configuration (Keycloak)
    JWT_ISSUER: str | None = Field(default=None, alias="JWT_ISSUER")
    JWT_AUDIENCE: str | None = Field(default=None, alias="JWT_AUDIENCE")
    JWT_JWKS_URI: str | None = Field(default=None, alias="JWT_JWKS_URI")

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")

    # Health Check Configuration
    HEALTH_CHECK_PATH: str = "/health"

    # Metrics Configuration
    METRICS_PATH: str = "/metrics"

    # Environment
    ENVIRONMENT: str = Field(default="development", alias="NODE_ENV")


# Global settings instance
settings = Settings()
