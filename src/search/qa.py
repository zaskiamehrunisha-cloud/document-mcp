"""Q&A service with grounded answers and citations."""
import logging
from typing import Optional

from src.search.hybrid import hybrid_search
from src.llm.client import llm_client
from src.common.audit import create_qa_audit
from src.common.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class QAService:
    """
    Q&A service that combines hybrid retrieval with LLM answer generation.
    Returns grounded answers with verifiable citations.
    """
    
    def __init__(self):
        """Initialize Q&A service."""
        self.default_limit = 5  # Number of chunks to retrieve
    
    async def ask(
        self,
        query: str,
        discipline: Optional[str] = None,
        document_ids: Optional[list[int]] = None,
    ) -> dict:
        """
        Answer a question using retrieved document context.
        
        Args:
            query: User's question
            discipline: Optional discipline filter
            document_ids: Optional document ID filter
            
        Returns:
            Dictionary with answer, citations, and confidence
        """
        try:
            # Step 1: Retrieve relevant context
            context_chunks = await hybrid_search.search_with_parent_expansion(
                query=query,
                limit=self.default_limit,
                discipline=discipline,
                document_ids=document_ids,
            )
            
            if not context_chunks:
                return {
                    "answer": "I cannot find this information in the provided documents.",
                    "confidence": "Low",
                    "citations": [],
                    "query": query,
                }
            
            # Step 2: Generate answer using LLM
            llm_result = await llm_client.generate_answer(query, context_chunks)
            
            # Step 3: Prepare result
            result = {
                "answer": llm_result["answer"],
                "confidence": llm_result["confidence"],
                "citations": llm_result["citations"],
                "query": query,
                "context_chunks_used": len(context_chunks),
            }
            
            # Step 4: Create audit log
            cited_doc_ids = [c["document_number"] for c in llm_result["citations"]]
            retrieved_chunk_ids = [c["chunk"]["id"] for c in context_chunks if "chunk" in c]
            
            audit = create_qa_audit(
                query_text=query,
                answer=llm_result["answer"],
                confidence_level=llm_result["confidence"],
                cited_document_ids=cited_doc_ids,
                retrieved_chunk_ids=retrieved_chunk_ids,
                model_version="llama3.1-8b",
            )
            audit.log()
            
            logger.info(
                f"Q&A complete for query '{query[:50]}...': "
                f"{llm_result['confidence']} confidence, {len(llm_result['citations'])} citations"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Q&A failed: {e}", exc_info=True)
            raise DatabaseError(f"Q&A failed: {e}") from e
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        discipline: Optional[str] = None,
        document_ids: Optional[list[int]] = None,
    ) -> dict:
        """
        Perform search without LLM answer generation.
        
        Args:
            query: Search query
            limit: Maximum results
            discipline: Optional discipline filter
            document_ids: Optional document ID filter
            
        Returns:
            Dictionary with search results
        """
        try:
            results = await hybrid_search.search(
                query=query,
                limit=limit,
                discipline=discipline,
                document_ids=document_ids,
            )
            
            return {
                "query": query,
                "results": results,
                "total": len(results),
            }
        
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise DatabaseError(f"Search failed: {e}") from e


# Global Q&A service instance
qa_service = QAService()