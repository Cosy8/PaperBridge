
from pydantic import BaseModel


class RecommendationRequest(BaseModel):
    article_id: str | None = None
    query_text: str | None = None

    model_config = {"json_schema_extra": {"example": {"query_text": "attention mechanism transformer NLP"}}}


class RecommendationResponse(BaseModel):
    article_id: str
    title: str
    abstract: str | None = None
    authors: list[str] = []
    keywords: list[str] = []
    year: int | None = None
    venue: str | None = None
    citations: int = 0
    url: str | None = None
    score: float
    method: str
