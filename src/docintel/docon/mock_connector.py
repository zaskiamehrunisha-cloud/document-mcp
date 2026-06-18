"""
Mock DOCON connector for DOCINTEL.
Simulates DOCON submission for MVP/testing.
"""

import time
import uuid
from typing import Any

from docintel.common.exceptions import DocONError
from docintel.common.logging import get_logger

logger = get_logger(__name__)


class MockDoconConnector:
    """
    Mock DOCON connector for development and testing.
    Simulates document submission without a real DOCON system.
    """
    
    def __init__(self):
        """Initialize the mock connector."""
        self.submissions: dict[str, dict[str, Any]] = {}
        logger.info("Mock DOCON connector initialized")
    
    async def submit(
        self,
        document_id: int,
        structured_record: dict[str, Any],
        file_path: str,
        discipline: str,
    ) -> dict[str, Any]:
        """
        Simulate submitting a document to DOCON.
        
        Args:
            document_id: Database ID of the document
            structured_record: Parsed structured record
            file_path: Path to the document file
            discipline: Submitting discipline
            
        Returns:
            Submission receipt with mock DOCON reference
        """
        try:
            # Generate a mock DOCON reference
            docon_ref = f"DOCON-{uuid.uuid4().hex[:8].upper()}"
            
            receipt = {
                "docon_reference": docon_ref,
                "status": "submitted",
                "submitted_at": time.time(),
                "document_id": document_id,
                "discipline": discipline,
                "document_number": structured_record.get("document_number"),
                "title": structured_record.get("title"),
            }
            
            # Store the submission
            self.submissions[docon_ref] = receipt
            
            logger.info(
                "Mock DOCON submission complete",
                extra={
                    "docon_ref": docon_ref,
                    "document_id": document_id,
                    "discipline": discipline,
                },
            )
            
            return receipt
            
        except Exception as e:
            error_msg = f"Mock DOCON submission failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise DocONError(error_msg) from e
    
    async def check_status(self, docon_reference: str) -> dict[str, Any]:
        """
        Check the status of a mock submission.
        
        Args:
            docon_reference: DOCON reference number
            
        Returns:
            Status information
        """
        if docon_reference not in self.submissions:
            return {
                "docon_reference": docon_reference,
                "status": "not_found",
                "message": "Submission not found",
            }
        
        submission = self.submissions[docon_reference]
        return {
            "docon_reference": docon_reference,
            "status": submission["status"],
            "submitted_at": submission["submitted_at"],
            "document_number": submission.get("document_number"),
        }
    
    def is_available(self) -> bool:
        """
        Mock connector is always available.
        
        Returns:
            Always True
        """
        return True
    
    def clear(self) -> None:
        """Clear all mock submissions (for testing)."""
        self.submissions.clear()
        logger.debug("Mock DOCON submissions cleared")