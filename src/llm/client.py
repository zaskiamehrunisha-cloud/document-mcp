"""Local LLM client for Q&A via Ollama."""
import json
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

import httpx
from src.config.settings import settings
from src.common.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Local LLM client for Q&A using Ollama.
    Generates grounded answers with citations from retrieved context.
    """
    
    def __init__(self):
        """Initialize LLM client."""
        self.ollama_host = settings.ollama_host
        self.model = settings.ollama_model
        self.fallback_model = settings.ollama_fallback_model
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def generate_answer(
        self,
        query: str,
        context_chunks: list[dict],
        use_fallback: bool = False,
    ) -> dict:
        """
        Generate a grounded answer from retrieved context chunks.
        
        Args:
            query: User's question
            context_chunks: Retrieved document chunks with metadata
            use_fallback: Whether to use fallback model
            
        Returns:
            Dictionary with answer, citations, and confidence
        """
        prompt = self._build_qa_prompt(query, context_chunks)
        
        try:
            response = await self._call_ollama(prompt, use_fallback=use_fallback)
            return self._parse_qa_response(response, context_chunks)
        except Exception as e:
            if not use_fallback:
                logger.warning(f"Primary LLM Q&A failed: {e}. Trying fallback model.")
                return await self.generate_answer(query, context_chunks, use_fallback=True)
            else:
                logger.error(f"LLM Q&A failed completely: {e}")
                raise LLMError(f"Q&A generation failed: {e}") from e
    
    def _build_qa_prompt(self, query: str, context_chunks: list[dict]) -> str:
        """
        Build Q&A prompt with retrieved context.
        
        Args:
            query: User's question
            context_chunks: Retrieved chunks
            
        Returns:
            Formatted prompt
        """
        # Build context section
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            doc_info = chunk.get("document", {})
            chunk_info = chunk.get("chunk", {})
            
            doc_number = doc_info.get("document_number", "Unknown")
            doc_title = doc_info.get("title", "Unknown")
            page_or_sheet = chunk_info.get("page_numbers", ["N/A"])[0] if chunk_info.get("page_numbers") else "N/A"
            
            context_parts.append(
                f"[{i}] Document: {doc_number} - {doc_title} (Page/Sheet: {page_or_sheet})\n"
                f"{chunk_info.get('content', '')}\n"
            )
        
        context_text = "\n".join(context_parts)
        
        prompt = f"""You are an engineering document assistant. Answer the user's question using ONLY the provided context from engineering documents.

RULES:
1. Answer ONLY from the provided context - do not use outside knowledge
2. If the context doesn't contain the answer, say "I cannot find this information in the provided documents"
3. Cite your sources using the document number and page/sheet number in the format: [DOC_NUMBER · Sheet/Page X]
4. Be precise and technical - use exact values, units, and terminology from the documents
5. If multiple sources provide different information, mention both

CONTEXT FROM DOCUMENTS:
{context_text}

USER QUESTION: {query}

Provide your answer in this format:
ANSWER: [Your grounded answer with citations]
CONFIDENCE: [High/Medium/Low]
CITATIONS: [List of document numbers and pages used]

ANSWER:"""
        
        return prompt
    
    def _parse_qa_response(self, response: str, context_chunks: list[dict]) -> dict:
        """
        Parse LLM Q&A response.
        
        Args:
            response: Raw LLM response
            context_chunks: Retrieved chunks for citation extraction
            
        Returns:
            Parsed response with answer, citations, and confidence
        """
        try:
            # Extract answer, confidence, and citations
            answer = ""
            confidence = "Medium"
            citations = []
            
            lines = response.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("ANSWER:"):
                    answer = line.replace("ANSWER:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    conf_text = line.replace("CONFIDENCE:", "").strip().lower()
                    if conf_text in ["high", "medium", "low"]:
                        confidence = conf_text.capitalize()
                elif line.startswith("CITATIONS:"):
                    citations_text = line.replace("CITATIONS:", "").strip()
                    # Parse citations (format: DOC_NUMBER · Sheet/Page X)
                    citations = self._parse_citations(citations_text, context_chunks)
            
            # If no structured format found, use entire response as answer
            if not answer:
                answer = response.strip()
            
            # Extract citations from context if not explicitly provided
            if not citations:
                citations = self._extract_citations_from_context(context_chunks)
            
            return {
                "answer": answer,
                "confidence": confidence,
                "citations": citations,
            }
            
        except Exception as e:
            logger.error(f"Failed to parse Q&A response: {e}")
            # Return raw response as fallback
            return {
                "answer": response.strip(),
                "confidence": "Low",
                "citations": [],
            }
    
    def _parse_citations(self, citations_text: str, context_chunks: list[dict]) -> list[dict]:
        """
        Parse citation text into structured citations.
        
        Args:
            citations_text: Raw citations text
            context_chunks: Context chunks for metadata
            
        Returns:
            List of citation dictionaries
        """
        citations = []
        
        # Simple parsing - look for document numbers and page/sheet references
        import re
        
        # Pattern: DOC-NUMBER · Sheet/Page X
        pattern = r"([A-Z]{2,4}-[A-Z]-[A-Z]{2}-\d{2}-\d{3})\s*[·•]\s*(?:Sheet|Page)\s*(\d+)"
        
        matches = re.findall(pattern, citations_text, re.IGNORECASE)
        
        for doc_number, page in matches:
            # Find matching context chunk
            for chunk in context_chunks:
                doc_info = chunk.get("document", {})
                if doc_info.get("document_number") == doc_number:
                    citations.append({
                        "document_number": doc_number,
                        "title": doc_info.get("title", "Unknown"),
                        "page_or_sheet": f"Sheet {page}" if "sheet" in citations_text.lower() else f"Page {page}",
                    })
                    break
        
        return citations
    
    def _extract_citations_from_context(self, context_chunks: list[dict]) -> list[dict]:
        """
        Extract citations from context chunks.
        
        Args:
            context_chunks: Retrieved context chunks
            
        Returns:
            List of citation dictionaries
        """
        citations = []
        seen_docs = set()
        
        for chunk in context_chunks:
            doc_info = chunk.get("document", {})
            chunk_info = chunk.get("chunk", {})
            
            doc_number = doc_info.get("document_number")
            if not doc_number or doc_number in seen_docs:
                continue
            
            seen_docs.add(doc_number)
            
            page_numbers = chunk_info.get("page_numbers", [])
            page_or_sheet = f"Sheet {page_numbers[0]}" if page_numbers else "N/A"
            
            citations.append({
                "document_number": doc_number,
                "title": doc_info.get("title", "Unknown"),
                "page_or_sheet": page_or_sheet,
            })
        
        return citations[:5]  # Limit to top 5 citations
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_ollama(self, prompt: str, use_fallback: bool = False) -> str:
        """
        Call Ollama API.
        
        Args:
            prompt: Prompt text
            use_fallback: Whether to use fallback model
            
        Returns:
            LLM response text
        """
        model = self.fallback_model if use_fallback else self.model
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Slightly higher for natural language
                        "num_predict": 1000,
                        "top_p": 0.9,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")


# Global LLM client instance
llm_client = LLMClient()