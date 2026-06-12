from pydantic import BaseModel
from typing import Optional


class RecommendationRequest(BaseModel):
    article_id: Optional[str] = None
    query_text: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {"query_text": "attention mechanism transformer NLP"}}}


class RecommendationResponse(BaseModel):
    article_id: str
    title: str
    abstract: Optional[str] = None
    authors: list[str] = []
    keywords: list[str] = []
    year: Optional[int] = None
    venue: Optional[str] = None
    citations: int = 0
    url: Optional[str] = None
    score: float
    method: str
