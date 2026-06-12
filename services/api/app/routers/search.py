"""Full-text search endpoint backed by Elasticsearch."""
from fastapi import APIRouter, Query
from typing import Annotated
from elasticsearch import Elasticsearch
from app.config import settings

router = APIRouter()


def get_es():
    return Elasticsearch(settings.elasticsearch_url)


@router.get("/")
async def search(
    q: Annotated[str, Query(min_length=2)],
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    year_from: int | None = None,
    year_to: int | None = None,
):
    """Full-text search across titles, abstracts, and keywords."""
    es = get_es()
    must = [{"multi_match": {"query": q, "fields": ["title^3", "abstract^2", "keywords^2"], "fuzziness": "AUTO"}}]
    filters = []
    if year_from:
        filters.append({"range": {"year": {"gte": year_from}}})
    if year_to:
        filters.append({"range": {"year": {"lte": year_to}}})

    body = {"query": {"bool": {"must": must, "filter": filters}}, "size": size,
            "highlight": {"fields": {"title": {}, "abstract": {"fragment_size": 200}}}}

    response = es.search(index=settings.elasticsearch_index, body=body)
    return {
        "total": response["hits"]["total"]["value"],
        "results": [
            {**hit["_source"], "id": hit["_id"], "score": hit["_score"],
             "highlights": hit.get("highlight", {})}
            for hit in response["hits"]["hits"]
        ],
    }
