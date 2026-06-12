"""Tests for FAISS vector index operations."""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock


class TestFAISSIndex:
    def test_search_returns_empty_when_no_vectors(self):
        import faiss
        from app.vector_index import FAISSIndex

        with patch("app.vector_index.settings") as mock_settings, \
             patch("app.vector_index.os.path.exists", return_value=False), \
             patch("app.vector_index.os.makedirs"):
            mock_settings.faiss_index_path = "/tmp/test.index"
            mock_settings.faiss_dimension = 384

            idx = FAISSIndex()
            # IVFFlat needs training before search; use flat index fallback
            idx.index = faiss.IndexFlatIP(384)
            results = idx.search([0.0] * 384, top_k=5)
            assert results == []

    def test_bulk_add_and_search(self):
        import faiss
        from app.vector_index import FAISSIndex

        with patch("app.vector_index.settings") as mock_settings, \
             patch("app.vector_index.os.path.exists", return_value=False), \
             patch("app.vector_index.os.makedirs"), \
             patch.object(FAISSIndex, "save"):
            mock_settings.faiss_index_path = "/tmp/test.index"
            mock_settings.faiss_dimension = 4

            idx = FAISSIndex()
            idx.index = faiss.IndexFlatIP(4)

            vecs = np.random.rand(10, 4).astype(np.float32)
            # Normalize
            vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
            ids = [f"article_{i}" for i in range(10)]
            idx.bulk_add(ids, vecs.tolist())

            results = idx.search(vecs[0].tolist(), top_k=3)
            assert len(results) <= 3
            assert results[0][0] == "article_0"  # Most similar to itself
