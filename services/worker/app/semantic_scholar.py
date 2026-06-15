"""
Semantic Scholar Academic Graph API client for the worker's ingestion task.

Replaces the old `scholarly` (Google Scholar) path. Returns the same article
dict shape the NLP pipeline expects. Supports two lookup modes:

  - by free-text query  → first search hit
  - by DOI              → exact paper lookup (`/paper/DOI:<doi>`)

Docs: https://api.semanticscholar.org/api-docs/graph
"""

import time

import requests
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

BASE_URL = "https://api.semanticscholar.org/graph/v1"

_session = requests.Session()

FIELDS = ",".join(
    [
        "title",
        "abstract",
        "authors",
        "year",
        "venue",
        "citationCount",
        "externalIds",
        "url",
        "paperId",
    ]
)


def _headers() -> dict:
    if settings.semantic_scholar_api_key:
        return {"x-api-key": settings.semantic_scholar_api_key.get_secret_value()}
    return {}


class RateLimited(Exception):
    """Raised on HTTP 429 so tenacity retries with a long, header-aware backoff."""


@retry(
    retry=retry_if_exception_type(RateLimited),
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    reraise=True,
)
def _get(path: str, params: dict) -> dict | None:
    """
    GET a Semantic Scholar endpoint with 429-aware retry.

    Returns the parsed JSON, or None on 404 (paper not found).
    """
    resp = _session.get(
        f"{BASE_URL}/{path}", params=params, headers=_headers(), timeout=30
    )

    if resp.status_code == 404:
        return None

    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                time.sleep(min(float(retry_after), 60))
            except ValueError:
                pass
        logger.warning(f"Rate limited (429) on {path}; retrying")
        raise RateLimited()

    resp.raise_for_status()
    return resp.json()


def _to_article(paper: dict) -> dict:
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


def fetch_by_doi(doi: str) -> dict | None:
    """Look up a single paper by DOI."""
    paper = _get(f"paper/DOI:{doi}", {"fields": FIELDS})
    return _to_article(paper) if paper else None


def fetch_by_query(query: str) -> dict | None:
    """Return the first search hit for a free-text query."""
    payload = _get("paper/search", {"query": query, "fields": FIELDS, "limit": 1})
    data = (payload or {}).get("data") or []
    return _to_article(data[0]) if data else None


def fetch_article(request: dict) -> dict | None:
    """
    Resolve an ingest request to a single article.

    Prefers an exact DOI lookup when provided, falling back to a query search.
    """
    if request.get("doi"):
        article = fetch_by_doi(request["doi"])
        if article:
            return article
        logger.warning(f"DOI {request['doi']} not found; falling back to query")
    if request.get("query"):
        return fetch_by_query(request["query"])
    return None
