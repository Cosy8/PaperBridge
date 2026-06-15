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


class TestScholarScraper:
    def test_fetch_articles_yields_dicts(self):
        from app.scholar_scraper import fetch_articles

        mock_filled = {
            "bib": {
                "title": "Test Paper",
                "abstract": "Test abstract text",
                "author": ["Author One", "Author Two"],
                "pub_year": "2023",
                "venue": "NeurIPS",
            },
            "num_citations": 100,
            "pub_url": "https://example.com/paper",
            "scholar_id": "abc123",
            "externalids": {"DOI": "10.1234/test"},
        }

        with patch("app.scholar_scraper.scholarly") as mock_scholarly, \
             patch("app.scholar_scraper.time.sleep"):
            mock_scholarly.search_pubs.return_value = iter([mock_filled])
            mock_scholarly.fill.return_value = mock_filled

            results = list(fetch_articles("test query"))

        assert len(results) == 1
        assert results[0]["title"] == "Test Paper"
        assert results[0]["doi"] == "10.1234/test"
        assert results[0]["citations"] == 100

    def test_setup_proxy_skipped_when_disabled(self):
        from app.scholar_scraper import setup_proxy

        with patch("app.scholar_scraper.settings") as mock_settings, \
             patch("app.scholar_scraper.scholarly") as mock_scholarly:
            mock_settings.scholar_use_proxy = False
            setup_proxy()
            mock_scholarly.use_proxy.assert_not_called()
