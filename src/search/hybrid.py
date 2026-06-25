"""Hybrid search combining pgvector cosine similarity and SQL full-text search."""
import logging
import asyncio
from typing import Optional
from datetime import datetime

import numpy as np
from sqlalchemy import select, func, text
from sqlalchemy.sql import ClauseElement

from src.db.models import DocumentChunk, ReferenceDocument
from src.db.session import async_session_factory
from src.embeddings.encoder import embedding_encoder
from src.common.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class HybridSearch:
    """
    Hybrid search combining vector similarity and full-text search.
    Merges and ranks results from both pgvector cosine distance and
    SQL full-text search for optimal recall on domain-specific content.
    """
    
    def __init__(self):
        """Initialize hybrid search."""
        self.vector_weight = 0.6  # Weight for vector similarity
        self.text_weight = 0.4    # Weight for full-text search
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        discipline: Optional[str] = None,
        document_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """
        Perform hybrid search for relevant document chunks.
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            discipline: Optional discipline filter
            document_ids: Optional list of document IDs to search within
            
        Returns:
            List of search results with chunks and metadata
        """
        try:
            # Generate query embedding
            query_embedding = embedding_encoder.encode(query, use_cache=True)
            
            # Run both searches concurrently
            vector_results, text_results = await asyncio.gather(
                self._vector_search(query_embedding, limit * 2, discipline, document_ids),
                self._text_search(query, limit * 2, discipline, document_ids),
            )
            
            # Merge and rank results
            merged_results = self._merge_results(
                vector_results,
                text_results,
                limit,
            )
            
            logger.info(
                f"Hybrid search for '{query[:50]}...': "
                f"{len(vector_results)} vector + {len(text_results)} text → {len(merged_results)} merged"
            )
            
            return merged_results
        
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}", exc_info=True)
            raise DatabaseError(f"Search failed: {e}") from e
    
    async def _vector_search(
        self,
        query_embedding: np.ndarray,
        limit: int,
        discipline: Optional[str] = None,
        document_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """
        Perform vector similarity search using pgvector.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum results
            discipline: Optional discipline filter
            document_ids: Optional document ID filter
            
        Returns:
            List of search results
        """
        try:
            from pgvector.sqlalchemy import register_vector_async
            
            async with async_session_factory() as session:
                # Build query
                query = (
                    select(
                        DocumentChunk,
                        ReferenceDocument,
                        func.cosine_distance(DocumentChunk.embedding, query_embedding).label("distance"),
                    )
                    .join(ReferenceDocument, DocumentChunk.document_id == ReferenceDocument.id)
                    .where(DocumentChunk.level == "child")
                    .where(DocumentChunk.embedding != None)
                )
                
                # Apply filters
                if discipline:
                    query = query.where(ReferenceDocument.discipline == discipline)
                
                if document_ids:
                    query = query.where(DocumentChunk.document_id.in_(document_ids))
                
                # Order by cosine distance and limit
                query = query.order_by("distance").limit(limit)
                
                # Execute
                result = await session.execute(query)
                rows = result.all()
                
                # Format results
                results = []
                for chunk, doc, distance in rows:
                    similarity = 1 - distance  # Convert distance to similarity
                    results.append({
                        "chunk": {
                            "id": chunk.id,
                            "content": chunk.content,
                            "level": chunk.level,
                            "token_count": chunk.token_count,
                            "page_numbers": [],  # Could be extracted from content
                        },
                        "document": {
                            "id": doc.id,
                            "document_number": doc.document_number,
                            "title": doc.title,
                            "discipline": doc.discipline,
                            "revision": doc.revision,
                            "issue_status": doc.issue_status,
                        },
                        "score": similarity,
                        "search_type": "vector",
                    })
                
                return results
        
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def _text_search(
        self,
        query: str,
        limit: int,
        discipline: Optional[str] = None,
        document_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """
        Perform full-text search using PostgreSQL tsvector.
        
        Args:
            query: Search query text
            limit: Maximum results
            discipline: Optional discipline filter
            document_ids: Optional document ID filter
            
        Returns:
            List of search results
        """
        try:
            async with async_session_factory() as session:
                # Build tsquery from query
                # Convert query to tsquery format
                tsquery = func.plainto_tsquery("english", query)
                
                # Build query
                query_sql = (
                    select(
                        DocumentChunk,
                        ReferenceDocument,
                        func.ts_rank(DocumentChunk.tsv, tsquery).label("rank"),
                    )
                    .join(ReferenceDocument, DocumentChunk.document_id == ReferenceDocument.id)
                    .where(DocumentChunk.level == "child")
                    .where(DocumentChunk.tsv != None)
                    .where(DocumentChunk.tsv.op("@@")(tsquery))
                )
                
                # Apply filters
                if discipline:
                    query_sql = query_sql.where(ReferenceDocument.discipline == discipline)
                
                if document_ids:
                    query_sql = query_sql.where(DocumentChunk.document_id.in_(document_ids))
                
                # Order by rank and limit
                query_sql = query_sql.order_by(text("rank DESC")).limit(limit)
                
                # Execute
                result = await session.execute(query_sql)
                rows = result.all()
                
                # Format results
                results = []
                for chunk, doc, rank in rows:
                    results.append({
                        "chunk": {
                            "id": chunk.id,
                            "content": chunk.content,
                            "level": chunk.level,
                            "token_count": chunk.token_count,
                            "page_numbers": [],
                        },
                        "document": {
                            "id": doc.id,
                            "document_number": doc.document_number,
                            "title": doc.title,
                            "discipline": doc.discipline,
                            "revision": doc.revision,
                            "issue_status": doc.issue_status,
                        },
                        "score": min(rank, 1.0),  # Normalize rank to 0-1
                        "search_type": "text",
                    })
                
                return results
        
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []
    
    def _merge_results(
        self,
        vector_results: list[dict],
        text_results: list[dict],
        limit: int,
    ) -> list[dict]:
        """
        Merge and rank results from vector and text search.
        
        Args:
            vector_results: Results from vector search
            text_results: Results from text search
            limit: Maximum results to return
            
        Returns:
            Merged and ranked results
        """
        # Create a map to combine scores
        chunk_scores: dict[int, dict] = {}
        
        # Add vector results
        for result in vector_results:
            chunk_id = result["chunk"]["id"]
            chunk_scores[chunk_id] = {
                "result": result,
                "vector_score": result["score"] * self.vector_weight,
                "text_score": 0.0,
            }
        
        # Add/merge text results
        for result in text_results:
            chunk_id = result["chunk"]["id"]
            text_score = result["score"] * self.text_weight
            
            if chunk_id in chunk_scores:
                # Merge scores
                chunk_scores[chunk_id]["text_score"] = text_score
            else:
                # Add new result
                chunk_scores[chunk_id] = {
                    "result": result,
                    "vector_score": 0.0,
                    "text_score": text_score,
                }
        
        # Calculate combined scores and sort
        scored_results = []
        for chunk_id, scores in chunk_scores.items():
            combined_score = scores["vector_score"] + scores["text_score"]
            result = scores["result"]
            result["score"] = combined_score
            result["search_type"] = "hybrid"
            scored_results.append(result)
        
        # Sort by combined score descending
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top results
        return scored_results[:limit]
    
    async def search_with_parent_expansion(
        self,
        query: str,
        limit: int = 10,
        discipline: Optional[str] = None,
        document_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """
        Search and expand results to include parent chunks.
        
        Args:
            query: Search query text
            limit: Maximum number of child results
            discipline: Optional discipline filter
            document_ids: Optional document ID filter
            
        Returns:
            List of results with parent context
        """
        # Perform hybrid search
        child_results = await self.search(query, limit, discipline, document_ids)
        
        # Expand to include parent chunks
        expanded_results = []
        parent_ids_seen = set()
        
        for result in child_results:
            chunk = result["chunk"]
            
            # Add child result
            expanded_results.append(result)
            
            # Find and add parent chunk
            parent_id = chunk.get("metadata", {}).get("parent_index")
            if parent_id is not None and parent_id not in parent_ids_seen:
                parent_chunk = await self._get_parent_chunk(
                    chunk["id"],
                    result["document"]["id"],
                )
                
                if parent_chunk:
                    parent_ids_seen.add(parent_id)
                    expanded_results.append({
                        "chunk": parent_chunk,
                        "document": result["document"],
                        "score": result["score"],
                        "search_type": "parent_expansion",
                    })
        
        return expanded_results
    
    async def _get_parent_chunk(self, child_chunk_id: int, document_id: int) -> Optional[dict]:
        """
        Get parent chunk for a child chunk.
        
        Args:
            child_chunk_id: ID of child chunk
            document_id: Document ID
            
        Returns:
            Parent chunk dictionary or None
        """
        try:
            async with async_session_factory() as session:
                # Get child chunk
                result = await session.execute(
                    select(DocumentChunk).where(DocumentChunk.id == child_chunk_id)
                )
                child_chunk = result.scalar_one_or_none()
                
                if not child_chunk or not child_chunk.parent_id:
                    return None
                
                # Get parent chunk
                result = await session.execute(
                    select(DocumentChunk).where(DocumentChunk.id == child_chunk.parent_id)
                )
                parent_chunk = result.scalar_one_or_none()
                
                if not parent_chunk:
                    return None
                
                return {
                    "id": parent_chunk.id,
                    "content": parent_chunk.content,
                    "level": parent_chunk.level,
                    "token_count": parent_chunk.token_count,
                    "page_numbers": [],
                }
        
        except Exception as e:
            logger.error(f"Failed to get parent chunk: {e}")
            return None


# Global hybrid search instance
hybrid_search = HybridSearch()