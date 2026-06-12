from loguru import logger
from app.producer import get_producer, publish_raw_article
from app.scholar_scraper import fetch_articles, setup_proxy

SEED_QUERIES = [
    "transformer neural network attention mechanism",
    "large language model fine-tuning",
    "graph neural network recommendation system",
]

def main():
    logger.info("PaperBridge Scraper starting...")
    setup_proxy()
    producer = get_producer()
    for query in SEED_QUERIES:
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
