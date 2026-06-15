"""
PaperBridge Airflow DAG: Daily article ingestion pipeline.

Orchestrates: seed query scraping → Kafka publish → processor trigger → index validation
"""
import os
from datetime import datetime, timedelta

from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from airflow import DAG

DEFAULT_ARGS = {
    "owner": "paperbridge",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# Comma-separated search queries to ingest, supplied via env. Empty by default —
# no seeded data. Set SEED_QUERIES (e.g. "query one,query two") to enable.
SEED_QUERIES = [q.strip() for q in os.getenv("SEED_QUERIES", "").split(",") if q.strip()]


S2_FIELDS = "title,abstract,authors,year,venue,citationCount,externalIds,url,paperId"
S2_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


class _RateLimitedError(Exception):
    """Raised on HTTP 429 so tenacity retries with a long, header-aware backoff."""


def _search_page(query: str, offset: int, limit: int) -> dict:
    """One Semantic Scholar search page with 429-aware retry.

    Mirrors the scraper/worker clients (separate images can't share a module).
    """
    import contextlib
    import os
    import time

    import requests
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )

    headers = {}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    @retry(
        retry=retry_if_exception_type(_RateLimitedError),
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        reraise=True,
    )
    def _do() -> dict:
        resp = requests.get(
            S2_SEARCH_URL,
            params={"query": query, "fields": S2_FIELDS, "offset": offset, "limit": limit},
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                with contextlib.suppress(ValueError):
                    time.sleep(min(float(retry_after), 60))
            print(f"Rate limited (429) on '{query}' @ offset {offset}; retrying")
            raise _RateLimitedError
        resp.raise_for_status()
        return resp.json()

    return _do()


def scrape_and_publish(query: str, **context):
    """Search Semantic Scholar for a query and publish results to Kafka."""
    import json
    import time

    from kafka import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers="kafka:9092",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    count = 0
    offset = 0
    limit = 20  # cap per query per run
    while count < limit:
        try:
            payload = _search_page(query, offset, limit - count)
        except Exception as e:
            print(f"Search request failed: {e}")
            break

        papers = payload.get("data") or []
        if not papers:
            break

        for paper in papers:
            external_ids = paper.get("externalIds") or {}
            authors = [a.get("name") for a in (paper.get("authors") or []) if a.get("name")]
            article = {
                "title": paper.get("title"),
                "abstract": paper.get("abstract"),
                "authors": authors,
                "year": paper.get("year"),
                "venue": paper.get("venue"),
                "citations": paper.get("citationCount", 0),
                "url": paper.get("url"),
                "scholar_id": paper.get("paperId"),
                "doi": external_ids.get("DOI"),
                "source_query": query,
            }
            if article["title"]:
                producer.send("raw-articles", value=article)
                count += 1

        if "next" not in payload:
            break
        offset = payload["next"]
        time.sleep(1)

    producer.flush()
    print(f"Published {count} articles for query: {query}")
    return count


def validate_index(**context):
    """Validate Elasticsearch index health after ingestion."""
    from elasticsearch import Elasticsearch
    es = Elasticsearch("http://elasticsearch:9200")
    stats = es.indices.stats(index="articles")
    doc_count = stats["_all"]["primaries"]["docs"]["count"]
    print(f"Index validation: {doc_count} documents in ES")
    if doc_count == 0:
        raise ValueError("Elasticsearch index is empty after ingestion!")
    return doc_count


with DAG(
    "paperbridge_daily_ingest",
    default_args=DEFAULT_ARGS,
    description="Daily article ingestion pipeline",
    schedule_interval="0 2 * * *",  # 2am daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["paperbridge", "ingestion"],
) as dag:

    scrape_tasks = [
        PythonOperator(
            task_id=f"scrape_{query.replace(' ', '_')[:30]}",
            python_callable=scrape_and_publish,
            op_kwargs={"query": query},
        )
        for query in SEED_QUERIES
    ]

    validate = PythonOperator(
        task_id="validate_index",
        python_callable=validate_index,
    )

    warm_cache = BashOperator(
        task_id="warm_recommendation_cache",
        bash_command="""
            curl -s -X POST http://api:8000/api/v1/recommendations/ \
              -H 'Content-Type: application/json' \
              -d '{"query_text": "machine learning"}' > /dev/null
            echo "Cache warmed"
        """,
    )

    scrape_tasks >> validate >> warm_cache
