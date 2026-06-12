"""
Tests for the recommendation endpoints.
Uses pytest-asyncio + httpx AsyncClient for async FastAPI testing.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app


@pytest.fixture
def mock_recommendations():
    return [
        {
            "article_id": "doi:10.1234/test1",
            "title": "Attention Is All You Need",
            "abstract": "We propose a new simple network architecture, the Transformer.",
            "authors": ["Vaswani, A.", "Shazeer, N."],
            "keywords": ["transformer", "attention", "nlp"],
            "year": 2017,
            "venue": "NeurIPS",
            "citations": 50000,
            "url": "https://arxiv.org/abs/1706.03762",
            "score": 0.95,
            "method": "hybrid",
        },
        {
            "article_id": "doi:10.1234/test2",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "abstract": "We introduce BERT, a new language representation model.",
            "authors": ["Devlin, J.", "Chang, M."],
            "keywords": ["bert", "pre-training", "nlp"],
            "year": 2019,
            "venue": "NAACL",
            "citations": 40000,
            "url": "https://arxiv.org/abs/1810.04805",
            "score": 0.88,
            "method": "hybrid",
        },
    ]


@pytest.mark.asyncio
async def test_recommend_by_query(mock_recommendations):
    """Test POST /recommendations/ with query_text."""
    with patch("app.routers.recommendations.get_redis") as mock_redis, \
         patch("app.services.recommender.get_recommendations") as mock_recs:

        redis_instance = MagicMock()
        redis_instance.get.return_value = None
        mock_redis.return_value = redis_instance

        from app.schemas.recommendation import RecommendationResponse
        mock_recs.return_value = [RecommendationResponse(**r) for r in mock_recommendations]

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/recommendations/",
                json={"query_text": "transformer attention mechanism"},
                params={"top_k": 10, "method": "hybrid"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Attention Is All You Need"
        assert data[0]["score"] == 0.95
        assert "keywords" in data[0]


@pytest.mark.asyncio
async def test_recommend_returns_cached_result(mock_recommendations):
    """Test that cached results are returned from Redis."""
    import json
    with patch("app.routers.recommendations.get_redis") as mock_redis:
        redis_instance = MagicMock()
        redis_instance.get.return_value = json.dumps(mock_recommendations)
        mock_redis.return_value = redis_instance

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/recommendations/",
                json={"query_text": "transformer"},
            )

        assert response.status_code == 200
        assert response.json()[0]["title"] == "Attention Is All You Need"


@pytest.mark.asyncio
async def test_recommend_invalid_top_k():
    """Test that top_k > 50 returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/recommendations/",
            json={"query_text": "test"},
            params={"top_k": 999},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test /health returns api status."""
    with patch("app.routers.health.SessionLocal") as mock_db, \
         patch("app.routers.health.redis") as mock_redis:

        mock_session = MagicMock()
        mock_session.execute.return_value = None
        mock_db.return_value = mock_session

        mock_redis_inst = MagicMock()
        mock_redis_inst.ping.return_value = True
        mock_redis.from_url.return_value = mock_redis_inst

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json()["api"] == "ok"
