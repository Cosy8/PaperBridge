"""Elasticsearch indexing for full-text and keyword search."""
from elasticsearch import Elasticsearch
from loguru import logger
from app.config import settings

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "title":      {"type": "text", "analyzer": "english"},
            "abstract":   {"type": "text", "analyzer": "english"},
            "authors":    {"type": "keyword"},
            "keywords":   {"type": "keyword"},
            "entities":   {"type": "object"},
            "year":       {"type": "integer"},
            "venue":      {"type": "keyword"},
            "citations":  {"type": "integer"},
            "url":        {"type": "keyword"},
            "doi":        {"type": "keyword"},
            "scholar_id": {"type": "keyword"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    }
}


def get_es_client() -> Elasticsearch:
    return Elasticsearch(settings.elasticsearch_url)


def ensure_index(es: Elasticsearch) -> None:
    if not es.indices.exists(index=settings.elasticsearch_index):
        es.indices.create(index=settings.elasticsearch_index, body=INDEX_MAPPING)
        logger.info(f"Created ES index: {settings.elasticsearch_index}")


def index_article(es: Elasticsearch, article: dict) -> None:
    """Index article metadata (excluding embedding vectors)."""
    doc = {k: v for k, v in article.items() if k != "embedding"}
    doc_id = article.get("doi") or article.get("scholar_id") or article.get("title", "unknown")
    es.index(index=settings.elasticsearch_index, id=doc_id, document=doc)
    logger.debug(f"ES indexed: {doc_id[:60]}")


def search_articles(es: Elasticsearch, query: str, size: int = 20) -> list[dict]:
    """Full-text search across title, abstract, and keywords."""
    response = es.search(
        index=settings.elasticsearch_index,
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "abstract^2", "keywords^2", "authors"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            },
            "size": size,
        }
    )
    return [hit["_source"] for hit in response["hits"]["hits"]]
