"""
MLflow experiment tracking for embedding model evaluation.
Compares different sentence-transformer models on recommendation quality.
"""
import mlflow
import mlflow.sklearn
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


TEST_ARTICLES = [
    {"id": "a1", "text": "BERT pre-training of deep bidirectional transformers for language understanding"},
    {"id": "a2", "text": "Attention is all you need transformer architecture self-attention"},
    {"id": "a3", "text": "GPT-3 language models few-shot learners"},
    {"id": "a4", "text": "ResNet deep residual learning image recognition convolutional"},
    {"id": "a5", "text": "CLIP learning transferable visual models from natural language supervision"},
]

MODELS_TO_COMPARE = [
    "all-MiniLM-L6-v2",
    "all-mpnet-base-v2",
    "paraphrase-multilingual-MiniLM-L12-v2",
]


def evaluate_model(model_name: str) -> dict:
    """Evaluate a model by checking NLP papers cluster together."""
    model = SentenceTransformer(model_name)
    embeddings = model.encode([a["text"] for a in TEST_ARTICLES], normalize_embeddings=True)
    sim_matrix = cosine_similarity(embeddings)

    nlp_avg = np.mean([sim_matrix[0, 1], sim_matrix[0, 2], sim_matrix[1, 2]])
    cross_avg = np.mean([sim_matrix[0, 3], sim_matrix[0, 4], sim_matrix[1, 3], sim_matrix[2, 4]])
    discrimination_score = nlp_avg - cross_avg

    return {
        "nlp_cluster_similarity": float(nlp_avg),
        "cross_domain_similarity": float(cross_avg),
        "discrimination_score": float(discrimination_score),
        "model_dimension": int(embeddings.shape[1]),
    }


def run_experiments(tracking_uri: str = "http://localhost:5000"):
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("paperbridge-embeddings")

    for model_name in MODELS_TO_COMPARE:
        with mlflow.start_run(run_name=model_name):
            mlflow.log_param("model_name", model_name)
            metrics = evaluate_model(model_name)
            mlflow.log_metrics(metrics)
            print(f"{model_name}: discrimination={metrics['discrimination_score']:.4f}")

    print("\nExperiment complete. View at:", tracking_uri)


if __name__ == "__main__":
    run_experiments()
