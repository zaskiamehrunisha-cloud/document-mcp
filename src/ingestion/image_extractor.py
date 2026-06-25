"""Image extractor for raster images (PNG, JPG, TIFF) with OCR."""
import logging
from pathlib import Path
from typing import Optional

from src.ocr.engine import ocr_engine
from src.ocr.confidence import ConfidenceGate
from src.common.exceptions import IngestionError, OCRError

logger = logging.getLogger(__name__)


class ImageExtractor:
    """
    Image extractor for raster images.
    Routes directly through OCR while preserving bounding-box geometry.
    """
    
    def __init__(self):
        """Initialize image extractor."""
        self.confidence_gate = ConfidenceGate()
    
    def extract(self, file_path: Path, page_count: Optional[int] = None) -> dict:
        """
        Extract text from image using OCR.
        
        Args:
            file_path: Path to image file
            page_count: Optional known page count (default 1 for images)
            
        Returns:
            Dictionary with extracted text, blocks, and low-confidence regions
        """
        try:
            # Load image
            image = self._load_image(file_path)
            
            # Perform OCR
            blocks = ocr_engine.ocr_image(image, page=1)
            
            # Apply confidence gating
            passing_blocks, low_conf = self.confidence_gate.evaluate(
                blocks, document_id=0  # Will be set later
            )
            
            # Collect text
            text = "\n".join(block.text for block in passing_blocks)
            
            logger.info(
                f"Image OCR complete: {len(blocks)} blocks detected, "
                f"{len(passing_blocks)} passing, {len(low_conf)} low-confidence"
            )
            
            return {
                "text": text,
                "blocks": blocks,
                "low_confidence_regions": low_conf,
                "page_count": 1,
                "extraction_method": "ocr",
                "image_size": image.size,
            }
        
        except Exception as e:
            logger.error(f"Image extraction failed: {e}", exc_info=True)
            raise IngestionError(f"Image extraction failed: {e}") from e
    
    def _load_image(self, file_path: Path):
        """
        Load image from file.
        
        Args:
            file_path: Path to image file
            
        Returns:
            PIL Image object
        """
        try:
            from PIL import Image
            return Image.open(file_path)
        except ImportError:
            raise OCRError("PIL/Pillow is required for image loading")
        except Exception as e:
            raise OCRError(f"Failed to load image: {e}")


# Global image extractor instance
image_extractor = ImageExtractor()