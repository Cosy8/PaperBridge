from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_raw_articles: str = "raw-articles"
    # Semantic Scholar API. Key is optional but lifts the rate limit; request one
    # at https://www.semanticscholar.org/product/api. Stored as a SecretStr.
    semantic_scholar_api_key: SecretStr | None = None
    max_results_per_query: int = 20
    request_delay_seconds: float = 1.0
    # Comma-separated search queries to ingest. Empty by default — no seeded data.
    seed_queries: str = ""
    minio_endpoint: str = "minio:9000"
    minio_access_key: str
    minio_secret_key: SecretStr
    minio_bucket_raw: str = "raw-html"

    class Config:
        env_file = ".env"


settings = Settings()
