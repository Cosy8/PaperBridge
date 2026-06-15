"""
FAISS vector index management.
Uses IVFFlat for efficient approximate nearest neighbor search at scale.
"""
import json
import os

import faiss
import numpy as np
from loguru import logger

from app.config import settings

# IVFFlat needs at least this many training vectors (one per cluster) before it
# can be trained. Below this threshold we use an exact IndexFlatIP, which needs
# no training and gives identical (in fact exact) results on a small corpus.
IVF_NLIST = 100


class FAISSIndex:
    def __init__(self):
        self.index_path = settings.faiss_index_path
        self.dimension = settings.faiss_dimension
        self.id_map: list[str] = []
        # Keep raw vectors so we can rebuild/retrain when the corpus crosses the
        # IVF training threshold. (The persisted .index file alone cannot be
        # retrained into a different index type.)
        self._vectors: list[list[float]] = []
        self.index = self._load_or_create()

    @property
    def _id_map_path(self) -> str:
        return self.index_path + ".ids.json"

    def _load_or_create(self) -> faiss.Index:
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        if os.path.exists(self.index_path):
            logger.info(f"Loading FAISS index from {self.index_path}")
            index = faiss.read_index(self.index_path)
            # Restore the id_map and raw vectors so subsequent adds can rebuild.
            if os.path.exists(self._id_map_path):
                with open(self._id_map_path) as f:
                    self.id_map = json.load(f)
            if index.ntotal:
                if isinstance(index, faiss.IndexIVFFlat):
                    index.make_direct_map()
                self._vectors = index.reconstruct_n(0, index.ntotal).tolist()
            return index
        logger.info(f"Creating new FAISS FlatIP index (dim={self.dimension})")
        # Start exact; promote to IVFFlat once the corpus is large enough to train.
        return faiss.IndexFlatIP(self.dimension)

    def _build_index(self) -> None:
        """(Re)build the underlying index from the buffered vectors, choosing the
        index type based on corpus size."""
        vecs = np.array(self._vectors, dtype=np.float32)
        if len(self._vectors) >= IVF_NLIST:
            quantizer = faiss.IndexFlatIP(self.dimension)
            index = faiss.IndexIVFFlat(
                quantizer, self.dimension, IVF_NLIST, faiss.METRIC_INNER_PRODUCT
            )
            index.train(vecs)
            index.add(vecs)
        else:
            index = faiss.IndexFlatIP(self.dimension)
            index.add(vecs)
        self.index = index

    def add(self, article_id: str, embedding: list[float]) -> None:
        self._vectors.append(embedding)
        self.id_map.append(article_id)
        self._build_index()
        self.save()

    def bulk_add(self, article_ids: list[str], embeddings: list[list[float]]) -> None:
        """Add many vectors at once — preferred for training IVF index accurately."""
        self._vectors.extend(embeddings)
        self.id_map.extend(article_ids)
        self._build_index()
        self.save()

    def search(self, query_embedding: list[float], top_k: int = 10) -> list[tuple[str, float]]:
        """Return top_k article IDs with similarity scores."""
        vec = np.array([query_embedding], dtype=np.float32)
        if isinstance(self.index, faiss.IndexIVFFlat):
            self.index.nprobe = 10  # Search 10 nearest clusters
        distances, indices = self.index.search(vec, top_k)
        results = []
        for dist, idx in zip(distances[0], indices[0], strict=False):
            if idx != -1 and idx < len(self.id_map):
                results.append((self.id_map[idx], float(dist)))
        return results

    def save(self) -> None:
        faiss.write_index(self.index, self.index_path)
        # Persist the id_map alongside the index so the API process can map FAISS
        # positions back to article IDs (the .index file stores vectors only).
        with open(self._id_map_path, "w") as f:
            json.dump(self.id_map, f)
        logger.debug(f"FAISS index saved ({self.index.ntotal} vectors)")


_faiss_index: FAISSIndex | None = None


def get_faiss_index() -> FAISSIndex:
    global _faiss_index
    if _faiss_index is None:
        _faiss_index = FAISSIndex()
    return _faiss_index
