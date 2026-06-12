from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_raw_articles: str = "raw-articles"
    scholar_use_proxy: bool = False
    max_scrape_workers: int = 4
    scrape_delay_seconds: float = 2.0
    minio_endpoint: str = "minio:9000"
    minio_access_key: str
    minio_secret_key: SecretStr
    minio_bucket_raw: str = "raw-html"

    class Config:
        env_file = ".env"


settings = Settings()
