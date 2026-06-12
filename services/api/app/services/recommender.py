"""
Hybrid recommender service.
Combines semantic similarity (FAISS) and keyword match (Elasticsearch)
using reciprocal rank fusion for robust ranking.
"""
from __future__ import annotations
import numpy as np
from loguru import logger
from sqlalchemy.orm import Session
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.vector_index import get_faiss_index

_embed_model: SentenceTransformer | None = None
_es_client: Elasticsearch | None = None


def get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(settings.embedding_model)
    return _embed_model


def get_es() -> Elasticsearch:
    global _es_client
    if _es_client is None:
        _es_client = Elasticsearch(settings.elasticsearch_url)
    return _es_client


def reciprocal_rank_fusion(
    semantic_results: list[tuple[str, float]],
    keyword_results: list[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    Reciprocal Rank Fusion (RRF) — robust method for combining ranked lists.
    score(d) = Σ 1/(k + rank(d))
    """
    scores: dict[str, float] = {}
    for rank, (doc_id, _) in enumerate(semantic_results, start=1):
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    for rank, (doc_id, _) in enumerate(keyword_results, start=1):
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


async def get_semantic_results(text: str, top_k: int) -> list[tuple[str, float]]:
    embedding = get_embed_model().encode(text, normalize_embeddings=True).tolist()
    faiss_index = get_faiss_index()
    return faiss_index.search(embedding, top_k=top_k * 2)


async def get_keyword_results(text: str, top_k: int) -> list[tuple[str, float]]:
    es = get_es()
    response = es.search(
        index=settings.elasticsearch_index,
        body={
            "query": {
                "multi_match": {
                    "query": text,
                    "fields": ["title^3", "abstract^2", "keywords^2"],
                    "type": "best_fields",
                }
            },
            "size": top_k * 2,
        }
    )
    return [
        (hit["_id"], hit["_score"])
        for hit in response["hits"]["hits"]
    ]


async def get_recommendations(
    request: RecommendationRequest,
    top_k: int,
    method: str,
    db: Session,
) -> list[RecommendationResponse]:
    """Dispatch to semantic, keyword, or hybrid recommendation."""
    query_text = request.query_text or ""

    if request.article_id:
        # Fetch article text from ES to use as query
        es = get_es()
        try:
            doc = es.get(index=settings.elasticsearch_index, id=request.article_id)
            src = doc["_source"]
            query_text = f"{src.get('title', '')} {src.get('abstract', '')}"
        except Exception:
            logger.warning(f"Article {request.article_id} not found in ES")

    if not query_text:
        return []

    semantic, keyword = [], []

    if method in ("semantic", "hybrid"):
        semantic = await get_semantic_results(query_text, top_k)

    if method in ("keyword", "hybrid"):
        keyword = await get_keyword_results(query_text, top_k)

    if method == "hybrid":
        fused = reciprocal_rank_fusion(semantic, keyword)
    elif method == "semantic":
        fused = semantic
    else:
        fused = keyword

    # Fetch full metadata for top results
    results = []
    es = get_es()
    for doc_id, score in fused[:top_k]:
        if doc_id == request.article_id:
            continue  # Skip the source article itself
        try:
            doc = es.get(index=settings.elasticsearch_index, id=doc_id)
            src = doc["_source"]
            results.append(RecommendationResponse(
                article_id=doc_id,
                title=src.get("title", ""),
                abstract=src.get("abstract"),
                authors=src.get("authors", []),
                keywords=src.get("keywords", []),
                year=src.get("year"),
                venue=src.get("venue"),
                citations=src.get("citations", 0),
                url=src.get("url"),
                score=score,
                method=method,
            ))
        except Exception:
            pass

    return results
