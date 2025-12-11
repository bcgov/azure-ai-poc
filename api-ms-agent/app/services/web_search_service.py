"""
Web Search Service for Deep Research Agent.

Provides web search capabilities using DuckDuckGo Search library
to get current information from the web for research reports.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException

from app.logger import get_logger

logger = get_logger(__name__)

# Dedicated thread pool for web search operations
# Larger than default to handle concurrent research requests
_WEB_SEARCH_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="web_search_")


@dataclass
class WebSearchResult:
    """A single web search result."""

    title: str
    url: str
    snippet: str
    source: str = "web"


class WebSearchService:
    """
    Web search service using DuckDuckGo Search library.

    Provides free web search without API keys for research augmentation.
    Uses the official duckduckgo-search library for reliable results.
    Uses a dedicated thread pool to avoid blocking the main event loop.
    """

    def __init__(self) -> None:
        """Initialize the web search service."""
        logger.info("WebSearchService initialized with dedicated thread pool")

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
            # Run synchronous DuckDuckGo search in dedicated thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                _WEB_SEARCH_EXECUTOR,
                lambda: self._search_sync(query, max_results),
            )

            logger.info(
                "web_search_completed",
                query=query,
                results_count=len(results),
            )

            return results

        except (DDGSException, RatelimitException) as e:
            logger.warning("ddgs_search_error", query=query, error=str(e))
            # Return empty on rate limit - agent will use LLM knowledge
            return []
        except Exception as e:
            logger.error(
                "web_search_failed", query=query, error=str(e), error_type=type(e).__name__
            )
            return []

    def _search_sync(self, query: str, max_results: int) -> list[WebSearchResult]:
        """
        Synchronous search implementation using DDGS.

        Args:
            query: The search query.
            max_results: Maximum number of results.

        Returns:
            List of WebSearchResult objects.
        """
        results = []

        try:
            with DDGS() as ddgs:
                # Use text search for general web results
                # Region ca-en for Canadian English results
                search_results = ddgs.text(
                    query,
                    max_results=max_results,
                    region="ca-en",  # Canadian English
                    safesearch="moderate",
                )

                for result in search_results:
                    if not result:
                        continue

                    title = result.get("title", "")
                    url = result.get("href", result.get("link", ""))
                    snippet = result.get("body", result.get("snippet", ""))

                    if title and url:
                        results.append(
                            WebSearchResult(
                                title=title.strip(),
                                url=url.strip(),
                                snippet=snippet[:500] if snippet else "",
                                source="duckduckgo",
                            )
                        )

        except (DDGSException, RatelimitException):
            # Re-raise to handle at async level
            raise
        except Exception as e:
            logger.warning(
                "ddgs_search_error",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )

        return results

    async def search_news(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[WebSearchResult]:
        """
        Search news articles using DuckDuckGo News.

        Args:
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            List of news search results.
        """
        logger.info("news_search_started", query=query, max_results=max_results)

        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._search_news_sync(query, max_results),
            )

            logger.info(
                "news_search_completed",
                query=query,
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error("news_search_failed", query=query, error=str(e))
            return []

    def _search_news_sync(self, query: str, max_results: int) -> list[WebSearchResult]:
        """
        Synchronous news search implementation.

        Args:
            query: The search query.
            max_results: Maximum number of results.

        Returns:
            List of WebSearchResult objects from news.
        """
        results = []

        try:
            with DDGS() as ddgs:
                news_results = ddgs.news(
                    query,
                    max_results=max_results,
                    region="ca-en",  # Canadian English
                    safesearch="moderate",
                )

                for result in news_results:
                    if not result:
                        continue

                    title = result.get("title", "")
                    url = result.get("url", result.get("link", ""))
                    snippet = result.get("body", result.get("excerpt", ""))
                    source = result.get("source", "news")

                    if title and url:
                        results.append(
                            WebSearchResult(
                                title=title.strip(),
                                url=url.strip(),
                                snippet=snippet[:500] if snippet else "",
                                source=f"news:{source}" if source else "news",
                            )
                        )

        except Exception as e:
            logger.warning(
                "ddgs_news_error",
                query=query,
                error=str(e),
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
            for query, result in zip(queries, results, strict=True)
        }

    async def close(self) -> None:
        """Close the service (no persistent resources to clean up)."""
        logger.info("WebSearchService closed")


# Global service instance
_web_search_service: WebSearchService | None = None


def get_web_search_service() -> WebSearchService:
    """Get or create the global web search service."""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
