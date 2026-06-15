"""
Recommendation endpoints.
Hybrid ranking: semantic (FAISS) + keyword (Elasticsearch) scores combined.
Results are cached in Redis for performance.
"""
import hashlib
import json
from typing import Annotated

import redis as redis_lib
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommender import get_recommendations

router = APIRouter()


def get_redis():
    return redis_lib.from_url(settings.redis_url, decode_responses=True)


@router.post("/", response_model=list[RecommendationResponse])
async def recommend(
    request: RecommendationRequest,
    top_k: Annotated[int, Query(ge=1, le=50)] = 10,
    method: Annotated[str, Query()] = "hybrid",
    db: Session = Depends(get_db),
    cache: redis_lib.Redis = Depends(get_redis),
):
    """
    Get recommended articles for a given article ID or query text.

    - **method**: `semantic` (FAISS embeddings), `keyword` (Elasticsearch), or `hybrid`
    - **top_k**: Number of results to return (max 50)
    """
    cache_key = f"rec:{hashlib.md5(f'{request.model_dump_json()}{top_k}{method}'.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)

    results = await get_recommendations(
        request=request,
        top_k=top_k,
        method=method,
        db=db,
    )

    cache.setex(cache_key, 3600, json.dumps([r.model_dump() for r in results]))
    return results


@router.get("/article/{article_id}", response_model=list[RecommendationResponse])
async def recommend_by_id(
    article_id: str,
    top_k: Annotated[int, Query(ge=1, le=50)] = 10,
    method: str = "hybrid",
    db: Session = Depends(get_db),
    cache: redis_lib.Redis = Depends(get_redis),
):
    """Get recommendations for an existing article by its ID."""
    request = RecommendationRequest(article_id=article_id)
    return await recommend(request, top_k=top_k, method=method, db=db, cache=cache)
