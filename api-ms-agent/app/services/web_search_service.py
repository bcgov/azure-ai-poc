"""
Web Search Service for Deep Research Agent.

Provides web search capabilities using DuckDuckGo (free, no API key required)
to get current information from the web for research reports.
"""

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.logger import get_logger

logger = get_logger(__name__)

# DuckDuckGo HTML search endpoint (no API key needed)
DUCKDUCKGO_HTML_URL = "https://html.duckduckgo.com/html/"

# User agent to avoid blocks
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class WebSearchResult:
    """A single web search result."""

    title: str
    url: str
    snippet: str
    source: str = "web"


class WebSearchService:
    """
    Web search service using DuckDuckGo.

    Provides free web search without API keys for research augmentation.
    """

    def __init__(self) -> None:
        """Initialize the web search service."""
        self._client: httpx.AsyncClient | None = None
        logger.info("WebSearchService initialized")

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
        return self._client

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[WebSearchResult]:
        """
        Search the web using DuckDuckGo.

        Args:
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results with title, URL, and snippet.
        """
        logger.info("web_search_started", query=query, max_results=max_results)

        try:
            client = self._get_client()

            # Use DuckDuckGo HTML endpoint
            response = await client.post(
                DUCKDUCKGO_HTML_URL,
                data={"q": query, "b": ""},
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()

            # Parse HTML response to extract results
            results = self._parse_duckduckgo_html(response.text, max_results)

            logger.info(
                "web_search_completed",
                query=query,
                results_count=len(results),
            )

            return results

        except httpx.TimeoutException:
            logger.warning("web_search_timeout", query=query)
            return []
        except Exception as e:
            logger.error("web_search_failed", query=query, error=str(e))
            return []

    def _parse_duckduckgo_html(
        self,
        html: str,
        max_results: int,
    ) -> list[WebSearchResult]:
        """
        Parse DuckDuckGo HTML response to extract search results.

        Args:
            html: The HTML response from DuckDuckGo.
            max_results: Maximum number of results to extract.

        Returns:
            List of parsed search results.
        """
        import re

        results = []

        # Find all result blocks - DuckDuckGo uses class="result"
        # Each result has: result__a (link), result__snippet (description)
        result_pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
            r'.*?<a[^>]*class="result__snippet"[^>]*>([^<]*(?:<[^>]*>[^<]*)*)</a>',
            re.DOTALL | re.IGNORECASE,
        )

        # Alternative pattern for result blocks
        alt_pattern = re.compile(
            r'<h2[^>]*class="result__title"[^>]*>.*?'
            r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )

        # Try primary pattern
        matches = result_pattern.findall(html)
        if not matches:
            matches = alt_pattern.findall(html)

        # Fallback: simpler extraction
        if not matches:
            # Extract links with result__url class
            url_pattern = re.compile(
                r'<a[^>]*class="[^"]*result__url[^"]*"[^>]*href="([^"]*)"[^>]*>',
                re.IGNORECASE,
            )
            title_pattern = re.compile(
                r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*>([^<]+)</a>',
                re.IGNORECASE,
            )
            snippet_pattern = re.compile(
                r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
                re.DOTALL | re.IGNORECASE,
            )

            urls = url_pattern.findall(html)
            titles = title_pattern.findall(html)
            snippets = snippet_pattern.findall(html)

            # Combine into matches
            for i in range(min(len(urls), len(titles), len(snippets), max_results)):
                matches.append((urls[i], titles[i], snippets[i]))

        for match in matches[:max_results]:
            url, title, snippet = match

            # Clean up snippet (remove HTML tags)
            snippet = re.sub(r"<[^>]+>", "", snippet)
            snippet = snippet.strip()

            # Skip if essential data is missing
            if not url or not title:
                continue

            # Decode URL if needed
            if url.startswith("//duckduckgo.com/l/?"):
                # Extract actual URL from DuckDuckGo redirect
                url_match = re.search(r"uddg=([^&]+)", url)
                if url_match:
                    from urllib.parse import unquote

                    url = unquote(url_match.group(1))

            results.append(
                WebSearchResult(
                    title=title.strip(),
                    url=url,
                    snippet=snippet[:500],  # Limit snippet length
                    source="duckduckgo",
                )
            )

        return results

    async def search_multiple(
        self,
        queries: list[str],
        max_results_per_query: int = 3,
    ) -> dict[str, list[WebSearchResult]]:
        """
        Search multiple queries in parallel.

        Args:
            queries: List of search queries.
            max_results_per_query: Maximum results per query.

        Returns:
            Dictionary mapping queries to their results.
        """
        tasks = [self.search(q, max_results_per_query) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            query: result if isinstance(result, list) else []
            for query, result in zip(queries, results)
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("WebSearchService closed")


# Global service instance
_web_search_service: WebSearchService | None = None


def get_web_search_service() -> WebSearchService:
    """Get or create the global web search service."""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
