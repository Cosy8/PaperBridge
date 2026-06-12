"""Tests for the search endpoint."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.mark.asyncio
async def test_search_returns_results():
    """Test GET /search/ returns formatted results."""
    mock_response = {
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_id": "doi:10.1234/test",
                    "_score": 1.5,
                    "_source": {
                        "title": "Test Paper",
                        "abstract": "Test abstract",
                        "authors": ["Author A"],
                        "year": 2023,
                        "keywords": ["test"],
                    },
                    "highlight": {"title": ["<em>Test</em> Paper"]},
                }
            ],
        }
    }

    with patch("app.routers.search.get_es") as mock_es_factory:
        mock_es = MagicMock()
        mock_es.search.return_value = mock_response
        mock_es_factory.return_value = mock_es

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/search/", params={"q": "test"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["results"][0]["title"] == "Test Paper"


@pytest.mark.asyncio
async def test_search_requires_min_length():
    """Test that single-char queries are rejected."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/search/", params={"q": "x"})
    assert response.status_code == 422
