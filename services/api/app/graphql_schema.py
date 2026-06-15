"""
GraphQL API using Strawberry.
Exposes article search and recommendations via a typed graph.
"""

import strawberry
from strawberry.fastapi import GraphQLRouter


@strawberry.type
class ArticleType:
    id: str
    title: str
    abstract: str | None
    authors: list[str]
    keywords: list[str]
    year: int | None
    venue: str | None
    citations: int
    url: str | None


@strawberry.type
class RecommendationType:
    article: ArticleType
    score: float
    method: str


@strawberry.type
class Query:
    @strawberry.field
    async def recommend(
        self,
        query_text: str,
        top_k: int = 10,
        method: str = "hybrid",
    ) -> list[RecommendationType]:
        """Get article recommendations for a query string."""
        from app.schemas.recommendation import RecommendationRequest
        from app.services.recommender import get_recommendations
        results = await get_recommendations(
            request=RecommendationRequest(query_text=query_text),
            top_k=top_k,
            method=method,
            db=None,
        )
        return [
            RecommendationType(
                article=ArticleType(
                    id=r.article_id,
                    title=r.title,
                    abstract=r.abstract,
                    authors=r.authors,
                    keywords=r.keywords,
                    year=r.year,
                    venue=r.venue,
                    citations=r.citations,
                    url=r.url,
                ),
                score=r.score,
                method=r.method,
            )
            for r in results
        ]


schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema)
