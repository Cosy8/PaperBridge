"""
Semantic Scholar Academic Graph API client.

Drop-in replacement for the legacy `scholar_scraper` module: `fetch_articles()`
yields the same article dict shape consumed by the Kafka `raw-articles` topic,
so the processor / ES / FAISS pipeline is unchanged.

Why this over scraping Google Scholar: Semantic Scholar exposes an official,
documented API (abstracts, citation counts, external IDs, author lists) with a
clear usage policy — no ToS breach, no proxy/Tor evasion, better data quality.
Docs: https://api.semanticscholar.org/api-docs/graph
"""
import contextlib
import time
from collections.abc import Generator

import requests
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# Shared session so connection pooling and headers persist across pages.
_session = requests.Session()

# Fields we request from the API, mapped 1:1 onto the raw-article contract below.
FIELDS = ",".join(
    [
        "title",
        "abstract",
        "authors",       # list of {authorId, name}
        "year",
        "venue",
        "citationCount",
        "externalIds",   # dict incl. DOI
        "url",
        "paperId",       # used as scholar_id replacement
    ]
)


def _to_article(paper: dict) -> dict:
    """Map a Semantic Scholar paper object onto the raw-articles contract."""
    external_ids = paper.get("externalIds") or {}
    authors = [a.get("name") for a in (paper.get("authors") or []) if a.get("name")]
    return {
        "title": paper.get("title"),
        "abstract": paper.get("abstract"),
        "authors": authors,
        "year": paper.get("year"),
        "venue": paper.get("venue"),
        "citations": paper.get("citationCount", 0),
        "url": paper.get("url"),
        "scholar_id": paper.get("paperId"),
        "doi": external_ids.get("DOI"),
    }


class RateLimitedError(Exception):
    """Raised on HTTP 429 so tenacity retries with a long, header-aware backoff."""


@retry(
    retry=retry_if_exception_type(RateLimitedError),
    # Semantic Scholar's keyless pool is ~1 req/sec shared globally, so 429s are
    # common. Back off generously and try several times before giving up.
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    reraise=True,
)
def _search_page(query: str, offset: int, limit: int) -> dict:
    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key.get_secret_value()

    resp = _session.get(
        SEARCH_URL,
        params={"query": query, "fields": FIELDS, "offset": offset, "limit": limit},
        headers=headers,
        timeout=30,
    )

    if resp.status_code == 429:
        # Honor Retry-After when present, otherwise let tenacity's backoff handle it.
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            with contextlib.suppress(ValueError):
                time.sleep(min(float(retry_after), 60))
        logger.warning(f"Rate limited (429) on '{query}' @ offset {offset}; retrying")
        raise RateLimitedError

    resp.raise_for_status()
    return resp.json()


def fetch_articles(query: str) -> Generator[dict, None, None]:
    """
    Yield article dicts for a query, paginating until `max_results_per_query`.

    Mirrors the old scraper's generator interface so `main.py` is unchanged.
    """
    fetched = 0
    offset = 0
    page_size = min(100, settings.max_results_per_query)  # API caps page at 100

    while fetched < settings.max_results_per_query:
        limit = min(page_size, settings.max_results_per_query - fetched)
        payload = _search_page(query, offset, limit)
        papers = payload.get("data") or []
        if not papers:
            break

        for paper in papers:
            if paper.get("title"):
                yield _to_article(paper)
            fetched += 1

        # `next` is absent once the result set is exhausted.
        if "next" not in payload:
            break
        offset = payload["next"]
        time.sleep(settings.request_delay_seconds)
