"""PDF extractor with native text extraction and OCR fallback."""
import logging
from pathlib import Path
from typing import Optional
import io

from src.ocr.engine import ocr_engine, TextBlock
from src.ocr.confidence import ConfidenceGate
from src.common.exceptions import OCRError, ParseError
from src.common.constants import NATIVE_TEXT_THRESHOLD

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    PDF extractor with native text extraction and OCR fallback.
    Uses pdfplumber/PyMuPDF for native text; triggers OCR when text is sparse.
    """
    
    def __init__(self):
        """Initialize PDF extractor."""
        self.confidence_gate = ConfidenceGate()
    
    def extract(self, file_path: Path, page_count: Optional[int] = None) -> dict:
        """
        Extract text and metadata from PDF.
        
        Args:
            file_path: Path to PDF file
            page_count: Optional known page count
            
        Returns:
            Dictionary with extracted text, metadata, and low-confidence regions
        """
        try:
            # Try native text extraction first
            native_text, detected_pages = self._extract_native_text(file_path)
            
            # Check if OCR fallback is needed
            needs_ocr = self._needs_ocr_fallback(native_text, detected_pages)
            
            all_text = native_text
            all_blocks = []
            low_confidence_regions = []
            
            if needs_ocr:
                logger.info(f"Native text sparse ({len(native_text)} chars), triggering OCR fallback")
                ocr_result = self._extract_with_ocr(file_path, page_count or detected_pages)
                all_text = ocr_result["text"]
                all_blocks = ocr_result["blocks"]
                low_confidence_regions = ocr_result["low_confidence_regions"]
            else:
                logger.info(f"Native text sufficient ({len(native_text)} chars), skipping OCR")
            
            return {
                "text": all_text,
                "blocks": all_blocks,
                "low_confidence_regions": low_confidence_regions,
                "page_count": page_count or detected_pages,
                "extraction_method": "ocr" if needs_ocr else "native",
            }
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}", exc_info=True)
            raise ParseError(f"PDF extraction failed: {e}") from e
    
    def _extract_native_text(self, file_path: Path) -> tuple[str, int]:
        """
        Extract native text from PDF using pdfplumber and PyMuPDF.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        text_parts = []
        page_count = 0
        
        # Try pdfplumber first (better for tables)
        try:
            import pdfplumber
            
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                
                for i, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"\n[Page {i}]\n{page_text}")
                    
                    # Also extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            table_text = self._format_table(table)
                            text_parts.append(f"\n[Table on Page {i}]\n{table_text}")
        
        except ImportError:
            logger.warning("pdfplumber not available, using PyMuPDF only")
            page_count = self._extract_with_pymupdf(file_path, text_parts)
        
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}, trying PyMuPDF")
            page_count = self._extract_with_pymupdf(file_path, text_parts)
        
        return "\n".join(text_parts), page_count
    
    def _extract_with_pymupdf(self, file_path: Path, text_parts: list[str]) -> int:
        """
        Extract text using PyMuPDF as fallback.
        
        Args:
            file_path: Path to PDF file
            text_parts: List to append text parts to
            
        Returns:
            Page count
        """
        import fitz  # PyMuPDF
        
        doc = fitz.open(file_path)
        page_count = len(doc)
        
        for i in range(page_count):
            page = doc[i]
            text = page.get_text()
            if text:
                text_parts.append(f"\n[Page {i + 1}]\n{text}")
        
        doc.close()
        return page_count
    
    def _format_table(self, table: list[list]) -> str:
        """
        Format extracted table as text.
        
        Args:
            table: Table data (list of rows)
            
        Returns:
            Formatted table text
        """
        lines = []
        for row in table:
            # Filter out None values and join with tabs
            cells = [str(cell) if cell is not None else "" for cell in row]
            lines.append("\t".join(cells))
        return "\n".join(lines)
    
    def _needs_ocr_fallback(self, text: str, page_count: int) -> bool:
        """
        Determine if OCR fallback is needed based on text density.
        
        Args:
            text: Extracted native text
            page_count: Number of pages
            
        Returns:
            True if OCR fallback is needed
        """
        if page_count == 0:
            return False
        
        # Calculate average characters per page
        chars_per_page = len(text) / page_count
        
        # If average is below threshold, likely needs OCR
        if chars_per_page < NATIVE_TEXT_THRESHOLD:
            logger.info(
                f"Low text density: {chars_per_page:.1f} chars/page "
                f"(threshold: {NATIVE_TEXT_THRESHOLD})"
            )
            return True
        
        return False
    
    def _extract_with_ocr(
        self,
        file_path: Path,
        page_count: int,
    ) -> dict:
        """
        Extract text using OCR on all pages.
        
        Args:
            file_path: Path to PDF file
            page_count: Number of pages
            
        Returns:
            Dictionary with text, blocks, and low-confidence regions
        """
        all_text_parts = []
        all_blocks = []
        all_low_confidence = []
        
        for page_num in range(1, page_count + 1):
            try:
                # Render page to image
                image = ocr_engine.render_page_to_image(file_path, page_num, dpi=300)
                
                # Perform OCR
                blocks = ocr_engine.ocr_image(image, page=page_num)
                
                # Apply confidence gating
                passing_blocks, low_conf = self.confidence_gate.evaluate(
                    blocks, document_id=0  # Will be set later
                )
                
                # Collect text
                page_text = "\n".join(block.text for block in passing_blocks)
                all_text_parts.append(f"\n[Page {page_num}]\n{page_text}")
                
                # Collect blocks and low-confidence regions
                all_blocks.extend(blocks)
                all_low_confidence.extend(low_conf)
                
            except Exception as e:
                logger.error(f"OCR failed for page {page_num}: {e}")
                # Continue with other pages
        
        return {
            "text": "\n".join(all_text_parts),
            "blocks": all_blocks,
            "low_confidence_regions": all_low_confidence,
        }


# Global PDF extractor instance
pdf_extractor = PDFExtractor()