"""
Application-wide constants for DOCINTEL.
Centralizes magic numbers, regex patterns, and fixed strings.
"""

import re

# ---------------------------------------------------------------------------
# Application Metadata
# ---------------------------------------------------------------------------

APP_NAME = "docintel"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "Engineering Document Intelligence MCP Server"

# ---------------------------------------------------------------------------
# Supported File Formats
# ---------------------------------------------------------------------------

SUPPORTED_MIME_TYPES: dict[str, str] = {
    # PDF
    "application/pdf": "pdf",
    # AutoCAD
    "image/vnd.dwg": "dwg",
    "image/vnd.dxf": "dxf",
    "application/dxf": "dxf",
    # Microsoft Office
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    # Fallbacks by extension
    ".pdf": "pdf",
    ".dwg": "dwg",
    ".dxf": "dxf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
}

SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".dwg", ".dxf", ".docx", ".xlsx", ".pptx"}

# ---------------------------------------------------------------------------
# Document Number Grammar
# ---------------------------------------------------------------------------

DOCUMENT_NUMBER_REGEX: str = r"^[A-Z]{3}-[A-Z]-[A-Z]{2}-\d{2}-\d{3}$"
DOCUMENT_NUMBER_PATTERN = re.compile(DOCUMENT_NUMBER_REGEX)

# ---------------------------------------------------------------------------
# Title Block Field Patterns
# ---------------------------------------------------------------------------

TITLE_BLOCK_FIELDS: list[str] = [
    "DOCUMENT NO.",
    "CONTRACTOR DOC NO.",
    "REV.",
    "CONTRACT NO.",
    "PAGE",
    "CLIENT",
    "PROJECT TITLE",
    "DOC. TITLE",
]

# ---------------------------------------------------------------------------
# Revision / Issue Status Ladder
# ---------------------------------------------------------------------------

REVISION_LADDER: list[dict[str, str]] = [
    {"code": "A", "description": "Issued for Review", "short": "IFR"},
    {"code": "B", "description": "Issued for Approval", "short": "IFA"},
    {"code": "0", "description": "Issued for Construction", "short": "IFC"},
    {"code": "1", "description": "Re-Issued for Construction", "short": "Re-IFC"},
    {"code": "ASB", "description": "As-Built", "short": "ASB"},
    {"code": "IFI", "description": "Issued for Information", "short": "IFI"},
]

REVISION_CODES: set[str] = {r["code"] for r in REVISION_LADDER}
ISSUE_STATUS_CODES: set[str] = {r["short"] for r in REVISION_LADDER}

# ---------------------------------------------------------------------------
# Mandatory Administrative Sheets
# ---------------------------------------------------------------------------

MANDATORY_SHEETS: list[str] = [
    "COMMENTS RESPONSE SHEET",
    "RECORD OF REVISION",
]

# ---------------------------------------------------------------------------
# Default Thresholds
# ---------------------------------------------------------------------------

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.6
DEFAULT_OCR_CONFIDENCE_THRESHOLD: float = 0.7
DEFAULT_TITLE_BLOCK_MATCH_THRESHOLD: float = 0.8

# ---------------------------------------------------------------------------
# Chunking Defaults
# ---------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE: int = 512
DEFAULT_CHUNK_OVERLAP: int = 50

# ---------------------------------------------------------------------------
# Pagination Defaults
# ---------------------------------------------------------------------------

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# ---------------------------------------------------------------------------
# Vector Search Defaults
# ---------------------------------------------------------------------------

DEFAULT_TOP_K: int = 5
MAX_TOP_K: int = 50

# ---------------------------------------------------------------------------
# Source Layer Labels
# ---------------------------------------------------------------------------

SOURCE_LAYER_NATIVE: str = "native"
SOURCE_LAYER_OCR: str = "ocr"

# ---------------------------------------------------------------------------
# Submission Outcomes
# ---------------------------------------------------------------------------

OUTCOME_PASS: str = "pass"
OUTCOME_FAIL: str = "fail"

# ---------------------------------------------------------------------------
# HTTP Status Codes (aliases for readability)
# ---------------------------------------------------------------------------

HTTP_200_OK: int = 200
HTTP_201_CREATED: int = 201
HTTP_400_BAD_REQUEST: int = 400
HTTP_404_NOT_FOUND: int = 404
HTTP_422_UNPROCESSABLE_ENTITY: int = 422
HTTP_500_INTERNAL_SERVER_ERROR: int = 500

# ---------------------------------------------------------------------------
# Regex Patterns for Title Block Extraction
# ---------------------------------------------------------------------------

# Matches "Page X of Y" or "Page X/Y"
PAGE_NUMBER_PATTERN = re.compile(r"Page\s+\d+\s*(?:of|\/)\s*\d+", re.IGNORECASE)

# Matches dates like "02-Feb-25" or "19-Dec-2025"
DATE_PATTERN = re.compile(r"\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}")

# Matches revision codes like "A", "B", "0", "1", "ASB", "IFI"
REVISION_CODE_PATTERN = re.compile(r"\b([A-Z]|\d{1,2}|ASB|IFI)\b")

# Matches issue status keywords
ISSUE_STATUS_PATTERN = re.compile(
    r"\b(IFR|IFA|IFC|ASB|IFI|Re[- ]?IFC)\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Severity Levels
# ---------------------------------------------------------------------------

SEVERITY_ERROR: str = "error"
SEVERITY_WARNING: str = "warning"
SEVERITY_INFO: str = "info"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_FORMAT_JSON: str = "json"
LOG_FORMAT_CONSOLE: str = "console"