"""Domain-specific constants for the engineering document control system."""
from enum import Enum


class Discipline(str, Enum):
    """Engineering disciplines supported by the system."""
    ELC = "ELC"  # Electrical
    MEC = "MEC"  # Mechanical
    INS = "INS"  # Instrumentation
    SIM = "SIM"  # Simulation


class IssueStatus(str, Enum):
    """Document issue status codes per engineering document control standards."""
    IFR = "IFR"  # Issued for Review
    IFA = "IFA"  # Issued for Approval
    IFC = "IFC"  # Issued for Construction
    ASB = "ASB"  # As Built
    IFI = "IFI"  # Issued for Information


class DocumentStatus(str, Enum):
    """Internal document processing status."""
    CHECKING = "Checking"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class ValidationRuleType(str, Enum):
    """Types of validation rules."""
    WARNING = "warning"
    BLOCKING = "blocking"


class ChunkLevel(str, Enum):
    """Chunk hierarchy levels for parent-child retrieval."""
    PARENT = "parent"
    CHILD = "child"


class ConfidenceLevel(str, Enum):
    """Q&A answer confidence levels."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class SubmissionStatus(str, Enum):
    """Document Controller submission status."""
    PASS = "pass"
    FAIL = "fail"


# Document number pattern: [A-Z]{2,4}-[A-Z]-[A-Z]{2}-\d{2}-\d{3}
# Examples: ARG-E-OD-00-006, EPC-M-ELE-01-001
DOCUMENT_NUMBER_PATTERN = r"[A-Z]{2,4}-[A-Z]-[A-Z]{2}-\d{2}-\d{3}"

# OCR Configuration
OCR_CONFIDENCE_THRESHOLD = 0.75
OCR_DPI = 300
OCR_FALLBACK_DPI = 150
NATIVE_TEXT_THRESHOLD = 50  # characters; below this triggers OCR fallback

# Chunking Configuration
PARENT_CHUNK_SIZE = 1024
PARENT_CHUNK_OVERLAP = 128
CHILD_CHUNK_SIZE = 256
CHILD_CHUNK_OVERLAP = 32

# Embedding Configuration
EMBEDDING_DIMENSIONS = 384
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Vector Index Configuration
IVFFLAT_LISTS = 100

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".dwg",
    ".dxf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".tif",
}

# MIME type mapping
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".dwg": "image/vnd.dwg",
    ".dxf": "image/vnd.dxf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}

# Issue status tick-box labels for parsing
ISSUE_STATUS_LABELS = {
    "IFR": ["IFR", "Issued for Review"],
    "IFA": ["IFA", "Issued for Approval"],
    "IFC": ["IFC", "Issued for Construction"],
    "ASB": ["ASB", "As Built"],
    "IFI": ["IFI", "Issued for Information"],
}

# Signature block roles
SIGNATURE_ROLES = ["prepared_by", "checked_by", "approved_by"]