"""On-device embedding encoder using BAAI/bge-small-en-v1.5."""
import logging
import asyncio
from pathlib import Path
from typing import Optional
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config.settings import settings
from src.common.exceptions import EmbeddingError
from src.common.hashing import compute_text_hash

logger = logging.getLogger(__name__)


class EmbeddingEncoder:
    """
    On-device embedding encoder using BAAI/bge-small-en-v1.5.
    Generates 384-dimensional embeddings for text chunks.
    Includes LRU cache keyed on SHA-256 content hash.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize embedding encoder.
        
        Args:
            model_name: HuggingFace model name (defaults to settings)
        """
        self.model_name = model_name or settings.embed_model
        self.model: Optional[SentenceTransformer] = None
        self._cache: dict[str, np.ndarray] = {}
        self._cache_size = settings.embed_cache_size
    
    def _load_model(self) -> None:
        """Load the sentence-transformers model (lazy loading)."""
        if self.model is None:
            try:
                logger.info(f"Loading embedding model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise EmbeddingError(f"Failed to load embedding model: {e}") from e
    
    def _get_from_cache(self, text_hash: str) -> Optional[np.ndarray]:
        """
        Get embedding from cache.
        
        Args:
            text_hash: SHA-256 hash of text
            
        Returns:
            Cached embedding or None
        """
        return self._cache.get(text_hash)
    
    def _add_to_cache(self, text_hash: str, embedding: np.ndarray) -> None:
        """
        Add embedding to cache with LRU eviction.
        
        Args:
            text_hash: SHA-256 hash of text
            embedding: Embedding vector
        """
        # Simple LRU: if cache is full, remove oldest entry
        if len(self._cache) >= self._cache_size:
            # Remove first (oldest) entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[text_hash] = embedding
    
    def encode(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            use_cache: Whether to use cache
            
        Returns:
            384-dimensional numpy array embedding
        """
        self._load_model()
        
        # Check cache
        text_hash = compute_text_hash(text)
        if use_cache:
            cached = self._get_from_cache(text_hash)
            if cached is not None:
                logger.debug(f"Cache hit for text hash {text_hash[:8]}")
                return cached
        
        # Generate embedding
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,  # Normalize for cosine similarity
                show_progress_bar=False,
            )
            
            # Ensure correct dimensions
            if embedding.shape[-1] != 384:
                raise EmbeddingError(
                    f"Embedding dimension mismatch: expected 384, got {embedding.shape[-1]}"
                )
            
            # Add to cache
            if use_cache:
                self._add_to_cache(text_hash, embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}") from e
    
    async def encode_async(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Async wrapper for encode.
        
        Args:
            text: Text to embed
            use_cache: Whether to use cache
            
        Returns:
            384-dimensional numpy array embedding
        """
        # Run in thread pool since sentence-transformers is synchronous
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.encode, text, use_cache)
    
    def encode_batch(
        self,
        texts: list[str],
        use_cache: bool = True,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            use_cache: Whether to use cache
            show_progress: Whether to show progress bar
            
        Returns:
            Numpy array of embeddings (n_texts, 384)
        """
        self._load_model()
        
        # Check cache for each text
        embeddings = []
        texts_to_encode = []
        indices_to_encode = []
        
        for i, text in enumerate(texts):
            text_hash = compute_text_hash(text)
            if use_cache:
                cached = self._get_from_cache(text_hash)
                if cached is not None:
                    embeddings.append((i, cached))
                    continue
            
            texts_to_encode.append(text)
            indices_to_encode.append(i)
        
        # Encode uncached texts
        if texts_to_encode:
            try:
                new_embeddings = self.model.encode(
                    texts_to_encode,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=show_progress,
                )
                
                # Add to cache and results
                for idx, text, embedding in zip(
                    indices_to_encode, texts_to_encode, new_embeddings
                ):
                    text_hash = compute_text_hash(text)
                    if use_cache:
                        self._add_to_cache(text_hash, embedding)
                    embeddings.append((idx, embedding))
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                raise EmbeddingError(f"Batch embedding generation failed: {e}") from e
        
        # Sort by original index and return
        embeddings.sort(key=lambda x: x[0])
        return np.array([emb for _, emb in embeddings])
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            "size": len(self._cache),
            "max_size": self._cache_size,
            "utilization": len(self._cache) / self._cache_size,
        }
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")


# Global encoder instance
embedding_encoder = EmbeddingEncoder()