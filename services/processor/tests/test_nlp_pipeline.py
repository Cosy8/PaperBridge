"""
Tests for the NLP processing pipeline.
Tests keyword extraction, entity recognition, and embedding generation.
"""
import numpy as np

SAMPLE_ABSTRACT = """
We introduce BERT, a new language representation model which stands for Bidirectional Encoder
Representations from Transformers. Unlike recent language representation models, BERT is designed
to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both
left and right context in all layers. As a result, the pre-trained BERT model can be fine-tuned
with just one additional output layer to create state-of-the-art models for a wide range of tasks,
such as question answering and language inference.
"""

SAMPLE_ARTICLE = {
    "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
    "abstract": SAMPLE_ABSTRACT,
    "authors": ["Devlin, J.", "Chang, M.", "Lee, K.", "Toutanova, K."],
    "year": 2019,
    "citations": 40000,
}


class TestKeywordExtraction:
    def test_extracts_keywords_from_text(self):
        from app.nlp_pipeline import extract_keywords
        keywords = extract_keywords(SAMPLE_ABSTRACT, top_n=5)
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        assert all(isinstance(kw, str) for kw in keywords)

    def test_returns_empty_for_empty_text(self):
        from app.nlp_pipeline import extract_keywords
        assert extract_keywords("") == []
        assert extract_keywords(None) == []  # type: ignore

    def test_keywords_are_relevant(self):
        from app.nlp_pipeline import extract_keywords
        keywords = extract_keywords(SAMPLE_ABSTRACT, top_n=10)
        nlp_terms = {"bert", "language", "transformer", "pre-training", "bidirectional"}
        found = any(any(term in kw.lower() for term in nlp_terms) for kw in keywords)
        assert found, f"No NLP keywords found in: {keywords}"


class TestEntityExtraction:
    def test_extracts_entities(self):
        from app.nlp_pipeline import extract_entities
        entities = extract_entities("Google released BERT in 2018 at NeurIPS conference.")
        assert isinstance(entities, list)
        assert all("text" in e and "label" in e for e in entities)

    def test_returns_empty_for_empty_text(self):
        from app.nlp_pipeline import extract_entities
        assert extract_entities("") == []


class TestEmbeddingGeneration:
    def test_generates_384_dim_embedding(self):
        from app.nlp_pipeline import generate_embedding
        embedding = generate_embedding("transformer neural network")
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert embedding.dtype == np.float32

    def test_embedding_is_normalized(self):
        from app.nlp_pipeline import generate_embedding
        embedding = generate_embedding("test sentence for normalization")
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 1e-5, f"Embedding not normalized: norm={norm}"

    def test_similar_texts_have_high_similarity(self):
        from app.nlp_pipeline import generate_embedding
        e1 = generate_embedding("transformer attention mechanism NLP")
        e2 = generate_embedding("self-attention neural network language model")
        e3 = generate_embedding("convolutional network image classification vision")
        sim_nlp = float(np.dot(e1, e2))
        sim_cross = float(np.dot(e1, e3))
        assert sim_nlp > sim_cross, "NLP texts should be more similar to each other"


class TestFullPipeline:
    def test_process_article_returns_all_fields(self):
        from app.nlp_pipeline import process_article
        result = process_article(SAMPLE_ARTICLE)
        assert "keywords" in result
        assert "entities" in result
        assert "embedding" in result
        assert result["processed"] is True
        assert isinstance(result["keywords"], list)
        assert isinstance(result["embedding"], list)
        assert len(result["embedding"]) == 384

    def test_process_article_preserves_original_fields(self):
        from app.nlp_pipeline import process_article
        result = process_article(SAMPLE_ARTICLE)
        assert result["title"] == SAMPLE_ARTICLE["title"]
        assert result["year"] == SAMPLE_ARTICLE["year"]
        assert result["citations"] == SAMPLE_ARTICLE["citations"]
