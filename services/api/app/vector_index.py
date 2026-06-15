"""FAISS index client shared by API and recommender service."""
import json
import os

import faiss
import numpy as np
from loguru import logger

from app.config import settings

_faiss_index = None


class FAISSIndex:
    def __init__(self):
        self.index_path = settings.faiss_index_path
        self.dimension = settings.faiss_dimension
        self.id_map: list[str] = []
        self.index = self._load()

    def _load(self):
        if os.path.exists(self.index_path):
            logger.info(f"Loading FAISS index from {self.index_path}")
            id_map_path = self.index_path + ".ids.json"
            if os.path.exists(id_map_path):
                with open(id_map_path) as f:
                    self.id_map = json.load(f)
            else:
                logger.warning("FAISS id_map sidecar not found — semantic results will be empty")
            return faiss.read_index(self.index_path)
        logger.warning("FAISS index not found — returning empty index")
        return faiss.IndexFlatIP(self.dimension)

    def search(self, query_embedding: list[float], top_k: int = 10) -> list[tuple[str, float]]:
        if self.index.ntotal == 0:
            return []
        vec = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(vec, min(top_k, self.index.ntotal))
        return [
            (self.id_map[idx], float(dist))
            for dist, idx in zip(distances[0], indices[0], strict=False)
            if idx != -1 and idx < len(self.id_map)
        ]


def get_faiss_index() -> FAISSIndex:
    global _faiss_index
    if _faiss_index is None:
        _faiss_index = FAISSIndex()
    return _faiss_index
