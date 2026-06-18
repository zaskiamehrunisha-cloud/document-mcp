"""
Local embedding model for DOCINTEL.
Generates embeddings using sentence-transformers BGE models.
Runs entirely on-device with no network calls.
"""

import asyncio
from functools import partial
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from docintel.common.exceptions import EmbeddingError
from docintel.common.logging import get_logger
from docintel.config.settings import settings

logger = get_logger(__name__)


class LocalEmbedder:
    """
    On-device embedding model using sentence-transformers.
    Generates embeddings for RAG retrieval.
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        normalize: Optional[bool] = None,
    ):
        """
        Initialize the local embedder.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to run on ("cpu", "cuda", "mps")
            normalize: Whether to normalize embeddings
        """
        self.model_name = model_name or settings.embedding_model
        self.device = device or settings.embedding_device
        self.normalize = normalize if normalize is not None else True
        
        self._model: Optional[SentenceTransformer] = None
        self._dimension: Optional[int] = None
    
    def _load_model(self) -> SentenceTransformer:
        """Load the embedding model (lazy loading)."""
        if self._model is None:
            logger.info(
                "Loading embedding model",
                extra={"model": self.model_name, "device": self.device},
            )
            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                )
                # Get the actual dimension from the model
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(
                    "Embedding model loaded",
                    extra={"model": self.model_name, "dimension": self._dimension},
                )
            except Exception as e:
                error_msg = f"Failed to load embedding model {self.model_name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise EmbeddingError(error_msg) from e
        return self._model
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension or settings.embedding_dimension
    
    def embed_single(self, text: str) -> List[float]:
        """
        Embed a single text string.
        
        Args:
            text: The text to embed
            
        Returns:
            Embedding vector as a list of floats
        """
        model = self._load_model()
        
        try:
            embedding = model.encode(
                text,
                normalize_embeddings=self.normalize,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return embedding.tolist()
        except Exception as e:
            error_msg = f"Failed to embed text: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise EmbeddingError(error_msg) from e
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Embed a batch of texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
            
        Returns:
            List of embedding vectors
        """
        model = self._load_model()
        batch_size = batch_size or settings.chunk_size
        
        try:
            embeddings = model.encode(
                texts,
                normalize_embeddings=self.normalize,
                convert_to_numpy=True,
                batch_size=batch_size,
                show_progress_bar=show_progress,
            )
            return embeddings.tolist()
        except Exception as e:
            error_msg = f"Failed to embed batch: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise EmbeddingError(error_msg) from e
    
    async def embed_single_async(self, text: str) -> List[float]:
        """
        Async wrapper for embedding a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            Embedding vector as a list of floats
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_single, text)
    
    async def embed_batch_async(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        """
        Async wrapper for batch embedding.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for encoding
            
        Returns:
            List of embedding vectors
        """
        loop = asyncio.get_event_loop()
        func = partial(self.embed_batch, texts=texts, batch_size=batch_size)
        return await loop.run_in_executor(None, func)
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        a = np.array(embedding1)
        b = np.array(embedding2)
        
        if self.normalize:
            # If embeddings are normalized, cosine similarity is just dot product
            return float(np.dot(a, b))
        else:
            # Otherwise compute cosine similarity
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))


# Global embedder instance
_embedder: Optional[LocalEmbedder] = None


def get_embedder() -> LocalEmbedder:
    """Get the global embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = LocalEmbedder()
    return _embedder