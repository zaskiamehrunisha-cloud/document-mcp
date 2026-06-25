"""Audit trail utilities for logging system events."""
from datetime import datetime, timezone
from typing import Any, Optional
import json
import logging

from src.config.settings import settings

logger = logging.getLogger(__name__)


class AuditEvent:
    """Represents a single audit event."""
    
    def __init__(
        self,
        event_type: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        file_hash: Optional[str] = None,
        model_version: Optional[str] = None,
        confidence_score: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize an audit event.
        
        Args:
            event_type: Type of event (e.g., 'ocr', 'parse', 'validate', 'qa')
            entity_type: Type of entity (e.g., 'document', 'chunk', 'review')
            entity_id: Optional database ID of the entity
            file_hash: SHA-256 hash of the processed file
            model_version: Version of the model used
            confidence_score: Confidence score if applicable
            metadata: Additional event-specific data
        """
        self.event_type = event_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.file_hash = file_hash
        self.model_version = model_version
        self.confidence_score = confidence_score
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert audit event to dictionary for logging/storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "file_hash": self.file_hash,
            "model_version": self.model_version,
            "confidence_score": self.confidence_score,
            "metadata": self.metadata,
        }
    
    def log(self) -> None:
        """Log the audit event."""
        event_dict = self.to_dict()
        logger.info(
            f"AUDIT: {self.event_type}",
            extra={"audit_event": event_dict}
        )


def create_ocr_audit(
    document_id: int,
    file_hash: str,
    model_version: str,
    confidence_score: float,
    page: int,
    block_count: int,
    low_confidence_count: int,
) -> AuditEvent:
    """
    Create an audit event for OCR processing.
    
    Args:
        document_id: ID of the document being processed
        file_hash: SHA-256 hash of the file
        model_version: Version of the OCR model
        confidence_score: Average confidence score
        page: Page number processed
        block_count: Total text blocks detected
        low_confidence_count: Blocks below confidence threshold
        
    Returns:
        AuditEvent instance
    """
    return AuditEvent(
        event_type="ocr",
        entity_type="document",
        entity_id=document_id,
        file_hash=file_hash,
        model_version=model_version,
        confidence_score=confidence_score,
        metadata={
            "page": page,
            "block_count": block_count,
            "low_confidence_count": low_confidence_count,
        },
    )


def create_parse_audit(
    document_id: int,
    file_hash: str,
    model_version: str,
    parser_type: str,
    success: bool,
    extracted_fields: Optional[list[str]] = None,
) -> AuditEvent:
    """
    Create an audit event for document parsing.
    
    Args:
        document_id: ID of the document being parsed
        file_hash: SHA-256 hash of the file
        model_version: Version of the parser/model
        parser_type: Type of parser (deterministic, llm, merge)
        success: Whether parsing succeeded
        extracted_fields: List of successfully extracted fields
        
    Returns:
        AuditEvent instance
    """
    return AuditEvent(
        event_type="parse",
        entity_type="document",
        entity_id=document_id,
        file_hash=file_hash,
        model_version=model_version,
        metadata={
            "parser_type": parser_type,
            "success": success,
            "extracted_fields": extracted_fields or [],
        },
    )


def create_validation_audit(
    document_id: int,
    file_hash: str,
    model_version: str,
    passed: bool,
    rules_evaluated: int,
    rules_failed: int,
    rejection_note: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    """
    Create an audit event for validation.
    
    Args:
        document_id: ID of the document being validated
        file_hash: SHA-256 hash of the file
        model_version: Version of the validation rules
        passed: Whether validation passed
        rules_evaluated: Number of rules evaluated
        rules_failed: Number of rules that failed
        rejection_note: JSONB rejection note if validation failed
        
    Returns:
        AuditEvent instance
    """
    return AuditEvent(
        event_type="validate",
        entity_type="document",
        entity_id=document_id,
        file_hash=file_hash,
        model_version=model_version,
        metadata={
            "passed": passed,
            "rules_evaluated": rules_evaluated,
            "rules_failed": rules_failed,
            "rejection_note": rejection_note,
        },
    )


def create_qa_audit(
    query_text: str,
    answer: str,
    confidence_level: str,
    cited_document_ids: list[int],
    retrieved_chunk_ids: list[int],
    model_version: str,
) -> AuditEvent:
    """
    Create an audit event for Q&A query.
    
    Args:
        query_text: The user's query
        answer: Generated answer
        confidence_level: High/Medium/Low
        cited_document_ids: List of cited document IDs
        retrieved_chunk_ids: List of retrieved chunk IDs
        model_version: Version of the LLM model
        
    Returns:
        AuditEvent instance
    """
    return AuditEvent(
        event_type="qa",
        entity_type="query",
        metadata={
            "query_text": query_text,
            "answer": answer,
            "confidence_level": confidence_level,
            "cited_document_ids": cited_document_ids,
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "model_version": model_version,
        },
    )