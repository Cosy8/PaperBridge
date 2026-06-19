"""Tests for the worker's Semantic Scholar client and ingest-request resolution."""
from unittest.mock import patch


class TestToArticle:
    def test_maps_api_fields(self):
        from app.semantic_scholar import _to_article

        paper = {
            "title": "Test Paper",
            "abstract": "Test abstract text",
            "authors": [{"name": "Author One"}, {"name": "Author Two"}],
            "year": 2023,
            "venue": "NeurIPS",
            "citationCount": 100,
            "url": "https://example.com/paper",
            "paperId": "abc123",
            "externalIds": {"DOI": "10.1234/test"},
        }

        article = _to_article(paper)

        assert article["title"] == "Test Paper"
        assert article["authors"] == ["Author One", "Author Two"]
        assert article["doi"] == "10.1234/test"
        assert article["scholar_id"] == "abc123"
        assert article["citations"] == 100

    def test_handles_missing_optional_fields(self):
        from app.semantic_scholar import _to_article

        article = _to_article({"title": "Sparse Paper", "paperId": "x1"})

        assert article["doi"] is None
        assert article["authors"] == []
        assert article["citations"] == 0


class TestFetchArticle:
    def test_prefers_doi_lookup_when_present(self):
        from app import semantic_scholar

        with patch.object(
            semantic_scholar, "fetch_by_doi", return_value={"title": "By DOI"}
        ) as by_doi, patch.object(semantic_scholar, "fetch_by_query") as by_query:
            result = semantic_scholar.fetch_article({"doi": "10.1/x", "query": "ignored"})

        by_doi.assert_called_once_with("10.1/x")
        by_query.assert_not_called()
        assert result["title"] == "By DOI"

    def test_falls_back_to_query_when_doi_missing(self):
        from app import semantic_scholar

        with patch.object(semantic_scholar, "fetch_by_doi", return_value=None) as by_doi, patch.object(
            semantic_scholar, "fetch_by_query", return_value={"title": "By Query"}
        ) as by_query:
            result = semantic_scholar.fetch_article({"doi": "10.1/missing", "query": "deep learning"})

        by_doi.assert_called_once_with("10.1/missing")
        by_query.assert_called_once_with("deep learning")
        assert result["title"] == "By Query"

    def test_returns_none_when_no_doi_or_query(self):
        from app.semantic_scholar import fetch_article

        assert fetch_article({}) is None
