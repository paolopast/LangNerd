from __future__ import annotations

import logging
from typing import Dict, List

import httpx


logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search"


def search_web(
    query: str,
    *,
    api_key: str,
    max_results: int = 6,
    country: str = "it",
    language: str = "it",
) -> List[Dict[str, str]]:
    """Query SerpAPI (Google Search) to retrieve high-quality snippets."""

    if not query:
        return []

    params = {
        "engine": "google",
        "q": query,
        "gl": country,
        "hl": language,
        "num": max(3, min(max_results, 10)),
        "api_key": api_key,
    }

    try:
        response = httpx.get(SERPAPI_ENDPOINT, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        logger.exception("SerpAPI search failed for query '%s': %s", query, exc)
        return []

    organic = data.get("organic_results") or []
    cleaned: List[Dict[str, str]] = []
    seen_urls: set[str] = set()

    for item in organic:
        url = item.get("link") or item.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        cleaned.append(
            {
                "title": item.get("title") or "Risultato senza titolo",
                "url": url,
                "snippet": item.get("snippet")
                or " ".join(item.get("snippet_highlighted_words", []))
                or item.get("description")
                or "",
            }
        )
        if len(cleaned) >= max_results:
            break

    return cleaned
