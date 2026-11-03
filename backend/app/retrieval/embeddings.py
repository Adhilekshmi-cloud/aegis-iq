"""Sentence Transformers embedding service for semantic document search."""

import hashlib
import logging
from typing import List, Optional, Union

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Embedding dimension for all-MiniLM-L6-v2
EMBEDDING_DIM = 384


class EmbeddingService:
    """Service for encoding text into dense vector embeddings using Sentence Transformers."""

    _instance: Optional["EmbeddingService"] = None

    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern for shared model caching."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: Optional[str] = None):
        """Initialize the embedding model if not already initialized.

        Args:
            model_name: HuggingFace sentence-transformers model name.
        """
        if getattr(self, "_initialized", False):
            return

        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None
        self._load_model()
        self._initialized = True

    def _load_model(self) -> None:
        """Attempt to load SentenceTransformer model with fallback handling."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            logger.info("SentenceTransformer model %s loaded successfully.", self.model_name)
        except Exception as exc:
            logger.warning(
                "SentenceTransformer model %s could not be loaded (%s). "
                "Using deterministic offline pseudo-embeddings.",
                self.model_name,
                exc,
            )
            self._model = None

    def _deterministic_fallback_embed(self, text: str) -> np.ndarray:
        """Generate a deterministic normalized 384-dimensional pseudo-embedding for testing/offline use.

        Args:
            text: Input string.

        Returns:
            Unit-normalized float32 numpy vector of length EMBEDDING_DIM.
        """
        hasher = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(hasher[:4], "big")
        rng = np.random.RandomState(seed)
        vec = rng.randn(EMBEDDING_DIM).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def encode_text(self, text: str) -> np.ndarray:
        """Encode a single text string into a 1D float32 normalized embedding vector.

        Args:
            text: Text to embed.

        Returns:
            1D numpy array of shape (384,).
        """
        if not text:
            return np.zeros(EMBEDDING_DIM, dtype=np.float32)

        if self._model is not None:
            try:
                emb = self._model.encode(
                    text,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                return emb.astype(np.float32)
            except Exception as exc:
                logger.error("Error during model inference: %s. Using fallback.", exc)

        return self._deterministic_fallback_embed(text)

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of texts into a 2D float32 array of shape (N, 384).

        Args:
            texts: List of text strings.

        Returns:
            2D numpy array of shape (len(texts), 384).
        """
        if not texts:
            return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

        if self._model is not None:
            try:
                embs = self._model.encode(
                    texts,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    batch_size=32,
                    show_progress_bar=False,
                )
                return embs.astype(np.float32)
            except Exception as exc:
                logger.error("Error during batch model inference: %s. Using fallback.", exc)

        vectors = [self._deterministic_fallback_embed(t) for t in texts]
        return np.vstack(vectors).astype(np.float32)


def get_embedding_service() -> EmbeddingService:
    """Return singleton instance of EmbeddingService."""
    return EmbeddingService()
