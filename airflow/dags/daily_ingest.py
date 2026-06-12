"""
PaperBridge Airflow DAG: Daily article ingestion pipeline.

Orchestrates: seed query scraping → Kafka publish → processor trigger → index validation
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {
    "owner": "paperbridge",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

SEED_QUERIES = [
    "large language models 2024",
    "graph neural networks recommendation",
    "transformer architecture attention",
    "retrieval augmented generation",
    "contrastive learning self-supervised",
    "diffusion models image generation",
    "federated learning privacy",
    "knowledge graph embedding",
]


def scrape_and_publish(query: str, **context):
    """Scrape Scholar for a query and publish to Kafka."""
    import json
    import time
    from kafka import KafkaProducer
    from scholarly import scholarly

    producer = KafkaProducer(
        bootstrap_servers="kafka:9092",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    count = 0
    for result in scholarly.search_pubs(query):
        try:
            filled = scholarly.fill(result)
            article = {
                "title": filled.get("bib", {}).get("title"),
                "abstract": filled.get("bib", {}).get("abstract"),
                "authors": filled.get("bib", {}).get("author", []),
                "year": filled.get("bib", {}).get("pub_year"),
                "citations": filled.get("num_citations", 0),
                "url": filled.get("pub_url"),
                "scholar_id": filled.get("scholar_id"),
                "doi": filled.get("externalids", {}).get("DOI"),
                "source_query": query,
            }
            if article["title"]:
                producer.send("raw-articles", value=article)
                count += 1
            if count >= 20:  # Limit per query per run
                break
            time.sleep(2)
        except Exception as e:
            print(f"Error on result: {e}")

    producer.flush()
    print(f"Published {count} articles for query: {query}")
    return count


def validate_index(**context):
    """Validate Elasticsearch index health after ingestion."""
    from elasticsearch import Elasticsearch
    es = Elasticsearch("http://elasticsearch:9200")
    stats = es.indices.stats(index="articles")
    doc_count = stats["_all"]["primaries"]["docs"]["count"]
    print(f"Index validation: {doc_count} documents in ES")
    if doc_count == 0:
        raise ValueError("Elasticsearch index is empty after ingestion!")
    return doc_count


with DAG(
    "paperbridge_daily_ingest",
    default_args=DEFAULT_ARGS,
    description="Daily article ingestion pipeline",
    schedule_interval="0 2 * * *",  # 2am daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["paperbridge", "ingestion"],
) as dag:

    scrape_tasks = [
        PythonOperator(
            task_id=f"scrape_{query.replace(' ', '_')[:30]}",
            python_callable=scrape_and_publish,
            op_kwargs={"query": query},
        )
        for query in SEED_QUERIES
    ]

    validate = PythonOperator(
        task_id="validate_index",
        python_callable=validate_index,
    )

    warm_cache = BashOperator(
        task_id="warm_recommendation_cache",
        bash_command="""
            curl -s -X POST http://api:8000/api/v1/recommendations/ \
              -H 'Content-Type: application/json' \
              -d '{"query_text": "machine learning"}' > /dev/null
            echo "Cache warmed"
        """,
    )

    scrape_tasks >> validate >> warm_cache
