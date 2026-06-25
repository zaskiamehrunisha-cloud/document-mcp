"""Custom exceptions for the engineering document control system."""


class DocumentControlError(Exception):
    """Base exception for all document control errors."""
    pass


class IngestionError(DocumentControlError):
    """Raised when document ingestion fails."""
    pass


class OCRError(DocumentControlError):
    """Raised when OCR processing fails."""
    pass


class ParseError(DocumentControlError):
    """Raised when document parsing fails."""
    pass


class ValidationError(DocumentControlError):
    """Raised when document validation fails."""
    pass


class EmbeddingError(DocumentControlError):
    """Raised when embedding generation fails."""
    pass


class LLMError(DocumentControlError):
    """Raised when LLM inference fails."""
    pass


class DatabaseError(DocumentControlError):
    """Raised when database operations fail."""
    pass


class FileStorageError(DocumentControlError):
    """Raised when file storage operations fail."""
    pass


class AuthenticationError(DocumentControlError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(DocumentControlError):
    """Raised when authorization fails."""
    pass


class ExternalServiceError(DocumentControlError):
    """Raised when external service integration fails."""
    pass