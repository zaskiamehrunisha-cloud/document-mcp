"""
Question-answering service for DOCINTEL.
Generates grounded answers with citations using local LLM.
"""

from typing import Any

from docintel.common.logging import get_logger
from docintel.llm.local_client import get_llm_client
from docintel.retrieval.search import get_search

logger = get_logger(__name__)


class QuestionAnswering:
    """
    Generates grounded answers with citations using local LLM.
    """
    
    def __init__(self):
        """Initialize the QA service."""
        self.llm_client = get_llm_client()
        self.search = get_search()
    
    async def answer_question(
        self,
        question: str,
        top_k: int = 5,
        discipline: str | None = None,
    ) -> dict[str, Any]:
        """
        Answer a question using RAG with citations.
        
        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            discipline: Optional discipline filter
            
        Returns:
            Answer with citations
        """
        try:
            # Search for relevant chunks
            search_results = await self.search.search(
                query=question,
                top_k=top_k,
                discipline=discipline,
            )
            
            if not search_results["results"]:
                return {
                    "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
                    "citations": [],
                    "sources": [],
                    "confidence": 0.0,
                }
            
            # Build context from search results
            context_parts = []
            citations = []
            sources = []
            
            for i, result in enumerate(search_results["results"], 1):
                context_parts.append(
                    f"[Source {i}]\n"
                    f"Document: {result['document']['document_number']} - {result['document']['title']}\n"
                    f"Page/Sheet: {result['page_or_sheet']}\n"
                    f"Relevance: {result['score']:.2f}\n"
                    f"Content: {result['chunk_text']}\n"
                )
                
                citations.append({
                    "source_number": i,
                    "document_number": result["document"]["document_number"],
                    "document_title": result["document"]["title"],
                    "page_or_sheet": result["page_or_sheet"],
                    "relevance_score": result["score"],
                    "snippet": result["chunk_text"][:200] + "..." if len(result["chunk_text"]) > 200 else result["chunk_text"],
                })
                
                sources.append({
                    "document_id": result["document"]["id"],
                    "document_number": result["document"]["document_number"],
                    "title": result["document"]["title"],
                    "discipline": result["document"]["discipline"],
                })
            
            context = "\n\n".join(context_parts)
            
            # Generate answer using LLM
            prompt = self._build_qa_prompt(question, context)
            
            answer = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,  # Low temperature for factual answers
                max_tokens=1000,
            )
            
            # Calculate confidence based on search scores
            avg_score = sum(r["score"] for r in search_results["results"]) / len(search_results["results"])
            confidence = min(avg_score, 1.0)
            
            logger.info(
                "QA complete",
                extra={
                    "question_length": len(question),
                    "sources_used": len(citations),
                    "confidence": round(confidence, 2),
                },
            )
            
            return {
                "answer": answer.strip(),
                "citations": citations,
                "sources": sources,
                "confidence": confidence,
            }
            
        except Exception as e:
            error_msg = f"QA failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
    
    def _build_qa_prompt(self, question: str, context: str) -> str:
        """
        Build the QA prompt for the LLM.
        
        Args:
            question: User's question
            context: Retrieved context from documents
            
        Returns:
            Formatted prompt
        """
        return f"""You are an engineering document assistant. Answer the question based ONLY on the provided context from engineering documents.
If the context doesn't contain enough information to answer the question, say so clearly.
Always cite which source(s) you used for your answer.

Context from documents:
{context}

Question: {question}

Instructions:
1. Answer the question based strictly on the provided context
2. Be precise and technical - this is for engineering professionals
3. If you use information from a specific source, reference it (e.g., "According to Source 1...")
4. If the context doesn't contain the answer, state that clearly
5. Do not make up information or infer beyond what's in the context

Answer:"""
    
    async def answer_with_structured_lookup(
        self,
        question: str,
        document_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Answer question using both vector search and structured SQL lookup.
        
        Args:
            question: User's question
            document_id: Optional specific document to search
            
        Returns:
            Answer with citations
        """
        try:
            # First try vector search
            search_results = await self.search.search(
                query=question,
                top_k=5,
            )
            
            # If document_id specified, also get structured data
            structured_context = ""
            if document_id:
                chunks = await self.search.get_document_chunks(document_id)
                if chunks:
                    structured_context = f"\n\nAdditional context from document:\n"
                    for chunk in chunks[:3]:
                        structured_context += f"{chunk['chunk_text']}\n"
            
            if not search_results["results"]:
                return {
                    "answer": "I couldn't find any relevant information in the knowledge base.",
                    "citations": [],
                    "sources": [],
                    "confidence": 0.0,
                }
            
            # Build context
            context_parts = []
            citations = []
            sources = []
            
            for i, result in enumerate(search_results["results"], 1):
                context_parts.append(
                    f"[Source {i}] {result['document']['document_number']} (Page/Sheet {result['page_or_sheet']}):\n{result['chunk_text']}"
                )
                citations.append({
                    "source_number": i,
                    "document_number": result["document"]["document_number"],
                    "page_or_sheet": result["page_or_sheet"],
                    "snippet": result["chunk_text"][:200],
                })
                sources.append({
                    "document_id": result["document"]["id"],
                    "document_number": result["document"]["document_number"],
                    "title": result["document"]["title"],
                })
            
            if structured_context:
                context_parts.append(structured_context)
            
            context = "\n\n".join(context_parts)
            
            # Generate answer
            prompt = self._build_qa_prompt(question, context)
            answer = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1000,
            )
            
            avg_score = sum(r["score"] for r in search_results["results"]) / len(search_results["results"])
            confidence = min(avg_score, 1.0)
            
            return {
                "answer": answer.strip(),
                "citations": citations,
                "sources": sources,
                "confidence": confidence,
            }
            
        except Exception as e:
            logger.error(f"Structured lookup QA failed: {str(e)}", exc_info=True)
            raise


# Global QA instance
_qa: QuestionAnswering | None = None


def get_qa() -> QuestionAnswering:
    """Get the global QA instance."""
    global _qa
    if _qa is None:
        _qa = QuestionAnswering()
    return _qa