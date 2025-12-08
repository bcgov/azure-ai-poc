"""Application settings using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "API MS Agent"
    debug: bool = False
    environment: str = "local"  # local, development, production

    # Azure OpenAI settings
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""  # Optional if using managed identity
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-10-21"

    # Azure OpenAI Embedding settings
    azure_openai_embedding_endpoint: str = ""
    azure_openai_embedding_deployment: str = "text-embedding-3-large"

    # LLM Configuration - Low temperature for high confidence responses
    llm_temperature: float = 0.0  # Low temperature for consistent, high-confidence responses
    llm_max_output_tokens: int = 5000  # Cap responses to control cost/token usage

    # Dev UI (Agent Framework DevUI) settings
    devui_enabled: bool = True
    devui_host: str = "localhost"
    devui_port: int = 8000
    devui_auto_open: bool = True
    devui_mode: str = "developer"  # developer | user

    # Cosmos DB settings - for chat history, metadata, and workflow persistence
    cosmos_db_endpoint: str = ""
    cosmos_db_key: str = ""  # Optional if using managed identity
    cosmos_db_database_name: str = "azure-ai-poc"

    # Azure AI Search settings - for vector embeddings storage
    azure_search_endpoint: str = ""
    azure_search_key: str = ""  # Optional if using managed identity
    azure_search_index_name: str = "documents-index"

    # Azure Document Intelligence settings
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""  # Optional if using managed identity

    # MCP base URLs for BC APIs (override defaults if needed)
    geocoder_base_url: str = ""
    orgbook_base_url: str = ""
    parks_base_url: str = ""

    # Use managed identity for non-local environments
    # Local uses API keys, cloud environments use managed identity
    @property
    def use_managed_identity(self) -> bool:
        """Use managed identity for Azure services in non-local environments."""
        return self.environment != "local"


settings = Settings()
