"""
Chat Agent Service using Microsoft Agent Framework.

This service provides a simple chat agent using Azure OpenAI.
All responses MUST include source attribution for traceability.
"""

import json
from dataclasses import dataclass, field

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SourceInfo:
    """Information about a source used in the response.

    MANDATORY: All sources must include detailed citation information.
    For API sources, include endpoint, params, and full URL.
    For web sources, include full URL with query parameters.
    For LLM knowledge, include topic area and confidence reasoning.
    """

    source_type: str  # 'llm_knowledge', 'document', 'web', 'api', 'unknown'
    description: str  # Detailed description including topic/query details
    confidence: str = "high"  # 'high', 'medium', 'low'
    url: str | None = None  # Full URL with query parameters when applicable
    api_endpoint: str | None = None  # API endpoint path for API sources
    api_params: dict | None = None  # Query parameters for API sources


@dataclass
class ChatResult:
    """Result from a chat interaction including sources."""

    response: str
    sources: list[SourceInfo] = field(default_factory=list)
    has_sufficient_info: bool = True


class ChatAgentService:
    """Simple chat agent service using Azure OpenAI."""

    # noqa: E501 - Line length exceptions for LLM prompt readability
    SYSTEM_PROMPT = """You are a helpful AI assistant that provides accurate, \
well-sourced responses.

CRITICAL REQUIREMENTS:
1. You MUST ALWAYS provide source attribution for your information.
2. If you cannot provide verifiable sources or don't have enough information, \
you MUST say: "I don't have enough information to answer this question accurately."
3. Be clear about what you know vs. what you're uncertain about.

SOURCE TYPE RULES (follow strictly):
- Use "llm_knowledge" for general knowledge from your training data \
(this is the DEFAULT for most questions)
- Use "document" ONLY when explicitly referencing an uploaded document
- Use "web" ONLY when you have an actual URL to cite
- Use "api" ONLY when data comes from a specific API call
- Use "unknown" if you cannot determine the source

DETAILED CITATION REQUIREMENTS (MANDATORY - NO EXCEPTIONS):
- For "llm_knowledge": Include the topic area and reasoning for confidence level
- For "document": Include document name, section/page if known
- For "web": Include the full URL with any query parameters
- For "api": Include the full API URL, endpoint path, and query parameters used

For general knowledge questions, ALWAYS use:
- source_type: "llm_knowledge"
- description: "General knowledge about [TOPIC]. [Explain confidence reasoning]"
- confidence: based on how certain you are (high/medium/low)

You MUST respond with ONLY valid JSON using this exact format:
{
    "response": "Your detailed response here",
    "sources": [
        {
            "source_type": "llm_knowledge",
            "description": "General knowledge about [topic]. [Confidence reasoning].",
            "confidence": "high|medium|low",
            "url": null
        }
    ],
    "has_sufficient_info": true
}

If you don't have sufficient information, respond with:
{
    "response": "I don't have enough information to answer this accurately.",
    "sources": [],
    "has_sufficient_info": false
}"""

    def __init__(self) -> None:
        """Initialize the chat agent service."""
        self._client: AsyncAzureOpenAI | None = None
        self._credential: DefaultAzureCredential | None = None
        logger.info("ChatAgentService initialized")

    async def _get_client(self) -> AsyncAzureOpenAI:
        """Get or create the Azure OpenAI client."""
        if self._client is None:
            logger.debug(
                "creating_openai_client",
                endpoint=settings.azure_openai_endpoint,
                deployment=settings.azure_openai_deployment,
                api_version=settings.azure_openai_api_version,
                use_managed_identity=settings.use_managed_identity,
            )

            if settings.use_managed_identity:
                # Use Azure CLI / Managed Identity
                self._credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(
                    self._credential, "https://cognitiveservices.azure.com/.default"
                )
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=settings.azure_openai_api_version,
                )
                logger.info(
                    "Using managed identity for Azure OpenAI",
                    endpoint=settings.azure_openai_endpoint,
                )
            else:
                # Use API key
                api_key = settings.azure_openai_api_key
                logger.debug(
                    "using_api_key_auth",
                    key_length=len(api_key) if api_key else 0,
                    key_preview=f"{api_key[:4]}...{api_key[-4:]}"
                    if api_key and len(api_key) > 8
                    else "***",
                )
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    api_key=api_key,
                    api_version=settings.azure_openai_api_version,
                )
                logger.info(
                    "Using API key for Azure OpenAI",
                    endpoint=settings.azure_openai_endpoint,
                )
        return self._client

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
    ) -> ChatResult:
        """
        Process a chat message and return a response with source attribution.

        Args:
            message: The user's message
            history: Optional conversation history
            session_id: Optional session identifier for logging

        Returns:
            ChatResult containing the response and source information
        """
        client = await self._get_client()

        # Build messages list
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # Add history if provided
        if history:
            messages.extend(history)

        # Add the current message
        messages.append({"role": "user", "content": message})

        logger.info(
            "chat_request",
            session_id=session_id,
            message_length=len(message),
            history_length=len(history) if history else 0,
        )

        try:
            response = await client.chat.completions.create(
                model=settings.azure_openai_deployment,
                messages=messages,
                temperature=settings.llm_temperature,  # Low temperature for high confidence
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            raw_content = response.choices[0].message.content or "{}"

            try:
                result_data = json.loads(raw_content)
            except json.JSONDecodeError:
                # If JSON parsing fails, wrap the response
                result_data = {
                    "response": raw_content,
                    "sources": [
                        {
                            "source_type": "llm_knowledge",
                            "description": "Response from AI model (unstructured)",
                            "confidence": "medium",
                            "url": None,
                        }
                    ],
                    "has_sufficient_info": True,
                }

            # Parse sources
            sources = []
            for src in result_data.get("sources", []):
                sources.append(
                    SourceInfo(
                        source_type=src.get("source_type", "llm_knowledge"),
                        description=src.get("description", "AI model knowledge"),
                        confidence=src.get("confidence", "medium"),
                        url=src.get("url"),
                    )
                )

            # If no sources provided, add default source attribution
            if not sources:
                sources.append(
                    SourceInfo(
                        source_type="llm_knowledge",
                        description="Based on AI model's training knowledge",
                        confidence="medium",
                    )
                )

            chat_result = ChatResult(
                response=result_data.get("response", raw_content),
                sources=sources,
                has_sufficient_info=result_data.get("has_sufficient_info", True),
            )

            logger.info(
                "chat_response",
                session_id=session_id,
                response_length=len(chat_result.response),
                source_count=len(chat_result.sources),
                has_sufficient_info=chat_result.has_sufficient_info,
                tokens_used=response.usage.total_tokens if response.usage else 0,
            )

            return chat_result

        except Exception as e:
            logger.error("chat_error", error=str(e), session_id=session_id)
            raise

    async def close(self) -> None:
        """Clean up resources."""
        if self._credential:
            await self._credential.close()
        if self._client:
            await self._client.close()
        logger.info("ChatAgentService closed")


# Global service instance
_chat_agent_service: ChatAgentService | None = None


def get_chat_agent_service() -> ChatAgentService:
    """Get or create the global chat agent service."""
    global _chat_agent_service
    if _chat_agent_service is None:
        _chat_agent_service = ChatAgentService()
    return _chat_agent_service
