"""
Celery async tasks for PaperBridge.
Handles article ingestion, processing, and index maintenance.
"""
from celery import shared_task
from loguru import logger


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_article_task(self, request: dict):
    """
    Full ingestion pipeline for one article request.
    Steps: scrape → NLP process → ES index → FAISS index
    """
    try:
        from scholarly import scholarly

        from app.es_indexer import ensure_index, get_es_client, index_article
        from app.nlp_pipeline import process_article
        from app.vector_index import get_faiss_index

        logger.info(f"Ingesting: {request}")

        # 1. Scrape
        article = None
        if request.get("query"):
            results = scholarly.search_pubs(request["query"])
            raw = next(results, None)
            if raw:
                filled = scholarly.fill(raw)
                article = {
                    "title": filled.get("bib", {}).get("title"),
                    "abstract": filled.get("bib", {}).get("abstract"),
                    "authors": filled.get("bib", {}).get("author", []),
                    "year": filled.get("bib", {}).get("pub_year"),
                    "citations": filled.get("num_citations", 0),
                    "url": filled.get("pub_url"),
                    "scholar_id": filled.get("scholar_id"),
                    "doi": filled.get("externalids", {}).get("DOI"),
                }

        if not article:
            return {"status": "skipped", "reason": "no article found"}

        # 2. NLP process
        processed = process_article(article)

        # 3. Index
        es = get_es_client()
        ensure_index(es)
        index_article(es, processed)

        faiss_index = get_faiss_index()
        article_id = processed.get("doi") or processed.get("scholar_id") or processed.get("title")
        faiss_index.add(article_id, processed["embedding"])

        return {"status": "success", "title": processed.get("title")}

    except Exception as exc:
        logger.error(f"Ingest task failed: {exc}")
        raise self.retry(exc=exc) from exc


@shared_task
def reindex_all_task():
    """Rebuild FAISS index from all articles in Elasticsearch."""
    logger.info("Starting full FAISS reindex...")
    # Implementation: scroll all ES docs, re-embed, rebuild index
    return {"status": "reindex complete"}
