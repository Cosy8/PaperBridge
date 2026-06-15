from loguru import logger

from app.config import settings
from app.producer import get_producer, publish_raw_article
from app.semantic_scholar import fetch_articles


def main():
    logger.info("PaperBridge Scraper starting...")
    queries = [q.strip() for q in settings.seed_queries.split(",") if q.strip()]
    if not queries:
        logger.warning("No SEED_QUERIES configured; nothing to scrape. Exiting.")
        return
    producer = get_producer()
    for query in queries:
        logger.info(f"Scraping: {query}")
        try:
            for article in fetch_articles(query):
                if article.get("title"):
                    publish_raw_article(producer, article)
        except Exception as e:
            logger.error(f"Query '{query}' failed: {e}")
    producer.flush()

if __name__ == "__main__":
    main()
