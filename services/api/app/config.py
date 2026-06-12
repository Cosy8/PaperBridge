from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_url: SecretStr
    redis_url: str = "redis://redis:6379/0"
    elasticsearch_url: str = "http://elasticsearch:9200"
    elasticsearch_index: str = "articles"
    faiss_index_path: str = "/data/faiss/articles.index"
    faiss_dimension: int = 384
    embedding_model: str = "all-MiniLM-L6-v2"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    api_secret_key: SecretStr
    api_cors_origins: str = "http://localhost:3000"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"

    class Config:
        env_file = ".env"


settings = Settings()
