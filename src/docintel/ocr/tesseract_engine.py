"""
Tesseract OCR engine for DOCINTEL.
Lightweight fallback OCR engine for clean text documents.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image

from docintel.common.exceptions import OCRUnavailableError
from docintel.common.logging import get_logger
from docintel.config.settings import settings

logger = get_logger(__name__)


class TesseractEngine:
    """
    Tesseract-based OCR engine.
    Lightweight fallback for clean printed text and simple documents.
    """
    
    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        lang: Optional[str] = None,
    ):
        """
        Initialize the Tesseract engine.
        
        Args:
            tesseract_cmd: Path to tesseract executable
            lang: Language code (e.g., "eng" for English)
        """
        self.tesseract_cmd = tesseract_cmd or settings.tesseract_cmd
        self.lang = lang or settings.ocr_lang
        
        # Configure pytesseract
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        
        # Verify tesseract is available
        self._check_availability()
    
    def _check_availability(self) -> None:
        """Check if tesseract is installed and accessible."""
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
        except Exception as e:
            error_msg = f"Tesseract not available: {str(e)}"
            logger.error(error_msg)
            raise OCRUnavailableError(error_msg) from e
    
    def ocr_image(self, image_path: str) -> str:
        """
        Perform OCR on an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text
        """
        try:
            # Open image with PIL
            image = Image.open(image_path)
            
            # Convert to grayscale for better OCR
            if image.mode != 'L':
                image = image.convert('L')
            
            # Perform OCR
            text = pytesseract.image_to_string(image, lang=self.lang)
            
            logger.info(
                "Tesseract OCR complete",
                extra={
                    "image": image_path,
                    "text_length": len(text),
                },
            )
            
            return text.strip()
            
        except Exception as e:
            error_msg = f"Tesseract OCR failed: {str(e)}"
            logger.error(error_msg, extra={"image": image_path}, exc_info=True)
            raise OCRUnavailableError(error_msg) from e
    
    def ocr_pdf_page(self, pdf_path: str, page_number: int) -> str:
        """
        Perform OCR on a specific page of a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            page_number: 1-based page number
            
        Returns:
            Extracted text from the page
        """
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            if page_number < 1 or page_number > len(doc):
                raise ValueError(f"Page {page_number} out of range")
            
            page = doc[page_number - 1]
            
            # Render page at 300 DPI
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            doc.close()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                img.save(tmp.name)
                tmp_path = tmp.name
            
            try:
                text = self.ocr_image(tmp_path)
                return text
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            error_msg = f"Failed to OCR PDF page {page_number}: {str(e)}"
            logger.error(error_msg, extra={"pdf": pdf_path}, exc_info=True)
            raise OCRUnavailableError(error_msg) from e
    
    def ocr_pdf(self, pdf_path: str) -> str:
        """
        Perform OCR on all pages of a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text from all pages
        """
        try:
            import fitz
            
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            text_parts = []
            
            logger.info(
                "Starting PDF OCR with Tesseract",
                extra={"pdf": pdf_path, "total_pages": total_pages},
            )
            
            for page_num in range(1, total_pages + 1):
                logger.debug(f"OCRing page {page_num}/{total_pages}")
                page_text = self.ocr_pdf_page(pdf_path, page_num)
                if page_text.strip():
                    text_parts.append(f"\n--- Page {page_num} ---\n{page_text}")
            
            doc.close()
            
            full_text = "\n".join(text_parts)
            
            logger.info(
                "PDF OCR complete",
                extra={
                    "pdf": pdf_path,
                    "pages_processed": total_pages,
                    "total_chars": len(full_text),
                },
            )
            
            return full_text
            
        except Exception as e:
            error_msg = f"Failed to OCR PDF: {str(e)}"
            logger.error(error_msg, extra={"pdf": pdf_path}, exc_info=True)
            raise OCRUnavailableError(error_msg) from e
    
    def ocr_image_array(self, image: np.ndarray) -> str:
        """
        Perform OCR on a numpy image array.
        
        Args:
            image: Image as numpy array (BGR or grayscale)
            
        Returns:
            Extracted text
        """
        try:
            # Convert BGR to RGB if needed
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(image)
            
            # Convert to grayscale
            if pil_image.mode != 'L':
                pil_image = pil_image.convert('L')
            
            # Perform OCR
            text = pytesseract.image_to_string(pil_image, lang=self.lang)
            
            logger.info(
                "Tesseract OCR on array complete",
                extra={"text_length": len(text)},
            )
            
            return text.strip()
            
        except Exception as e:
            error_msg = f"Tesseract OCR on array failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise OCRUnavailableError(error_msg) from e
    
    def get_confidence(self, image_path: str) -> float:
        """
        Get OCR confidence score for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Average confidence score (0-1)
        """
        try:
            image = Image.open(image_path)
            if image.mode != 'L':
                image = image.convert('L')
            
            data = pytesseract.image_to_data(image, lang=self.lang, output_type=pytesseract.Output.DICT)
            
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            if not confidences:
                return 0.0
            
            avg_confidence = sum(confidences) / len(confidences) / 100.0
            return avg_confidence
            
        except Exception as e:
            logger.warning(f"Could not get OCR confidence: {str(e)}")
            return 0.0


# Global Tesseract instance
_tesseract: Optional[TesseractEngine] = None


def get_tesseract() -> TesseractEngine:
    """Get the global Tesseract instance."""
    global _tesseract
    if _tesseract is None:
        _tesseract = TesseractEngine()
    return _tesseract