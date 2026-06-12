"""
NLP Pipeline: keyword extraction + semantic embedding generation.
Uses KeyBERT for keyword extraction and sentence-transformers for embeddings.
"""
from typing import Optional
import spacy
import numpy as np
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from loguru import logger
from app.config import settings

_nlp: Optional[spacy.Language] = None
_kw_model: Optional[KeyBERT] = None
_embed_model: Optional[SentenceTransformer] = None


def get_nlp() -> spacy.Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def get_kw_model() -> KeyBERT:
    global _kw_model
    if _kw_model is None:
        _kw_model = KeyBERT(model=settings.keybert_model)
    return _kw_model


def get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(settings.embedding_model)
    return _embed_model


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Extract keywords using KeyBERT with Maximal Marginal Relevance."""
    if not text:
        return []
    keywords = get_kw_model().extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        stop_words="english",
        use_mmr=True,
        diversity=0.5,
        top_n=top_n,
    )
    return [kw for kw, _ in keywords]


def extract_entities(text: str) -> list[dict]:
    """Extract named entities using spaCy NER."""
    if not text:
        return []
    doc = get_nlp()(text[:10000])
    return [{"text": ent.text, "label": ent.label_} for ent in doc.ents]


def generate_embedding(text: str) -> np.ndarray:
    """Generate 384-dim semantic embedding (normalized for cosine similarity)."""
    embedding = get_embed_model().encode(text, normalize_embeddings=True)
    return embedding.astype(np.float32)


def process_article(article: dict) -> dict:
    """Full NLP processing pipeline for one article."""
    text = f"{article.get('title', '')} {article.get('abstract', '')}"
    logger.info(f"Processing: {article.get('title', 'unknown')[:60]}")
    return {
        **article,
        "keywords": extract_keywords(text),
        "entities": extract_entities(text),
        "embedding": generate_embedding(text).tolist(),
        "processed": True,
    }
