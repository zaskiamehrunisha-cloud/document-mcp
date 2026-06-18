"""
PaddleOCR engine for DOCINTEL.
Primary OCR engine with PP-Structure for document layout analysis.
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image

from docintel.common.exceptions import OCRUnavailableError
from docintel.common.logging import get_logger
from docintel.config.settings import settings

logger = get_logger(__name__)


class PaddleOCREngine:
    """
    PaddleOCR-based OCR engine with PP-Structure for layout analysis.
    Primary OCR engine for raster CAD sheets and scanned documents.
    """
    
    def __init__(
        self,
        use_angle_cls: Optional[bool] = None,
        lang: Optional[str] = None,
        use_gpu: bool = False,
    ):
        """
        Initialize the PaddleOCR engine.
        
        Args:
            use_angle_cls: Whether to use angle classification
            lang: Language code (e.g., "en")
            use_gpu: Whether to use GPU acceleration
        """
        self.use_angle_cls = use_angle_cls if use_angle_cls is not None else settings.paddle_use_angle_cls
        self.lang = lang or settings.ocr_lang
        self.use_gpu = use_gpu
        
        self._ocr: Optional[PaddleOCR] = None
    
    def _get_ocr(self) -> PaddleOCR:
        """Get or create the PaddleOCR instance."""
        if self._ocr is None:
            logger.info(
                "Initializing PaddleOCR",
                extra={"lang": self.lang, "use_gpu": self.use_gpu},
            )
            try:
                self._ocr = PaddleOCR(
                    use_angle_cls=self.use_angle_cls,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False,
                )
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                error_msg = f"Failed to initialize PaddleOCR: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise OCRUnavailableError(error_msg) from e
        return self._ocr
    
    def ocr_image(self, image_path: str) -> str:
        """
        Perform OCR on an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text
        """
        ocr = self._get_ocr()
        
        try:
            result = ocr.ocr(image_path, cls=True)
            
            # PaddleOCR returns a list of lists, one per page
            # Each page contains [bbox, (text, confidence)]
            text_parts = []
            
            if result and result[0]:
                for line in result[0]:
                    if line:
                        text = line[1][0]  # (text, confidence)
                        confidence = line[1][1]
                        if confidence > 0.5:  # Filter low-confidence results
                            text_parts.append(text)
            
            extracted_text = "\n".join(text_parts)
            
            logger.info(
                "OCR complete",
                extra={
                    "image": image_path,
                    "text_length": len(extracted_text),
                    "lines_detected": len(text_parts),
                },
            )
            
            return extracted_text
            
        except Exception as e:
            error_msg = f"PaddleOCR failed: {str(e)}"
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
            # Convert PDF page to image
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            if page_number < 1 or page_number > len(doc):
                raise ValueError(f"Page {page_number} out of range")
            
            page = doc[page_number - 1]
            
            # Render page at 300 DPI for good OCR quality
            mat = fitz.Matrix(2, 2)  # 2x zoom for ~300 DPI
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to numpy array
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            
            # Convert RGB to BGR (OpenCV format)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            doc.close()
            
            # Save to temporary file for PaddleOCR
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                cv2.imwrite(tmp.name, img)
                tmp_path = tmp.name
            
            try:
                text = self.ocr_image(tmp_path)
                return text
            finally:
                # Clean up temp file
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
                "Starting PDF OCR",
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
            image: Image as numpy array (BGR format)
            
        Returns:
            Extracted text
        """
        ocr = self._get_ocr()
        
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                cv2.imwrite(tmp.name, image)
                tmp_path = tmp.name
            
            try:
                text = self.ocr_image(tmp_path)
                return text
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            error_msg = f"PaddleOCR on image array failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise OCRUnavailableError(error_msg) from e
    
    def close(self) -> None:
        """Release resources."""
        self._ocr = None
        logger.debug("PaddleOCR engine closed")
    
    def __enter__(self) -> "PaddleOCREngine":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


# Global PaddleOCR instance
_paddle_ocr: Optional[PaddleOCREngine] = None


def get_paddle_ocr() -> PaddleOCREngine:
    """Get the global PaddleOCR instance."""
    global _paddle_ocr
    if _paddle_ocr is None:
        _paddle_ocr = PaddleOCREngine()
    return _paddle_ocr