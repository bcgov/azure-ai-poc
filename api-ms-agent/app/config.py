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
    azure_openai_api_version: str = "2024-10-21"

    # Azure OpenAI Model Deployments - Source of truth for available models
    # Format: {model_id: {deployment, display_name, api_version (optional)}}
    azure_openai_models: dict = {
        "gpt-4o-mini": {
            "deployment": "gpt-4o-mini",
            "display_name": "GPT-4o mini",
            "description": "Fast, cost-effective model for most tasks",
            "is_default": True,
        },
        "gpt-41-nano": {
            "deployment": "gpt-4.1-nano",
            "display_name": "GPT-4.1 Nano",
            "description": "Ultra-fast model for simple tasks",
        },
    }

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
    devui_auto_open: bool = False
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

    # Azure Speech Services settings (for TTS)
    azure_speech_key: str = ""
    azure_speech_region: str = "canadacentral"
    azure_speech_endpoint: str = ""
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

    def get_model_config(self, model_id: str) -> dict:
        """Get full configuration for a model ID."""
        return self.azure_openai_models.get(model_id, {})

    def get_deployment(self, model_id: str) -> str:
        """Get deployment name for a model ID."""
        config = self.get_model_config(model_id)
        if config:
            return config.get("deployment", model_id)
        # Fallback to default model's deployment
        return self.get_default_model()["deployment"]

    def get_default_model(self) -> dict:
        """Get the default model configuration."""
        for model_id, config in self.azure_openai_models.items():
            if config.get("is_default"):
                return {"id": model_id, **config}
        # Fallback to first model
        first_id = next(iter(self.azure_openai_models.keys()), "gpt-4o-mini")
        first_config = self.azure_openai_models.get(first_id, {})
        return {"id": first_id, **first_config}

    def get_default_model_id(self) -> str:
        """Get the default model ID."""
        return self.get_default_model()["id"]

    def get_available_models(self) -> list[dict]:
        """Get list of available models for API response."""
        return [
            {
                "id": model_id,
                "deployment": config["deployment"],
                "display_name": config["display_name"],
                "description": config.get("description", ""),
                "is_default": config.get("is_default", False),
            }
            for model_id, config in self.azure_openai_models.items()
        ]


settings = Settings()
