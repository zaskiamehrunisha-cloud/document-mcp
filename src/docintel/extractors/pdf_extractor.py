"""
PDF extractor for DOCINTEL.
Extracts text and metadata from PDF files using PyMuPDF.
"""

from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from docintel.common.exceptions import ExtractionError
from docintel.common.logging import get_logger
from docintel.common.constants import SOURCE_LAYER_NATIVE

logger = get_logger(__name__)


class PDFExtractor:
    """
    Extracts text and metadata from PDF files.
    Uses PyMuPDF for native text extraction.
    """
    
    def __init__(self):
        """Initialize the PDF extractor."""
        pass
    
    def extract(self, file_path: str) -> dict:
        """
        Extract text and metadata from a PDF.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with 'text', 'metadata', and 'source_layer'
        """
        try:
            doc = fitz.open(file_path)
            
            # Extract metadata
            metadata = self._extract_metadata(doc)
            
            # Extract text from all pages
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"\n--- Page {page_num + 1} ---\n{text}")
            
            doc.close()
            
            full_text = "\n".join(text_parts)
            
            logger.info(
                "PDF extraction complete",
                extra={
                    "file": file_path,
                    "pages": len(text_parts),
                    "total_chars": len(full_text),
                },
            )
            
            return {
                "text": full_text,
                "metadata": metadata,
                "source_layer": SOURCE_LAYER_NATIVE,
            }
            
        except Exception as e:
            error_msg = f"Failed to extract PDF: {str(e)}"
            logger.error(error_msg, extra={"file": file_path}, exc_info=True)
            raise ExtractionError(error_msg) from e
    
    def _extract_metadata(self, doc: fitz.Document) -> dict:
        """
        Extract metadata from a PDF document.
        
        Args:
            doc: PyMuPDF document object
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        try:
            # Get PDF metadata
            pdf_meta = doc.metadata
            if pdf_meta:
                metadata["title"] = pdf_meta.get("title", "")
                metadata["author"] = pdf_meta.get("author", "")
                metadata["subject"] = pdf_meta.get("subject", "")
                metadata["creator"] = pdf_meta.get("creator", "")
                metadata["producer"] = pdf_meta.get("producer", "")
                metadata["creation_date"] = pdf_meta.get("creationDate", "")
                metadata["modification_date"] = pdf_meta.get("modDate", "")
            
            # Get page count
            metadata["page_count"] = len(doc)
            
            # Try to extract document number from first page
            if len(doc) > 0:
                first_page = doc[0]
                text = first_page.get_text()
                metadata["first_page_text"] = text[:500]  # First 500 chars for analysis
                
        except Exception as e:
            logger.warning(f"Could not extract all metadata: {str(e)}")
        
        return metadata
    
    def extract_page(self, file_path: str, page_number: int) -> dict:
        """
        Extract text from a specific page.
        
        Args:
            file_path: Path to the PDF file
            page_number: 1-based page number
            
        Returns:
            Dictionary with 'text' and 'metadata'
        """
        try:
            doc = fitz.open(file_path)
            
            if page_number < 1 or page_number > len(doc):
                raise ValueError(f"Page {page_number} out of range (1-{len(doc)})")
            
            page = doc[page_number - 1]
            text = page.get_text()
            
            doc.close()
            
            logger.info(
                "PDF page extraction complete",
                extra={"file": file_path, "page": page_number, "chars": len(text)},
            )
            
            return {
                "text": text,
                "page_number": page_number,
                "source_layer": SOURCE_LAYER_NATIVE,
            }
            
        except Exception as e:
            error_msg = f"Failed to extract PDF page {page_number}: {str(e)}"
            logger.error(error_msg, extra={"file": file_path}, exc_info=True)
            raise ExtractionError(error_msg) from e
    
    def has_text_layer(self, file_path: str) -> bool:
        """
        Check if a PDF has a native text layer.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            True if the PDF has extractable text
        """
        try:
            doc = fitz.open(file_path)
            
            # Check first few pages for text
            text_found = False
            for i in range(min(3, len(doc))):
                text = doc[i].get_text()
                if len(text.strip()) > 50:
                    text_found = True
                    break
            
            doc.close()
            return text_found
            
        except Exception as e:
            logger.error(f"Failed to check text layer: {str(e)}")
            return False
    
    def get_page_count(self, file_path: str) -> int:
        """
        Get the number of pages in a PDF.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Number of pages
        """
        try:
            doc = fitz.open(file_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            error_msg = f"Failed to get page count: {str(e)}"
            logger.error(error_msg, extra={"file": file_path})
            raise ExtractionError(error_msg) from e
    
    def render_page_to_image(
        self, file_path: str, page_number: int, dpi: int = 300
    ) -> bytes:
        """
        Render a PDF page to an image.
        
        Args:
            file_path: Path to the PDF file
            page_number: 1-based page number
            dpi: Resolution in DPI
            
        Returns:
            Image bytes (PNG format)
        """
        try:
            doc = fitz.open(file_path)
            
            if page_number < 1 or page_number > len(doc):
                raise ValueError(f"Page {page_number} out of range")
            
            page = doc[page_number - 1]
            
            # Calculate zoom factor for desired DPI
            # Default is 72 DPI, so zoom = dpi / 72
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            
            doc.close()
            
            logger.debug(
                "Page rendered to image",
                extra={"file": file_path, "page": page_number, "dpi": dpi},
            )
            
            return img_bytes
            
        except Exception as e:
            error_msg = f"Failed to render page: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ExtractionError(error_msg) from e


# Global PDF extractor instance
_pdf_extractor: Optional[PDFExtractor] = None


def get_pdf_extractor() -> PDFExtractor:
    """Get the global PDF extractor instance."""
    global _pdf_extractor
    if _pdf_extractor is None:
        _pdf_extractor = PDFExtractor()
    return _pdf_extractor