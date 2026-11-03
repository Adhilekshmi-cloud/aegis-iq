"""FAISS vector index service for fast dense semantic retrieval over document chunks."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.config import settings
from app.retrieval.embeddings import EMBEDDING_DIM

try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchResult:
    """Result of a nearest-neighbor vector search."""
    chunk_id: str
    faiss_id: int
    score: float  # Cosine similarity (1.0 = identical)
    distance: float  # Raw distance


class FAISSIndexService:
    """Manages dense vector indexing and nearest-neighbor search for document chunks."""

    def __init__(self, dimension: int = EMBEDDING_DIM):
        """Initialize FAISS index service.

        Args:
            dimension: Dimensionality of vectors (default: 384).
        """
        self.dimension = dimension
        self._id_to_chunk: Dict[int, str] = {}
        self._chunk_to_id: Dict[str, int] = {}
        self._numpy_vectors: Optional[np.ndarray] = None  # Fallback store

        if _FAISS_AVAILABLE:
            # Inner Product index on unit vectors computes cosine similarity
            self._index = faiss.IndexFlatIP(self.dimension)
        else:
            self._index = None
            logger.warning("FAISS library not installed. Operating with numpy fallback.")

    @property
    def total_vectors(self) -> int:
        """Return the count of indexed items."""
        if self._index is not None:
            return self._index.ntotal
        elif self._numpy_vectors is not None:
            return len(self._numpy_vectors)
        return 0

    def add_vectors(self, chunk_ids: List[str], embeddings: np.ndarray) -> None:
        """Add dense vectors and map them to chunk_ids.

        Args:
            chunk_ids: List of unique chunk IDs.
            embeddings: 2D array of float32 embeddings (N, dimension).
        """
        if len(chunk_ids) == 0 or embeddings.shape[0] == 0:
            return

        if len(chunk_ids) != embeddings.shape[0]:
            raise ValueError(
                f"Mismatch: {len(chunk_ids)} chunk IDs but {embeddings.shape[0]} embeddings."
            )

        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_embs = (embeddings / norms).astype(np.float32)

        start_id = self.total_vectors

        if self._index is not None:
            self._index.add(normalized_embs)
            for idx, c_id in enumerate(chunk_ids):
                fid = start_id + idx
                self._id_to_chunk[fid] = c_id
                self._chunk_to_id[c_id] = fid
        else:
            # Fallback numpy storage
            if self._numpy_vectors is None:
                self._numpy_vectors = normalized_embs
            else:
                self._numpy_vectors = np.vstack([self._numpy_vectors, normalized_embs])

            for idx, c_id in enumerate(chunk_ids):
                fid = start_id + idx
                self._id_to_chunk[fid] = c_id
                self._chunk_to_id[c_id] = fid

        logger.info("Added %d vectors to FAISS index. Total: %d", len(chunk_ids), self.total_vectors)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[VectorSearchResult]:
        """Search for top_k most similar chunks to query vector.

        Args:
            query_embedding: 1D or 2D vector representing the query.
            top_k: Number of nearest neighbors to retrieve.

        Returns:
            List of VectorSearchResult ordered by similarity descending.
        """
        if self.total_vectors == 0:
            return []

        # Ensure 2D shape (1, dimension)
        if query_embedding.ndim == 1:
            q_vec = query_embedding.reshape(1, -1).astype(np.float32)
        else:
            q_vec = query_embedding.astype(np.float32)

        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm

        actual_k = min(top_k, self.total_vectors)
        results: List[VectorSearchResult] = []

        if self._index is not None:
            distances, indices = self._index.search(q_vec, actual_k)
            for dist, idx in zip(distances[0], indices[0]):
                if idx in self._id_to_chunk:
                    c_id = self._id_to_chunk[idx]
                    results.append(
                        VectorSearchResult(
                            chunk_id=c_id,
                            faiss_id=int(idx),
                            score=float(dist),
                            distance=float(1.0 - dist),
                        )
                    )
        else:
            # Fallback numpy dot-product search
            sims = np.dot(self._numpy_vectors, q_vec.T).flatten()
            top_indices = np.argsort(sims)[::-1][:actual_k]
            for idx in top_indices:
                dist = sims[idx]
                c_id = self._id_to_chunk.get(idx, f"chunk_{idx}")
                results.append(
                    VectorSearchResult(
                        chunk_id=c_id,
                        faiss_id=int(idx),
                        score=float(dist),
                        distance=float(1.0 - dist),
                    )
                )

        return results

    def save(self, directory: Optional[Path] = None) -> None:
        """Save FAISS index and metadata mappings to disk.

        Args:
            directory: Directory path to persist index.
        """
        target_dir = directory or Path(settings.FAISS_INDEX_PATH)
        target_dir.mkdir(parents=True, exist_ok=True)

        meta_path = target_dir / "index_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "dimension": self.dimension,
                    "id_to_chunk": {str(k): v for k, v in self._id_to_chunk.items()},
                },
                f,
                indent=2,
            )

        if self._index is not None and _FAISS_AVAILABLE:
            faiss_file = target_dir / "index.faiss"
            faiss.write_index(self._index, str(faiss_file))
            logger.info("Saved FAISS index to %s", faiss_file)
        elif self._numpy_vectors is not None:
            npy_file = target_dir / "vectors.npy"
            np.save(npy_file, self._numpy_vectors)
            logger.info("Saved fallback vector matrix to %s", npy_file)

    def load(self, directory: Optional[Path] = None) -> bool:
        """Load FAISS index and metadata mappings from disk.

        Args:
            directory: Directory path where index is stored.

        Returns:
            True if loaded successfully, False otherwise.
        """
        target_dir = directory or Path(settings.FAISS_INDEX_PATH)
        meta_path = target_dir / "index_meta.json"
        if not meta_path.exists():
            return False

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.dimension = data.get("dimension", EMBEDDING_DIM)
                self._id_to_chunk = {int(k): v for k, v in data.get("id_to_chunk", {}).items()}
                self._chunk_to_id = {v: k for k, v in self._id_to_chunk.items()}

            faiss_file = target_dir / "index.faiss"
            if _FAISS_AVAILABLE and faiss_file.exists():
                self._index = faiss.read_index(str(faiss_file))
                logger.info("Loaded FAISS index with %d vectors", self._index.ntotal)
                return True

            npy_file = target_dir / "vectors.npy"
            if npy_file.exists():
                self._numpy_vectors = np.load(npy_file)
                logger.info("Loaded fallback vector matrix with %d vectors", len(self._numpy_vectors))
                return True

        except Exception as exc:
            logger.error("Failed to load vector index: %s", exc)
            return False

        return False
