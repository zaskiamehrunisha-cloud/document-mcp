"""OCR engine with PaddleOCR primary and Tesseract fallback."""
import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
import pytesseract
from paddleocr import PaddleOCR

from src.config.settings import settings
from src.common.exceptions import OCRError
from src.common.constants import OCR_CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)


class TextBlock:
    """Represents a detected text block from OCR."""
    
    def __init__(
        self,
        text: str,
        confidence: float,
        bbox: list[float],  # [x1, y1, x2, y2]
        page: int,
    ):
        """
        Initialize a text block.
        
        Args:
            text: Extracted text content
            confidence: OCR confidence score (0-1)
            bbox: Bounding box coordinates [x1, y1, x2, y2]
            page: Page number
        """
        self.text = text
        self.confidence = confidence
        self.bbox = bbox
        self.page = page
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "page": self.page,
        }


class OCREngine:
    """
    OCR engine with PaddleOCR primary and Tesseract fallback.
    Renders pages at 300 DPI and emits per-block confidence scores.
    """
    
    def __init__(self):
        """Initialize OCR engines."""
        self.paddle_ocr: Optional[PaddleOCR] = None
        self.use_gpu = settings.ocr_use_gpu
        self._initialize_paddle()
    
    def _initialize_paddle(self) -> None:
        """Initialize PaddleOCR engine."""
        try:
            # PaddleOCR 3.x API
            self.paddle_ocr = PaddleOCR(
                use_textline_orientation=True,  # Replaces use_angle_cls in 3.x
                lang=settings.ocr_lang,
                use_gpu=self.use_gpu,
                show_log=False,
            )
            logger.info("PaddleOCR initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize PaddleOCR: {e}. Will use Tesseract fallback.")
            self.paddle_ocr = None
    
    def ocr_image(self, image: Image.Image, page: int = 1) -> list[TextBlock]:
        """
        Perform OCR on an image.
        
        Args:
            image: PIL Image to process
            page: Page number for tracking
            
        Returns:
            List of TextBlock objects with text, confidence, and bbox
        """
        # Try PaddleOCR first
        if self.paddle_ocr is not None:
            try:
                return self._ocr_paddle(image, page)
            except Exception as e:
                logger.warning(f"PaddleOCR failed: {e}. Falling back to Tesseract.")
        
        # Fallback to Tesseract
        return self._ocr_tesseract(image, page)
    
    def _ocr_paddle(self, image: Image.Image, page: int) -> list[TextBlock]:
        """
        OCR using PaddleOCR.
        
        Args:
            image: PIL Image
            page: Page number
            
        Returns:
            List of TextBlock objects
        """
        # Convert PIL Image to numpy array
        img_array = np.array(image)
        
        # Run PaddleOCR
        result = self.paddle_ocr.ocr(img_array, cls=True)
        
        text_blocks = []
        
        # PaddleOCR 3.x returns a list of results per page
        if result and result[0]:
            for line in result[0]:
                if line:
                    bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    text_info = line[1]
                    text = text_info[0]
                    confidence = text_info[1]
                    
                    # Convert bbox to [x1, y1, x2, y2] format
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    bbox_flat = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
                    
                    text_blocks.append(TextBlock(
                        text=text,
                        confidence=confidence,
                        bbox=bbox_flat,
                        page=page,
                    ))
        
        return text_blocks
    
    def _ocr_tesseract(self, image: Image.Image, page: int) -> list[TextBlock]:
        """
        OCR using Tesseract as fallback.
        
        Args:
            image: PIL Image
            page: Page number
            
        Returns:
            List of TextBlock objects
        """
        # Get OCR data with bounding boxes
        ocr_data = pytesseract.image_to_data(
            image,
            lang=settings.ocr_lang,
            output_type=pytesseract.Output.DICT,
        )
        
        text_blocks = []
        
        n_boxes = len(ocr_data["text"])
        for i in range(n_boxes):
            text = ocr_data["text"][i].strip()
            confidence = float(ocr_data["conf"][i]) / 100.0  # Convert to 0-1 range
            
            # Skip empty text and low-confidence detections
            if not text or confidence < 0.1:
                continue
            
            # Extract bounding box
            x = ocr_data["left"][i]
            y = ocr_data["top"][i]
            w = ocr_data["width"][i]
            h = ocr_data["height"][i]
            bbox = [x, y, x + w, y + h]
            
            text_blocks.append(TextBlock(
                text=text,
                confidence=confidence,
                bbox=bbox,
                page=page,
            ))
        
        return text_blocks
    
    def render_page_to_image(
        self,
        file_path: Path,
        page_number: int,
        dpi: int = 300,
    ) -> Image.Image:
        """
        Render a PDF page to an image at specified DPI.
        
        Args:
            file_path: Path to PDF file
            page_number: Page number (1-indexed)
            dpi: Resolution for rendering
            
        Returns:
            PIL Image of the rendered page
        """
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(file_path)
            page = doc[page_number - 1]  # Convert to 0-indexed
            
            # Render at specified DPI
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 is default PDF DPI
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            
            doc.close()
            return image
            
        except ImportError:
            logger.error("PyMuPDF not installed. Cannot render PDF pages.")
            raise OCRError("PyMuPDF is required for PDF rendering")
        except Exception as e:
            logger.error(f"Failed to render page {page_number}: {e}")
            raise OCRError(f"PDF rendering failed: {e}")
    
    def check_confidence(self, blocks: list[TextBlock]) -> tuple[list[TextBlock], list[TextBlock]]:
        """
        Split blocks into passing and low-confidence groups.
        
        Args:
            blocks: List of text blocks
            
        Returns:
            Tuple of (passing_blocks, low_confidence_blocks)
        """
        passing = []
        low_confidence = []
        
        for block in blocks:
            if block.confidence >= OCR_CONFIDENCE_THRESHOLD:
                passing.append(block)
            else:
                low_confidence.append(block)
        
        return passing, low_confidence


# Global OCR engine instance
ocr_engine = OCREngine()