"""OCR confidence gating - routes low-confidence blocks to review queue."""
import logging
from typing import Optional

from src.db.models import LowConfidenceRegion
from src.common.constants import OCR_CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)


class ConfidenceGate:
    """
    Gates OCR blocks based on confidence threshold.
    Blocks below threshold are flagged for human review.
    """
    
    def __init__(self, threshold: float = OCR_CONFIDENCE_THRESHOLD):
        """
        Initialize confidence gate.
        
        Args:
            threshold: Minimum confidence score (0-1) for acceptance
        """
        self.threshold = threshold
    
    def evaluate(
        self,
        blocks: list,
        document_id: int,
    ) -> tuple[list, list[LowConfidenceRegion]]:
        """
        Evaluate OCR blocks and split into passing and low-confidence groups.
        
        Args:
            blocks: List of OCR text blocks
            document_id: ID of the document being processed
            
        Returns:
            Tuple of (passing_blocks, low_confidence_regions)
        """
        passing = []
        low_confidence_regions = []
        
        for block in blocks:
            if block.confidence >= self.threshold:
                passing.append(block)
            else:
                # Create low-confidence region for review queue
                region = LowConfidenceRegion(
                    document_id=document_id,
                    page=block.page,
                    bbox={"bbox": block.bbox},  # JSONB format
                    text=block.text,
                    confidence=block.confidence,
                    reviewed=False,
                )
                low_confidence_regions.append(region)
        
        if low_confidence_regions:
            logger.info(
                f"Flagged {len(low_confidence_regions)} low-confidence regions "
                f"for document {document_id}"
            )
        
        return passing, low_confidence_regions
    
    def get_statistics(self, blocks: list) -> dict:
        """
        Get confidence statistics for a set of blocks.
        
        Args:
            blocks: List of OCR text blocks
            
        Returns:
            Dictionary with confidence statistics
        """
        if not blocks:
            return {
                "total_blocks": 0,
                "passing_blocks": 0,
                "low_confidence_blocks": 0,
                "avg_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
            }
        
        confidences = [block.confidence for block in blocks]
        passing = [c for c in confidences if c >= self.threshold]
        low_conf = [c for c in confidences if c < self.threshold]
        
        return {
            "total_blocks": len(blocks),
            "passing_blocks": len(passing),
            "low_confidence_blocks": len(low_conf),
            "avg_confidence": sum(confidences) / len(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
        }