import json

from kafka import KafkaProducer
from loguru import logger

from app.config import settings


def get_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
        retries=5,
    )


def publish_raw_article(producer: KafkaProducer, article: dict) -> None:
    key = article.get("doi") or article.get("title", "unknown")
    future = producer.send(settings.kafka_topic_raw_articles, key=key, value=article)
    meta = future.get(timeout=10)
    logger.info(f"Published → {meta.topic}:{meta.partition}:{meta.offset}")
