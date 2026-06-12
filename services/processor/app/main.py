"""
Processor service: Kafka consumer → NLP pipeline → ES + FAISS indexing.
"""
import json
from kafka import KafkaConsumer
from loguru import logger
from app.config import settings
from app.nlp_pipeline import process_article
from app.vector_index import get_faiss_index
from app.es_indexer import get_es_client, ensure_index, index_article


def main():
    logger.info("PaperBridge Processor starting...")
    es = get_es_client()
    ensure_index(es)
    faiss_index = get_faiss_index()

    consumer = KafkaConsumer(
        settings.kafka_topic_raw_articles,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    logger.info(f"Listening on topic: {settings.kafka_topic_raw_articles}")
    for message in consumer:
        article = message.value
        try:
            processed = process_article(article)
            index_article(es, processed)
            article_id = (
                processed.get("doi")
                or processed.get("scholar_id")
                or processed.get("title", "unknown")
            )
            faiss_index.add(article_id, processed["embedding"])
            logger.info(f"✓ Indexed: {processed.get('title', '')[:60]}")
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
