"""
DOCON connector interface for DOCINTEL.
Abstract base class for DOCON integration.
"""

from abc import ABC, abstractmethod
from typing import Any

from docintel.common.exceptions import DocONError, DocONConnectionError
from docintel.common.logging import get_logger

logger = get_logger(__name__)


class DoconConnector(ABC):
    """
    Abstract base class for DOCON connectors.
    Implementations handle the actual DOCON integration.
    """
    
    @abstractmethod
    async def submit(
        self,
        document_id: int,
        structured_record: dict[str, Any],
        file_path: str,
        discipline: str,
    ) -> dict[str, Any]:
        """
        Submit a document to DOCON.
        
        Args:
            document_id: Database ID of the document
            structured_record: Parsed structured record
            file_path: Path to the document file
            discipline: Submitting discipline
            
        Returns:
            Submission receipt with DOCON reference
            
        Raises:
            DocONError: If submission fails
            DocONConnectionError: If DOCON is unreachable
        """
        pass
    
    @abstractmethod
    async def check_status(self, docon_reference: str) -> dict[str, Any]:
        """
        Check the status of a submitted document.
        
        Args:
            docon_reference: DOCON reference number
            
        Returns:
            Status information
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the DOCON system is available.
        
        Returns:
            True if available, False otherwise
        """
        pass