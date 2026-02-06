import logging

from config.settings import tavily_config
from core.models import PipelineState, WebSearchResult

logger = logging.getLogger(__name__)

try:
    from tavily import TavilyClient

    tavily_client = (
        TavilyClient(api_key=tavily_config.api_key)
        if tavily_config.is_configured
        else None
    )
except ImportError:
    tavily_client = None


class WebSearchAgent:
    def search(self, state: PipelineState) -> PipelineState:
        understanding = state.get("understanding")

        if not understanding or not understanding.requires_web_search:
            logger.info("Web search skipped")
            return state

        if not tavily_client:
            logger.warning("Tavily not configured")
            state["web_search_results"] = WebSearchResult(
                query=state["query"], results=[], summary="Web search unavailable"
            )
            return state

        try:
            query = state["query"]
            logger.info(f"Searching: {query}")

            search_results = tavily_client.search(
                query=query, search_depth="advanced", max_results=5
            )

            results = search_results.get("results", [])
            summary_parts = []
            for i, result in enumerate(results, 1):
                summary_parts.append(
                    f"{i}. {result.get('title', 'Untitled')}: {result.get('content', '')[:200]}..."
                )

            state["web_search_results"] = WebSearchResult(
                query=query,
                results=results,
                summary="\n".join(summary_parts) if summary_parts else "No results",
            )

            logger.info(f"Found {len(results)} results")

        except Exception as e:
            logger.error(f"Web search failed: {e}", exc_info=True)
            state["web_search_results"] = WebSearchResult(
                query=state["query"], results=[], summary=f"Search error: {str(e)}"
            )

        return state
