"""
Custom exceptions for the DOCINTEL application.
Provides typed, descriptive errors for all failure modes.
"""

from typing import Optional


class DocIntelError(Exception):
    """Base exception for all DOCINTEL errors."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Extraction / OCR Errors
# ---------------------------------------------------------------------------

class ExtractionError(DocIntelError):
    """Raised when file extraction fails."""
    pass


class OCRUnavailableError(DocIntelError):
    """Raised when OCR engine is unavailable or fails."""
    pass


class UnsupportedFormatError(DocIntelError):
    """Raised when a file format is not supported."""
    
    def __init__(self, file_type: str, supported_types: list[str], **kwargs):
        message = f"Unsupported file format: {file_type}. Supported: {', '.join(supported_types)}"
        super().__init__(message, details={"file_type": file_type, "supported": supported_types}, **kwargs)


class NativeTextLayerUnreliableError(DocIntelError):
    """Raised when native text layer exists but is unreliable, requiring OCR fallback."""
    pass


# ---------------------------------------------------------------------------
# Parsing Errors
# ---------------------------------------------------------------------------

class ParseError(DocIntelError):
    """Raised when structured record parsing fails."""
    pass


class LLMInferenceError(DocIntelError):
    """Raised when the local LLM inference fails."""
    pass


class ConfidenceThresholdError(DocIntelError):
    """Raised when extraction confidence is below the configured threshold."""
    
    def __init__(self, confidence: float, threshold: float, **kwargs):
        message = f"Extraction confidence {confidence:.2f} is below threshold {threshold:.2f}"
        super().__init__(
            message,
            details={"confidence": confidence, "threshold": threshold},
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Validation Errors
# ---------------------------------------------------------------------------

class ValidationError(DocIntelError):
    """Raised when document validation fails."""
    
    def __init__(self, violations: list[dict], **kwargs):
        self.violations = violations
        message = f"Document validation failed with {len(violations)} violation(s)"
        super().__init__(message, details={"violations": violations}, **kwargs)


class RuleDerivationError(DocIntelError):
    """Raised when validation rules cannot be derived from reference documents."""
    pass


# ---------------------------------------------------------------------------
# Persistence Errors
# ---------------------------------------------------------------------------

class DatabaseError(DocIntelError):
    """Raised on database operation failures."""
    pass


class DocumentNotFoundError(DocIntelError):
    """Raised when a requested document does not exist."""
    
    def __init__(self, document_id: int, **kwargs):
        message = f"Document with ID {document_id} not found"
        super().__init__(message, details={"document_id": document_id}, **kwargs)


class DuplicateDocumentError(DocIntelError):
    """Raised when attempting to ingest a duplicate document."""
    
    def __init__(self, document_number: str, **kwargs):
        message = f"Document {document_number} already exists in the knowledge base"
        super().__init__(message, details={"document_number": document_number}, **kwargs)


# ---------------------------------------------------------------------------
# DOCON Errors
# ---------------------------------------------------------------------------

class DocONError(DocIntelError):
    """Raised when DOCON submission fails."""
    pass


class DocONConnectionError(DocONError):
    """Raised when the DOCON system is unreachable."""
    pass


# ---------------------------------------------------------------------------
# Retrieval / Embedding Errors
# ---------------------------------------------------------------------------

class EmbeddingError(DocIntelError):
    """Raised when embedding generation fails."""
    pass


class SearchError(DocIntelError):
    """Raised when semantic search fails."""
    pass


# ---------------------------------------------------------------------------
# Security / Offline Guard Errors
# ---------------------------------------------------------------------------

class OfflineGuardViolationError(DocIntelError):
    """Raised when an attempt is made to call a non-local/cloud endpoint."""
    
    def __init__(self, host: str, allowed_hosts: list[str], **kwargs):
        message = f"Offline guard violation: host '{host}' is not in the allowed list: {allowed_hosts}"
        super().__init__(
            message,
            details={"host": host, "allowed_hosts": allowed_hosts},
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Configuration Errors
# ---------------------------------------------------------------------------

class ConfigurationError(DocIntelError):
    """Raised when configuration is missing or invalid."""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when a required configuration value is missing."""
    
    def __init__(self, key: str, **kwargs):
        message = f"Missing required configuration: {key}"
        super().__init__(message, details={"key": key}, **kwargs)