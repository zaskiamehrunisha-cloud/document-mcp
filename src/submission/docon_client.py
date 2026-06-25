"""Document Controller client for submitting approved documents."""
import logging
import json
from typing import Optional
from datetime import datetime

import httpx
from src.config.settings import settings
from src.common.exceptions import ExternalServiceError
from src.common.hashing import compute_file_hash

logger = logging.getLogger(__name__)


class DocumentControllerClient:
    """
    Client for submitting documents to the external Document Controller.
    Handles the handoff of conforming documents with full structured metadata.
    """
    
    def __init__(self):
        """Initialize Document Controller client."""
        self.api_url = settings.docon_api_url
        self.api_key = settings.docon_api_key
        self.timeout = settings.docon_timeout
    
    async def submit_document(
        self,
        document_id: int,
        file_hash: str,
        file_extension: str,
        parsed_data: dict,
        discipline: str,
        model_version: str,
    ) -> dict:
        """
        Submit a document to the Document Controller.
        
        Args:
            document_id: Database ID of the document
            file_hash: SHA-256 hash of the file
            file_extension: File extension
            parsed_data: Parsed document data
            discipline: Discipline tag (ELC/MEC/INS/SIM)
            model_version: Model version used for extraction
            
        Returns:
            Dictionary with submission result and confirmation reference
        """
        try:
            # Build submission payload
            payload = self._build_submission_payload(
                document_id,
                file_hash,
                file_extension,
                parsed_data,
                discipline,
                model_version,
            )
            
            # Submit to Document Controller
            confirmation_ref = await self._send_submission(payload)
            
            # Build result
            result = {
                "document_id": document_id,
                "status": "submitted",
                "confirmation_ref": confirmation_ref,
                "submitted_at": datetime.utcnow().isoformat(),
                "discipline": discipline,
            }
            
            logger.info(
                f"Document {document_id} submitted to Document Controller: "
                f"ref={confirmation_ref}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Document Controller submission failed for {document_id}: {e}")
            raise ExternalServiceError(f"Submission failed: {e}") from e
    
    def _build_submission_payload(
        self,
        document_id: int,
        file_hash: str,
        file_extension: str,
        parsed_data: dict,
        discipline: str,
        model_version: str,
    ) -> dict:
        """
        Build the submission payload for the Document Controller.
        
        Args:
            document_id: Database ID
            file_hash: SHA-256 hash
            file_extension: File extension
            parsed_data: Parsed document data
            discipline: Discipline tag
            model_version: Model version
            
        Returns:
            Payload dictionary
        """
        # Build structured metadata
        metadata = {
            "document_id": document_id,
            "file_hash": file_hash,
            "file_extension": file_extension,
            "discipline": discipline,
            "model_version": model_version,
            "submission_timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add extracted structured data
        if hasattr(parsed_data, "document_number") and parsed_data.document_number:
            metadata["document_number"] = parsed_data.document_number
        if hasattr(parsed_data, "title") and parsed_data.title:
            metadata["title"] = parsed_data.title
        if hasattr(parsed_data, "revision") and parsed_data.revision:
            metadata["revision"] = parsed_data.revision
        if hasattr(parsed_data, "issue_status") and parsed_data.issue_status:
            metadata["issue_status"] = parsed_data.issue_status
        if hasattr(parsed_data, "contract_number") and parsed_data.contract_number:
            metadata["contract_number"] = parsed_data.contract_number
        if hasattr(parsed_data, "page_count") and parsed_data.page_count:
            metadata["page_count"] = parsed_data.page_count
        
        # Add revision history
        if hasattr(parsed_data, "revision_history") and parsed_data.revision_history:
            metadata["revision_history"] = parsed_data.revision_history
        
        # Add comments/response
        if hasattr(parsed_data, "comments") and parsed_data.comments:
            metadata["comments"] = parsed_data.comments
        
        # Add equipment ratings
        if hasattr(parsed_data, "equipment_ratings") and parsed_data.equipment_ratings:
            metadata["equipment_ratings"] = parsed_data.equipment_ratings
        
        # Add legend symbols
        if hasattr(parsed_data, "legend_symbols") and parsed_data.legend_symbols:
            metadata["legend_symbols"] = parsed_data.legend_symbols
        
        # Add drawing index
        if hasattr(parsed_data, "drawing_index") and parsed_data.drawing_index:
            metadata["drawing_index"] = parsed_data.drawing_index
        
        # Build full payload
        payload = {
            "submission_type": "engineering_document",
            "discipline": discipline,
            "metadata": metadata,
            "file_info": {
                "hash": file_hash,
                "extension": file_extension,
            },
        }
        
        return payload
    
    async def _send_submission(self, payload: dict) -> str:
        """
        Send submission to Document Controller API.
        
        Args:
            payload: Submission payload
            
        Returns:
            Confirmation reference from Document Controller
            
        Raises:
            ExternalServiceError: If submission fails
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                )
                
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                
                # Extract confirmation reference
                confirmation_ref = result.get("confirmation_ref") or result.get("reference") or result.get("id")
                
                if not confirmation_ref:
                    raise ExternalServiceError(
                        "Document Controller did not return a confirmation reference"
                    )
                
                return str(confirmation_ref)
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Document Controller HTTP error: {e.response.status_code} - {e.response.text}")
            raise ExternalServiceError(
                f"Document Controller returned error: {e.response.status_code}"
            ) from e
        except httpx.TimeoutException:
            logger.error("Document Controller request timeout")
            raise ExternalServiceError("Document Controller request timeout") from None
        except Exception as e:
            logger.error(f"Document Controller request failed: {e}")
            raise ExternalServiceError(f"Submission request failed: {e}") from e
    
    async def check_status(self, confirmation_ref: str) -> dict:
        """
        Check submission status with Document Controller.
        
        Args:
            confirmation_ref: Confirmation reference from submission
            
        Returns:
            Status dictionary
        """
        try:
            status_url = f"{self.api_url}/{confirmation_ref}/status"
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(status_url, headers=headers)
                response.raise_for_status()
                return response.json()
        
        except Exception as e:
            logger.error(f"Failed to check submission status: {e}")
            raise ExternalServiceError(f"Status check failed: {e}") from e


# Global Document Controller client instance
docon_client = DocumentControllerClient()