from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_raw_articles: str = "raw-articles"
    kafka_topic_processed: str = "processed-articles"
    kafka_consumer_group: str = "processor-group"
    elasticsearch_url: str = "http://elasticsearch:9200"
    elasticsearch_index: str = "articles"
    postgres_url: SecretStr
    faiss_index_path: str = "/data/faiss/articles.index"
    faiss_dimension: int = 384
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_experiment_name: str = "paperbridge-embeddings"
    embedding_model: str = "all-MiniLM-L6-v2"
    keybert_model: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"


settings = Settings()
