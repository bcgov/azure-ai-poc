"""
Source and Citation Utilities.

Common functions for handling source citations across the application.
Provides consistent sorting, formatting, and validation of sources.
"""

from dataclasses import dataclass
from typing import Any

# Confidence level ordering (higher = better)
CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}


@dataclass
class SourceInfo:
    """
    Information about a source used in a response.

    MANDATORY: All sources must include detailed citation information.
    For API sources, include endpoint, params, and full URL.
    For web sources, include full URL with query parameters.
    For LLM knowledge, include topic area and confidence reasoning.
    """

    source_type: str  # 'llm_knowledge', 'document', 'web', 'api', 'unknown'
    description: str  # Detailed description including topic/query details
    confidence: str = "medium"  # 'high', 'medium', 'low'
    url: str | None = None  # Full URL with query parameters when applicable
    api_endpoint: str | None = None  # API endpoint path for API sources
    api_params: dict | None = None  # Query parameters for API sources

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with all available details."""
        result = {
            "source_type": self.source_type,
            "description": self.description,
            "confidence": self.confidence,
        }
        if self.url:
            result["url"] = self.url
        if self.api_endpoint:
            result["api_endpoint"] = self.api_endpoint
        if self.api_params:
            result["api_params"] = self.api_params
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceInfo":
        """Create SourceInfo from dictionary."""
        return cls(
            source_type=data.get("source_type", "unknown"),
            description=data.get("description", ""),
            confidence=data.get("confidence", "medium"),
            url=data.get("url"),
            api_endpoint=data.get("api_endpoint"),
            api_params=data.get("api_params"),
        )


def get_confidence_value(confidence: str) -> int:
    """
    Get numeric value for confidence level for sorting.
    Higher values = higher confidence.

    Args:
        confidence: Confidence level string ('high', 'medium', 'low')

    Returns:
        Numeric value for sorting (3=high, 2=medium, 1=low, 0=unknown)
    """
    return CONFIDENCE_ORDER.get(confidence.lower(), 0)


def sort_sources_by_confidence(
    sources: list[SourceInfo | dict[str, Any]],
) -> list[SourceInfo | dict[str, Any]]:
    """
    Sort sources by confidence level (highest first).

    Args:
        sources: List of SourceInfo objects or dictionaries

    Returns:
        Sorted list with high confidence first, then medium, then low
    """
    if not sources:
        return sources

    def get_confidence(source: SourceInfo | dict[str, Any]) -> int:
        if isinstance(source, SourceInfo):
            return get_confidence_value(source.confidence)
        elif isinstance(source, dict):
            return get_confidence_value(source.get("confidence", "medium"))
        return 0

    return sorted(sources, key=get_confidence, reverse=True)


def sort_source_dicts_by_confidence(
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Sort source dictionaries by confidence level (highest first).

    Args:
        sources: List of source dictionaries

    Returns:
        Sorted list with high confidence first
    """
    if not sources:
        return sources

    return sorted(
        sources,
        key=lambda s: get_confidence_value(s.get("confidence", "medium")),
        reverse=True,
    )


def sources_to_dicts(sources: list[SourceInfo]) -> list[dict[str, Any]]:
    """
    Convert list of SourceInfo to list of dictionaries.
    Also sorts by confidence (highest first).

    Args:
        sources: List of SourceInfo objects

    Returns:
        List of dictionaries sorted by confidence
    """
    dicts = [s.to_dict() for s in sources]
    return sort_source_dicts_by_confidence(dicts)


def dicts_to_sources(dicts: list[dict[str, Any]]) -> list[SourceInfo]:
    """
    Convert list of dictionaries to list of SourceInfo.
    Also sorts by confidence (highest first).

    Args:
        dicts: List of source dictionaries

    Returns:
        List of SourceInfo objects sorted by confidence
    """
    sources = [SourceInfo.from_dict(d) for d in dicts]
    return sort_sources_by_confidence(sources)


def deduplicate_sources(
    sources: list[SourceInfo | dict[str, Any]],
) -> list[SourceInfo | dict[str, Any]]:
    """
    Remove duplicate sources based on description and URL.

    Args:
        sources: List of sources (SourceInfo or dicts)

    Returns:
        Deduplicated list sorted by confidence
    """
    seen = set()
    unique = []

    for source in sources:
        if isinstance(source, SourceInfo):
            key = (source.description, source.url)
        else:
            key = (source.get("description", ""), source.get("url"))

        if key not in seen:
            seen.add(key)
            unique.append(source)

    return sort_sources_by_confidence(unique)


def create_llm_knowledge_source(
    description: str,
    confidence: str = "medium",
) -> SourceInfo:
    """
    Create an LLM knowledge source.

    Args:
        description: Description of the knowledge
        confidence: Confidence level ('high', 'medium', 'low')

    Returns:
        SourceInfo configured for LLM knowledge
    """
    return SourceInfo(
        source_type="llm_knowledge",
        description=description,
        confidence=confidence,
        url=None,
    )


def create_web_source(
    title: str,
    url: str,
    confidence: str = "high",
) -> SourceInfo:
    """
    Create a web source.

    Args:
        title: Title/description of the web page
        url: Full URL
        confidence: Confidence level

    Returns:
        SourceInfo configured for web source
    """
    return SourceInfo(
        source_type="web",
        description=f"Web search: {title}",
        confidence=confidence,
        url=url,
    )


def create_api_source(
    description: str,
    url: str,
    endpoint: str | None = None,
    params: dict | None = None,
    confidence: str = "high",
) -> SourceInfo:
    """
    Create an API source with full details.

    Args:
        description: Description of the API call
        url: Full URL with query parameters
        endpoint: API endpoint path
        params: Query parameters
        confidence: Confidence level

    Returns:
        SourceInfo configured for API source
    """
    return SourceInfo(
        source_type="api",
        description=description,
        confidence=confidence,
        url=url,
        api_endpoint=endpoint,
        api_params=params,
    )


def create_document_source(
    description: str,
    confidence: str = "high",
    url: str | None = None,
) -> SourceInfo:
    """
    Create a document source.

    Args:
        description: Description of the document section
        confidence: Confidence level
        url: Optional URL/link to document

    Returns:
        SourceInfo configured for document source
    """
    return SourceInfo(
        source_type="document",
        description=description,
        confidence=confidence,
        url=url,
    )
