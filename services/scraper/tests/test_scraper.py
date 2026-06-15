"""Tests for the Kafka producer and article scraper."""
from unittest.mock import MagicMock, patch


class TestKafkaProducer:
    def test_publish_raw_article_sends_to_kafka(self):
        from app.producer import publish_raw_article

        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get.return_value = MagicMock(topic="raw-articles", partition=0, offset=1)
        mock_producer.send.return_value = mock_future

        article = {
            "title": "Test Article",
            "doi": "10.1234/test",
            "abstract": "Test abstract",
        }
        publish_raw_article(mock_producer, article)

        mock_producer.send.assert_called_once()
        call_kwargs = mock_producer.send.call_args
        assert call_kwargs[0][0] == "raw-articles"
        assert call_kwargs[1]["key"] == "10.1234/test"  # uses DOI as key

    def test_publish_uses_title_as_key_when_no_doi(self):
        from app.producer import publish_raw_article

        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get.return_value = MagicMock(topic="raw-articles", partition=0, offset=2)
        mock_producer.send.return_value = mock_future

        article = {"title": "No DOI Article", "abstract": "Some abstract"}
        publish_raw_article(mock_producer, article)

        call_kwargs = mock_producer.send.call_args
        assert call_kwargs[1]["key"] == "No DOI Article"


class TestSemanticScholarClient:
    def test_fetch_articles_maps_api_response(self):
        from app.semantic_scholar import fetch_articles

        page = {
            "data": [
                {
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
            ]
            # no "next" key → single page, generator stops
        }

        with patch("app.semantic_scholar._search_page", return_value=page), \
             patch("app.semantic_scholar.time.sleep"):
            results = list(fetch_articles("test query"))

        assert len(results) == 1
        assert results[0]["title"] == "Test Paper"
        assert results[0]["authors"] == ["Author One", "Author Two"]
        assert results[0]["doi"] == "10.1234/test"
        assert results[0]["scholar_id"] == "abc123"
        assert results[0]["citations"] == 100

    def test_fetch_articles_handles_missing_optional_fields(self):
        from app.semantic_scholar import fetch_articles

        page = {"data": [{"title": "Sparse Paper", "paperId": "x1"}]}

        with patch("app.semantic_scholar._search_page", return_value=page), \
             patch("app.semantic_scholar.time.sleep"):
            results = list(fetch_articles("q"))

        assert results[0]["doi"] is None
        assert results[0]["authors"] == []
        assert results[0]["citations"] == 0
