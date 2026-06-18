"""
Native text layer detection and reliability assessment.
Determines whether a PDF has a usable native text layer or requires OCR.
"""

import re
from typing import Optional

import fitz  # PyMuPDF

from docintel.common.constants import (
    DEFAULT_OCR_CONFIDENCE_THRESHOLD,
    PAGE_NUMBER_PATTERN,
)
from docintel.common.exceptions import NativeTextLayerUnreliableError
from docintel.common.logging import get_logger

logger = get_logger(__name__)


class TextLayerAnalyzer:
    """Analyzes PDF text layers to determine extraction strategy."""
    
    def __init__(self, confidence_threshold: float = DEFAULT_OCR_CONFIDENCE_THRESHOLD):
        """
        Initialize the text layer analyzer.
        
        Args:
            confidence_threshold: Minimum ratio of text-bearing pages required
        """
        self.confidence_threshold = confidence_threshold
    
    def has_reliable_text_layer(self, file_path: str) -> bool:
        """
        Check if a PDF has a reliable native text layer.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            True if the text layer is reliable, False if OCR is needed
        """
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            if total_pages == 0:
                logger.warning("PDF has no pages", extra={"file": file_path})
                return False
            
            text_pages = 0
            total_text_length = 0
            
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                text_length = len(text.strip())
                total_text_length += text_length
                
                # Consider a page as having text if it has more than 50 characters
                # and contains recognizable patterns (page numbers, dates, etc.)
                if text_length > 50:
                    text_pages += 1
            
            doc.close()
            
            # Calculate the ratio of pages with text
            text_ratio = text_pages / total_pages
            
            # Also check total text density (characters per page)
            avg_chars_per_page = total_text_length / total_pages
            
            # A reliable text layer should have:
            # 1. Most pages (>70%) containing text
            # 2. Reasonable text density (>100 chars/page on average)
            is_reliable = text_ratio >= 0.7 and avg_chars_per_page >= 100
            
            logger.info(
                "Text layer analysis complete",
                extra={
                    "file": file_path,
                    "total_pages": total_pages,
                    "text_pages": text_pages,
                    "text_ratio": round(text_ratio, 2),
                    "avg_chars_per_page": round(avg_chars_per_page, 1),
                    "is_reliable": is_reliable,
                },
            )
            
            return is_reliable
            
        except Exception as e:
            logger.error(
                "Failed to analyze text layer",
                extra={"file": file_path, "error": str(e)},
                exc_info=True,
            )
            # If we can't analyze, assume we need OCR to be safe
            return False
    
    def extract_native_text(self, file_path: str) -> str:
        """
        Extract text from the native text layer of a PDF.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text from all pages
        """
        try:
            doc = fitz.open(file_path)
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"\n--- Page {page_num + 1} ---\n{text}")
            
            doc.close()
            
            full_text = "\n".join(text_parts)
            logger.info(
                "Native text extraction complete",
                extra={
                    "file": file_path,
                    "pages_extracted": len(text_parts),
                    "total_chars": len(full_text),
                },
            )
            
            return full_text
            
        except Exception as e:
            error_msg = f"Failed to extract native text: {str(e)}"
            logger.error(error_msg, extra={"file": file_path}, exc_info=True)
            raise NativeTextLayerUnreliableError(error_msg) from e
    
    def get_page_text(self, file_path: str, page_number: int) -> str:
        """
        Extract text from a specific page.
        
        Args:
            file_path: Path to the PDF file
            page_number: 1-based page number
            
        Returns:
            Text from the specified page
        """
        try:
            doc = fitz.open(file_path)
            if page_number < 1 or page_number > len(doc):
                raise ValueError(f"Page {page_number} out of range (1-{len(doc)})")
            
            page = doc[page_number - 1]
            text = page.get_text()
            doc.close()
            
            return text
            
        except Exception as e:
            error_msg = f"Failed to extract text from page {page_number}: {str(e)}"
            logger.error(error_msg, extra={"file": file_path}, exc_info=True)
            raise NativeTextLayerUnreliableError(error_msg) from e


def has_reliable_text_layer(file_path: str) -> bool:
    """
    Convenience function to check if a PDF has a reliable text layer.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        True if the text layer is reliable, False otherwise
    """
    analyzer = TextLayerAnalyzer()
    return analyzer.has_reliable_text_layer(file_path)