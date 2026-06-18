"""
Document search for DOCINTEL.
Performs pgvector similarity search and SQL lookup.
"""

from typing import Any

from docintel.common.logging import get_logger
from docintel.db.repositories.chunks import ChunkRepository
from docintel.db.repositories.documents import DocumentRepository
from docintel.embeddings.local_embedder import get_embedder

logger = get_logger(__name__)


class DocumentSearch:
    """
    Searches documents using pgvector similarity and SQL lookup.
    """
    
    def __init__(self):
        """Initialize the search service."""
        self.embedder = get_embedder()
        self.chunk_repo = ChunkRepository()
        self.doc_repo = DocumentRepository()
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        discipline: str | None = None,
        document_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Search for relevant document chunks.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            discipline: Optional discipline filter
            document_ids: Optional list of document IDs to search within
            
        Returns:
            Search results with chunks and metadata
        """
        try:
            # Embed the query
            query_embedding = await self.embedder.embed_text(query)
            
            # Search pgvector
            chunks = await self.chunk_repo.search_similar(
                embedding=query_embedding,
                top_k=top_k,
                discipline=discipline,
                document_ids=document_ids,
            )
            
            # Enrich with document metadata
            results = []
            for chunk in chunks:
                doc = await self.doc_repo.get_by_id(chunk["document_id"])
                if doc:
                    results.append({
                        "chunk_text": chunk["chunk_text"],
                        "page_or_sheet": chunk["page_or_sheet"],
                        "score": chunk["score"],
                        "document": {
                            "id": doc.id,
                            "document_number": doc.document_number,
                            "title": doc.title,
                            "discipline": doc.discipline,
                        },
                    })
            
            logger.info(
                "Search complete",
                extra={
                    "query_length": len(query),
                    "results_found": len(results),
                    "top_k": top_k,
                },
            )
            
            return {
                "query": query,
                "results": results,
                "total_found": len(results),
            }
            
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
    
    async def search_by_document_number(
        self,
        document_number: str,
    ) -> dict[str, Any] | None:
        """
        Search for a document by its document number.
        
        Args:
            document_number: Document number to search for
            
        Returns:
            Document metadata or None
        """
        try:
            doc = await self.doc_repo.get_by_document_number(document_number)
            if not doc:
                return None
            
            return {
                "id": doc.id,
                "document_number": doc.document_number,
                "title": doc.title,
                "revision": doc.revision,
                "discipline": doc.discipline,
                "contract_number": doc.contract_number,
            }
        except Exception as e:
            logger.error(f"Document number search failed: {str(e)}")
            return None
    
    async def get_document_chunks(
        self,
        document_id: int,
        page_or_sheet: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get all chunks for a document.
        
        Args:
            document_id: Database ID of the document
            page_or_sheet: Optional page/sheet number filter
            
        Returns:
            List of chunks
        """
        try:
            chunks = await self.chunk_repo.get_by_document(
                document_id=document_id,
                page_or_sheet=page_or_sheet,
            )
            
            return [
                {
                    "chunk_text": c.chunk_text,
                    "page_or_sheet": c.page_or_sheet,
                    "metadata": c.chunk_metadata,
                }
                for c in chunks
            ]
        except Exception as e:
            logger.error(f"Failed to get document chunks: {str(e)}")
            return []
    
    async def get_search_stats(self) -> dict[str, Any]:
        """
        Get search statistics.
        
        Returns:
            Dictionary with search statistics
        """
        try:
            total_chunks = await self.chunk_repo.count_all()
            return {
                "total_chunks": total_chunks,
                "embedding_model": self.embedder.model_name,
                "embedding_dimension": self.embedder.embedding_dim,
            }
        except Exception as e:
            logger.error(f"Failed to get search stats: {str(e)}")
            return {}


# Global search instance
_search: DocumentSearch | None = None


def get_search() -> DocumentSearch:
    """Get the global search instance."""
    global _search
    if _search is None:
        _search = DocumentSearch()
    return _search