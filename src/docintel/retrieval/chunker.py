"""
Document chunker for DOCINTEL.
Splits documents into chunks for embedding and retrieval.
"""

import re
from typing import Any

from docintel.common.logging import get_logger
from docintel.config.settings import settings

logger = get_logger(__name__)


class DocumentChunker:
    """
    Splits documents into chunks for RAG retrieval.
    Page/sheet-aware chunking with overlap.
    """
    
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    def chunk_document(
        self,
        text: str,
        document_id: int,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Split a document into chunks.
        
        Args:
            text: Full document text
            document_id: Database ID of the document
            metadata: Optional metadata (page numbers, etc.)
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        # Split by page/sheet markers if present
        pages = self._split_by_pages(text)
        
        for page_num, page_text in pages:
            page_chunks = self._chunk_text(page_text, page_num)
            
            for chunk_text in page_chunks:
                chunk = {
                    "document_id": document_id,
                    "page_or_sheet": page_num,
                    "chunk_text": chunk_text,
                    "chunk_metadata": metadata or {},
                }
                chunks.append(chunk)
        
        logger.info(
            "Document chunking complete",
            extra={
                "document_id": document_id,
                "total_chunks": len(chunks),
                "pages": len(pages),
            },
        )
        
        return chunks
    
    def _split_by_pages(self, text: str) -> list[tuple[int, str]]:
        """
        Split text by page markers.
        
        Args:
            text: Full document text
            
        Returns:
            List of (page_number, page_text) tuples
        """
        pages = []
        
        # Look for page markers like "--- Page 1 ---" or "[Page 1]"
        page_pattern = re.compile(r'---\s*Page\s+(\d+)\s*---', re.IGNORECASE)
        page_pattern2 = re.compile(r'\[\s*Page\s+(\d+)\s*\]', re.IGNORECASE)
        
        # Try first pattern
        matches = list(page_pattern.finditer(text))
        if not matches:
            # Try second pattern
            matches = list(page_pattern2.finditer(text))
        
        if matches:
            # Split by page markers
            for i, match in enumerate(matches):
                page_num = int(match.group(1))
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                page_text = text[start:end].strip()
                if page_text:
                    pages.append((page_num, page_text))
        else:
            # No page markers found, treat as single page
            if text.strip():
                pages.append((1, text.strip()))
        
        return pages if pages else [(1, text)]
    
    def _chunk_text(self, text: str, page_num: int) -> list[str]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Text to chunk
            page_num: Page number for logging
            
        Returns:
            List of text chunks
        """
        if not text or len(text) <= self.chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for delimiter in [". ", ".\n", "\n\n", ".\t"]:
                    last_delim = text[start:end].rfind(delimiter)
                    if last_delim > self.chunk_size // 2:  # Only break if past halfway
                        end = start + last_delim + len(delimiter)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move forward with overlap
            start = end - self.chunk_overlap
        
        return chunks
    
    def chunk_with_context(
        self,
        text: str,
        document_id: int,
        context_before: int = 1,
        context_after: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Chunk document with surrounding context.
        
        Args:
            text: Full document text
            document_id: Database ID
            context_before: Number of previous chunks to include as context
            context_after: Number of next chunks to include as context
            
        Returns:
            List of chunks with context
        """
        base_chunks = self.chunk_document(text, document_id)
        
        if context_before == 0 and context_after == 0:
            return base_chunks
        
        enriched_chunks = []
        
        for i, chunk in enumerate(base_chunks):
            # Get context chunks
            context_parts = []
            
            # Previous chunks
            for j in range(max(0, i - context_before), i):
                context_parts.append(f"[Previous context]\n{base_chunks[j]['chunk_text']}")
            
            # Current chunk
            context_parts.append(f"[Current]\n{chunk['chunk_text']}")
            
            # Next chunks
            for j in range(i + 1, min(len(base_chunks), i + 1 + context_after)):
                context_parts.append(f"[Following context]\n{base_chunks[j]['chunk_text']}")
            
            enriched_chunk = chunk.copy()
            enriched_chunk["chunk_text"] = "\n\n".join(context_parts)
            enriched_chunks.append(enriched_chunk)
        
        return enriched_chunks


# Global chunker instance
_chunker: DocumentChunker | None = None


def get_chunker() -> DocumentChunker:
    """Get the global chunker instance."""
    global _chunker
    if _chunker is None:
        _chunker = DocumentChunker()
    return _chunker