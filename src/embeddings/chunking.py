"""Parent-child chunking for document retrieval."""
import logging
import re
from typing import Optional
from dataclasses import dataclass

from src.common.constants import (
    PARENT_CHUNK_SIZE,
    PARENT_CHUNK_OVERLAP,
    CHILD_CHUNK_SIZE,
    CHILD_CHUNK_OVERLAP,
    ChunkLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk (parent or child)."""
    
    content: str
    level: ChunkLevel
    document_id: int
    parent_id: Optional[int] = None
    chunk_index: int = 0
    token_count: int = 0
    page_numbers: list[int] = None
    metadata: dict = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.page_numbers is None:
            self.page_numbers = []
        if self.metadata is None:
            self.metadata = {}


class ParentChildChunker:
    """
    Implements parent-child chunking strategy.
    Parent chunks (1024 tokens, 128 overlap) provide context.
    Child chunks (256 tokens, 32 overlap) are embedded for retrieval.
    """
    
    def __init__(
        self,
        parent_size: int = PARENT_CHUNK_SIZE,
        parent_overlap: int = PARENT_CHUNK_OVERLAP,
        child_size: int = CHILD_CHUNK_SIZE,
        child_overlap: int = CHILD_CHUNK_OVERLAP,
    ):
        """
        Initialize chunker with configured sizes.
        
        Args:
            parent_size: Target token count for parent chunks
            parent_overlap: Overlap tokens between parent chunks
            child_size: Target token count for child chunks
            child_overlap: Overlap tokens between child chunks
        """
        self.parent_size = parent_size
        self.parent_overlap = parent_overlap
        self.child_size = child_size
        self.child_overlap = child_overlap
    
    def chunk_document(
        self,
        text: str,
        document_id: int,
        page_markers: bool = True,
    ) -> tuple[list[Chunk], list[Chunk]]:
        """
        Chunk a document into parent and child chunks.
        
        Args:
            text: Full document text
            document_id: ID of the document
            page_markers: Whether to include page markers in text
            
        Returns:
            Tuple of (parent_chunks, child_chunks)
        """
        # First, create parent chunks
        parent_chunks = self._create_parent_chunks(text, document_id, page_markers)
        
        # Then, create child chunks from each parent
        child_chunks = self._create_child_chunks(parent_chunks, document_id)
        
        logger.info(
            f"Created {len(parent_chunks)} parent chunks and {len(child_chunks)} child chunks "
            f"for document {document_id}"
        )
        
        return parent_chunks, child_chunks
    
    def _create_parent_chunks(
        self,
        text: str,
        document_id: int,
        page_markers: bool,
    ) -> list[Chunk]:
        """
        Create parent chunks from document text.
        
        Args:
            text: Document text
            document_id: Document ID
            page_markers: Whether text includes page markers
            
        Returns:
            List of parent Chunk objects
        """
        # Split text into paragraphs/sections
        sections = self._split_into_sections(text)
        
        parent_chunks = []
        current_chunk_text = ""
        current_tokens = 0
        chunk_index = 0
        
        for section in sections:
            section_tokens = self._estimate_tokens(section)
            
            # If adding this section would exceed parent size, finalize current chunk
            if current_tokens + section_tokens > self.parent_size and current_chunk_text:
                # Create parent chunk
                parent_chunk = Chunk(
                    content=current_chunk_text.strip(),
                    level=ChunkLevel.PARENT,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    token_count=current_tokens,
                )
                parent_chunks.append(parent_chunk)
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk_text, self.parent_overlap)
                current_chunk_text = overlap_text + "\n\n" + section
                current_tokens = self._estimate_tokens(current_chunk_text)
            else:
                # Add section to current chunk
                if current_chunk_text:
                    current_chunk_text += "\n\n" + section
                else:
                    current_chunk_text = section
                current_tokens += section_tokens
        
        # Don't forget the last chunk
        if current_chunk_text.strip():
            parent_chunk = Chunk(
                content=current_chunk_text.strip(),
                level=ChunkLevel.PARENT,
                document_id=document_id,
                chunk_index=chunk_index,
                token_count=current_tokens,
            )
            parent_chunks.append(parent_chunk)
        
        return parent_chunks
    
    def _create_child_chunks(
        self,
        parent_chunks: list[Chunk],
        document_id: int,
    ) -> list[Chunk]:
        """
        Create child chunks from parent chunks.
        
        Args:
            parent_chunks: List of parent chunks
            document_id: Document ID
            
        Returns:
            List of child Chunk objects
        """
        child_chunks = []
        
        for parent in parent_chunks:
            # Split parent into child chunks
            sections = self._split_into_sections(parent.content)
            
            current_child_text = ""
            current_tokens = 0
            child_index = 0
            
            for section in sections:
                section_tokens = self._estimate_tokens(section)
                
                # If adding this section would exceed child size, finalize current child
                if current_tokens + section_tokens > self.child_size and current_child_text:
                    child_chunk = Chunk(
                        content=current_child_text.strip(),
                        level=ChunkLevel.CHILD,
                        document_id=document_id,
                        parent_id=parent.id if hasattr(parent, 'id') else None,
                        chunk_index=child_index,
                        token_count=current_tokens,
                        metadata={"parent_index": parent.chunk_index},
                    )
                    child_chunks.append(child_chunk)
                    child_index += 1
                    
                    # Start new child with overlap
                    overlap_text = self._get_overlap_text(current_child_text, self.child_overlap)
                    current_child_text = overlap_text + "\n\n" + section
                    current_tokens = self._estimate_tokens(current_child_text)
                else:
                    # Add section to current child
                    if current_child_text:
                        current_child_text += "\n\n" + section
                    else:
                        current_child_text = section
                    current_tokens += section_tokens
            
            # Don't forget the last child
            if current_child_text.strip():
                child_chunk = Chunk(
                    content=current_child_text.strip(),
                    level=ChunkLevel.CHILD,
                    document_id=document_id,
                    parent_id=parent.id if hasattr(parent, 'id') else None,
                    chunk_index=child_index,
                    token_count=current_tokens,
                    metadata={"parent_index": parent.chunk_index},
                )
                child_chunks.append(child_chunk)
        
        return child_chunks
    
    def _split_into_sections(self, text: str) -> list[str]:
        """
        Split text into logical sections (paragraphs).
        
        Args:
            text: Text to split
            
        Returns:
            List of section texts
        """
        # Split on double newlines (paragraphs)
        sections = text.split("\n\n")
        
        # Filter out empty sections
        sections = [s.strip() for s in sections if s.strip()]
        
        return sections
    
    def _get_overlap_text(self, text: str, target_tokens: int) -> str:
        """
        Get the last N tokens from text for overlap.
        
        Args:
            text: Source text
            target_tokens: Number of tokens to include
            
        Returns:
            Overlap text
        """
        # Simple word-based tokenization (approximation)
        words = text.split()
        
        if len(words) <= target_tokens:
            return text
        
        # Take last N words
        overlap_words = words[-target_tokens:]
        return " ".join(overlap_words)
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Uses simple word count as approximation (1 word ≈ 1.3 tokens).
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        words = len(text.split())
        return int(words * 1.3)
    
    def extract_page_numbers(self, text: str) -> list[int]:
        """
        Extract page numbers from text with page markers.
        
        Args:
            text: Text with page markers like [Page 5]
            
        Returns:
            List of page numbers found in text
        """
        page_pattern = re.compile(r"\[Page\s+(\d+)\]", re.IGNORECASE)
        matches = page_pattern.findall(text)
        return [int(m) for m in matches]