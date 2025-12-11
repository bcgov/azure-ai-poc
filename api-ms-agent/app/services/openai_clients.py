"""
Azure OpenAI Client Factory.

Centralized client management for Azure OpenAI services. Provides:
- Singleton clients for each model deployment (gpt-4o-mini, gpt-4.1-nano, embeddings)
- Proper async lifecycle management with context managers
- Managed identity and API key authentication support
- Consistent configuration across all services

Usage:
    # Get clients directly
    from app.services.openai_clients import (
        get_gpt4o_mini_client,
        get_gpt41_nano_client,
        get_embedding_client,
    )

    client = await get_gpt4o_mini_client()
    response = await client.chat.completions.create(...)

    # Or use context manager for guaranteed cleanup
    async with gpt4o_mini_client() as client:
        response = await client.chat.completions.create(...)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class ModelType(Enum):
    """Available Azure OpenAI model deployments.

    NOTE: Chat models are dynamically loaded from config.py (azure_openai_models).
    Only EMBEDDING is hardcoded here as it's a special case.
    """

    EMBEDDING = "text-embedding-3-large"


@dataclass(frozen=True)
class ClientConfig:
    """Configuration for an Azure OpenAI client."""

    endpoint: str
    deployment: str
    api_version: str
    api_key: str | None = None
    use_managed_identity: bool = False


class AzureOpenAIClientFactory:
    """
    Factory for creating and managing Azure OpenAI clients.

    Implements singleton pattern per model type to avoid recreating clients.
    Supports both API key and managed identity authentication.

    Chat model clients are created dynamically based on config.py settings.
    Thread-safe for async operations.
    """

    # Clients keyed by deployment name (dynamic for chat models)
    _chat_clients: dict[str, AsyncAzureOpenAI] = {}
    _chat_credentials: dict[str, DefaultAzureCredential] = {}
    _chat_initialized: set[str] = set()

    # Embedding client (singleton)
    _embedding_client: AsyncAzureOpenAI | None = None
    _embedding_credential: DefaultAzureCredential | None = None
    _embedding_initialized: bool = False

    @classmethod
    def _get_embedding_config(cls) -> ClientConfig:
        """Get configuration for embedding model."""
        return ClientConfig(
            endpoint=settings.azure_openai_embedding_endpoint or settings.azure_openai_endpoint,
            deployment=settings.azure_openai_embedding_deployment,
            api_version=settings.azure_openai_api_version,
            api_key=settings.azure_openai_api_key,
            use_managed_identity=settings.use_managed_identity,
        )

    @classmethod
    def _get_chat_config(cls, model_id: str) -> ClientConfig:
        """Get configuration for a chat model from config.py."""
        deployment = settings.get_deployment(model_id)
        return ClientConfig(
            endpoint=settings.azure_openai_endpoint,
            deployment=deployment,
            api_version=settings.azure_openai_api_version,
            api_key=settings.azure_openai_api_key,
            use_managed_identity=settings.use_managed_identity,
        )

    @classmethod
    async def get_embedding_client(cls) -> AsyncAzureOpenAI:
        """Get or create the embedding model client."""
        if cls._embedding_client is not None and cls._embedding_initialized:
            return cls._embedding_client

        config = cls._get_embedding_config()

        logger.debug(
            "creating_embedding_client",
            endpoint=config.endpoint,
            deployment=config.deployment,
            use_managed_identity=config.use_managed_identity,
        )

        if config.use_managed_identity:
            cls._embedding_credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                cls._embedding_credential, "https://cognitiveservices.azure.com/.default"
            )
            cls._embedding_client = AsyncAzureOpenAI(
                azure_endpoint=config.endpoint,
                azure_ad_token_provider=token_provider,
                api_version=config.api_version,
            )
            logger.info("embedding_client_created", auth="managed_identity")
        else:
            cls._embedding_client = AsyncAzureOpenAI(
                azure_endpoint=config.endpoint,
                api_key=config.api_key,
                api_version=config.api_version,
            )
            logger.info("embedding_client_created", auth="api_key")

        cls._embedding_initialized = True
        return cls._embedding_client

    @classmethod
    async def get_chat_client(cls, model_id: str | None = None) -> AsyncAzureOpenAI:
        """
        Get or create an Azure OpenAI client for a chat model.

        Uses lazy initialization - client is created on first access.
        Subsequent calls return the cached instance.

        Args:
            model_id: The model identifier (e.g., 'gpt-4o-mini'). None uses default.

        Returns:
            AsyncAzureOpenAI client configured for the model
        """
        # Resolve model_id to actual ID
        if model_id is None:
            model_id = settings.get_default_model_id()

        # Get deployment name for this model
        deployment = settings.get_deployment(model_id)

        # Check cache by deployment name
        if deployment in cls._chat_clients and deployment in cls._chat_initialized:
            return cls._chat_clients[deployment]

        config = cls._get_chat_config(model_id)

        logger.debug(
            "creating_chat_client",
            model_id=model_id,
            deployment=config.deployment,
            use_managed_identity=config.use_managed_identity,
        )

        if config.use_managed_identity:
            credential = DefaultAzureCredential()
            cls._chat_credentials[deployment] = credential
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            client = AsyncAzureOpenAI(
                azure_endpoint=config.endpoint,
                azure_ad_token_provider=token_provider,
                api_version=config.api_version,
            )
            logger.info(
                "chat_client_created",
                model_id=model_id,
                deployment=deployment,
                auth="managed_identity",
            )
        else:
            client = AsyncAzureOpenAI(
                azure_endpoint=config.endpoint,
                api_key=config.api_key,
                api_version=config.api_version,
            )
            logger.info(
                "chat_client_created",
                model_id=model_id,
                deployment=deployment,
                auth="api_key",
            )

        cls._chat_clients[deployment] = client
        cls._chat_initialized.add(deployment)
        return client

    @classmethod
    def get_deployment_name(cls, model_id: str | None = None) -> str:
        """Get the deployment name for a model ID."""
        if model_id is None:
            model_id = settings.get_default_model_id()
        return settings.get_deployment(model_id)

    @classmethod
    async def close_chat_client(cls, deployment: str) -> None:
        """Close a specific chat client and its credential."""
        if deployment in cls._chat_clients:
            client = cls._chat_clients.pop(deployment)
            await client.close()
            logger.debug("chat_client_closed", deployment=deployment)

        if deployment in cls._chat_credentials:
            credential = cls._chat_credentials.pop(deployment)
            await credential.close()

        cls._chat_initialized.discard(deployment)

    @classmethod
    async def close_embedding_client(cls) -> None:
        """Close the embedding client."""
        if cls._embedding_client is not None:
            await cls._embedding_client.close()
            cls._embedding_client = None
            logger.debug("embedding_client_closed")

        if cls._embedding_credential is not None:
            await cls._embedding_credential.close()
            cls._embedding_credential = None

        cls._embedding_initialized = False

    @classmethod
    async def close_all(cls) -> None:
        """Close all clients and credentials. Call on application shutdown."""
        # Close all chat clients
        for deployment in list(cls._chat_clients.keys()):
            await cls.close_chat_client(deployment)

        # Close embedding client
        await cls.close_embedding_client()

        logger.info("all_openai_clients_closed")


# ==================== Convenience Functions ====================


async def get_gpt4o_mini_client() -> AsyncAzureOpenAI:
    """Get the GPT-4o mini client (default chat model)."""
    return await AzureOpenAIClientFactory.get_chat_client("gpt-4o-mini")


async def get_gpt41_nano_client() -> AsyncAzureOpenAI:
    """Get the GPT-4.1 nano client (fast/cheap model)."""
    return await AzureOpenAIClientFactory.get_chat_client("gpt-41-nano")


async def get_embedding_client() -> AsyncAzureOpenAI:
    """Get the embedding model client."""
    return await AzureOpenAIClientFactory.get_embedding_client()


async def get_client_for_model(model: str | None) -> AsyncAzureOpenAI:
    """
    Get client for a model identifier string.

    Dynamically creates/retrieves client based on config.py settings.

    Args:
        model: Model identifier from config.py (e.g., 'gpt-4o-mini', 'gpt-41-nano')
               None uses the default model.

    Returns:
        AsyncAzureOpenAI client for the specified model
    """
    return await AzureOpenAIClientFactory.get_chat_client(model)


def get_deployment_for_model(model: str | None) -> str:
    """
    Get deployment name for a model identifier string.

    Dynamically looks up deployment from config.py settings.

    Args:
        model: Model identifier from config.py (e.g., 'gpt-4o-mini', 'gpt-41-nano')
               None uses the default model.

    Returns:
        Azure OpenAI deployment name
    """
    return AzureOpenAIClientFactory.get_deployment_name(model)


# ==================== Context Managers ====================


@asynccontextmanager
async def chat_client(model: str | None = None) -> AsyncIterator[AsyncAzureOpenAI]:
    """
    Context manager for any chat model client.

    The client is cached and reused, but this ensures proper
    error handling context.

    Usage:
        async with chat_client("gpt-4o-mini") as client:
            response = await client.chat.completions.create(...)
    """
    client = await get_client_for_model(model)
    try:
        yield client
    except Exception:
        # Client remains cached for reuse, just re-raise
        raise


@asynccontextmanager
async def gpt4o_mini_client() -> AsyncIterator[AsyncAzureOpenAI]:
    """
    Context manager for GPT-4o mini client.

    Usage:
        async with gpt4o_mini_client() as client:
            response = await client.chat.completions.create(...)
    """
    async with chat_client("gpt-4o-mini") as client:
        yield client


@asynccontextmanager
async def gpt41_nano_client() -> AsyncIterator[AsyncAzureOpenAI]:
    """
    Context manager for GPT-4.1 nano client.

    Usage:
        async with gpt41_nano_client() as client:
            response = await client.chat.completions.create(...)
    """
    async with chat_client("gpt-41-nano") as client:
        yield client


@asynccontextmanager
async def embedding_client() -> AsyncIterator[AsyncAzureOpenAI]:
    """
    Context manager for embedding model client.

    Usage:
        async with embedding_client() as client:
            response = await client.embeddings.create(...)
    """
    client = await get_embedding_client()
    try:
        yield client
    except Exception:
        raise


# ==================== Cleanup Hook ====================


async def shutdown_clients() -> None:
    """
    Shutdown hook to close all clients.

    Call this in FastAPI's lifespan shutdown or atexit handler.
    """
    await AzureOpenAIClientFactory.close_all()
