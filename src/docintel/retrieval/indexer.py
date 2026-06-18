"""
Document indexer for DOCINTEL.
Embeds document chunks and stores them in pgvector.
"""

from typing import Any

from docintel.common.logging import get_logger
from docintel.db.repositories.chunks import ChunkRepository
from docintel.embeddings.local_embedder import get_embedder
from docintel.retrieval.chunker import get_chunker

logger = get_logger(__name__)


class DocumentIndexer:
    """
    Indexes documents by embedding chunks and storing in pgvector.
    """
    
    def __init__(self):
        """Initialize the indexer."""
        self.embedder = get_embedder()
        self.chunk_repo = ChunkRepository()
        self.chunker = get_chunker()
    
    async def index_document(
        self,
        document_id: int,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Index a document by chunking, embedding, and storing.
        
        Args:
            document_id: Database ID of the document
            text: Full document text
            metadata: Optional metadata
            
        Returns:
            Number of chunks indexed
        """
        try:
            # Chunk the document
            chunks = self.chunker.chunk_document(text, document_id, metadata)
            
            if not chunks:
                logger.warning(f"No chunks generated for document {document_id}")
                return 0
            
            # Embed all chunks
            chunk_texts = [c["chunk_text"] for c in chunks]
            embeddings = await self.embedder.embed_batch(chunk_texts)
            
            # Store chunks with embeddings
            for chunk, embedding in zip(chunks, embeddings):
                await self.chunk_repo.create(
                    document_id=chunk["document_id"],
                    page_or_sheet=chunk["page_or_sheet"],
                    chunk_text=chunk["chunk_text"],
                    embedding=embedding,
                    chunk_metadata=chunk.get("chunk_metadata", {}),
                )
            
            logger.info(
                "Document indexed",
                extra={
                    "document_id": document_id,
                    "chunks": len(chunks),
                },
            )
            
            return len(chunks)
            
        except Exception as e:
            error_msg = f"Failed to index document {document_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
    
    async def index_documents_batch(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, int]:
        """
        Index multiple documents in batch.
        
        Args:
            documents: List of dicts with 'document_id', 'text', and optional 'metadata'
            
        Returns:
            Dictionary with 'total_chunks' and 'documents_indexed'
        """
        total_chunks = 0
        documents_indexed = 0
        
        for doc in documents:
            try:
                chunks = await self.index_document(
                    document_id=doc["document_id"],
                    text=doc["text"],
                    metadata=doc.get("metadata"),
                )
                total_chunks += chunks
                documents_indexed += 1
            except Exception as e:
                logger.error(
                    f"Failed to index document {doc.get('document_id')}: {str(e)}",
                    exc_info=True,
                )
        
        logger.info(
            "Batch indexing complete",
            extra={
                "documents_indexed": documents_indexed,
                "total_chunks": total_chunks,
            },
        )
        
        return {
            "total_chunks": total_chunks,
            "documents_indexed": documents_indexed,
        }
    
    async def delete_document_index(self, document_id: int) -> bool:
        """
        Delete all chunks for a document.
        
        Args:
            document_id: Database ID of the document
            
        Returns:
            True if successful
        """
        try:
            await self.chunk_repo.delete_by_document(document_id)
            logger.info(f"Deleted index for document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index for document {document_id}: {str(e)}")
            return False
    
    async def get_index_stats(self) -> dict[str, Any]:
        """
        Get statistics about the index.
        
        Returns:
            Dictionary with index statistics
        """
        try:
            total_chunks = await self.chunk_repo.count_all()
            document_count = await self.chunk_repo.count_documents()
            
            return {
                "total_chunks": total_chunks,
                "indexed_documents": document_count,
                "embedding_model": self.embedder.model_name,
                "embedding_dimension": self.embedder.embedding_dim,
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}")
            return {}


# Global indexer instance
_indexer: DocumentIndexer | None = None


def get_indexer() -> DocumentIndexer:
    """Get the global indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = DocumentIndexer()
    return _indexer