"""
Deterministic parser for DOCINTEL.
Extracts structured fields from engineering document text using regex and rules.
"""

import re
from typing import Any

from docintel.common.constants import (
    DOCUMENT_NUMBER_PATTERN,
    ISSUE_STATUS_PATTERN,
    MANDATORY_SHEETS,
    PAGE_NUMBER_PATTERN,
    REVISION_CODE_PATTERN,
    TITLE_BLOCK_FIELDS,
)
from docintel.common.logging import get_logger

logger = get_logger(__name__)


class DeterministicParser:
    """
    Parses engineering document text using deterministic rules.
    Extracts title block fields, revision history, comments, etc.
    """
    
    def __init__(self):
        """Initialize the deterministic parser."""
        pass
    
    def parse(self, text: str, file_type: str = "pdf") -> dict[str, Any]:
        """
        Parse text and extract structured fields.
        
        Args:
            text: Raw text from document
            file_type: Type of file (pdf, dxf, etc.)
            
        Returns:
            Dictionary of extracted fields
        """
        result: dict[str, Any] = {}
        
        # Extract core fields
        result["document_number"] = self._extract_document_number(text)
        result["title"] = self._extract_title(text)
        result["revision"] = self._extract_revision(text)
        result["contract_number"] = self._extract_contract_number(text)
        result["issue_status"] = self._extract_issue_status(text)
        result["client"] = self._extract_client(text)
        result["project_title"] = self._extract_project_title(text)
        result["location"] = self._extract_location(text)
        result["page"] = self._extract_page_number(text)
        result["sheet_count"] = self._extract_sheet_count(text)
        
        # Extract structured tables
        result["comments"] = self._extract_comments(text)
        result["revision_history"] = self._extract_revision_history(text)
        result["legend_entries"] = self._extract_legend(text)
        result["drawing_index"] = self._extract_drawing_index(text)
        result["equipment_ratings"] = self._extract_equipment_ratings(text)
        
        # Check for mandatory sheets
        result["mandatory_sheets_present"] = self._check_mandatory_sheets(text)
        
        logger.info(
            "Deterministic parsing complete",
            extra={
                "doc_number": result.get("document_number"),
                "revision": result.get("revision"),
                "fields_found": sum(1 for v in result.values() if v is not None and v != []),
            },
        )
        
        return result
    
    def _extract_document_number(self, text: str) -> str | None:
        """Extract document number from text."""
        # Look for patterns like ARG-E-LO-00-006
        match = DOCUMENT_NUMBER_PATTERN.search(text)
        if match:
            return match.group(0)
        
        # Try to find DOC. NO. field
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "DOC. NO." in line or "DOCUMENT NO." in line:
                # Check current and next line
                for j in range(i, min(i + 3, len(lines))):
                    match = DOCUMENT_NUMBER_PATTERN.search(lines[j])
                    if match:
                        return match.group(0)
        
        return None
    
    def _extract_title(self, text: str) -> str | None:
        """Extract document title."""
        lines = text.split("\n")
        
        # Look for DOC. TITLE field
        for i, line in enumerate(lines):
            if "DOC. TITLE" in line:
                # Title is usually on the same line or next line
                if ":" in line:
                    return line.split(":", 1)[1].strip()
                elif i + 1 < len(lines):
                    return lines[i + 1].strip()
        
        # Fallback: look for a line that looks like a title (all caps, reasonable length)
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if len(line) > 10 and len(line) < 200 and line.isupper() and not line.startswith("KSO"):
                return line
        
        return None
    
    def _extract_revision(self, text: str) -> str | None:
        """Extract revision code."""
        # Look for REV. field
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "REV." in line and "CONTRACT" not in line:
                # Extract revision code
                match = REVISION_CODE_PATTERN.search(line)
                if match:
                    return match.group(1)
                # Check next line
                if i + 1 < len(lines):
                    match = REVISION_CODE_PATTERN.search(lines[i + 1])
                    if match:
                        return match.group(1)
        
        return None
    
    def _extract_contract_number(self, text: str) -> str | None:
        """Extract contract number."""
        # Look for CONTRACT NO. field
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "CONTRACT NO." in line or "CONTRACTOR DOC NO." in line:
                # Extract number
                parts = line.split()
                for part in parts:
                    if part.isdigit() and len(part) >= 8:
                        return part
                # Check next line
                if i + 1 < len(lines):
                    parts = lines[i + 1].split()
                    for part in parts:
                        if part.isdigit() and len(part) >= 8:
                            return part
        
        return None
    
    def _extract_issue_status(self, text: str) -> str | None:
        """Extract issue status (IFR, IFA, IFC, etc.)."""
        match = ISSUE_STATUS_PATTERN.search(text)
        if match:
            return match.group(1).upper()
        return None
    
    def _extract_client(self, text: str) -> str | None:
        """Extract client name."""
        lines = text.split("\n")
        for line in lines[:30]:  # Check first 30 lines
            if "CLIENT" in line.upper():
                if ":" in line:
                    return line.split(":", 1)[1].strip()
                else:
                    # Client is usually on the next line
                    idx = lines.index(line)
                    if idx + 1 < len(lines):
                        return lines[idx + 1].strip()
        return None
    
    def _extract_project_title(self, text: str) -> str | None:
        """Extract project title."""
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "PROJECT TITLE" in line:
                if ":" in line:
                    return line.split(":", 1)[1].strip()
                elif i + 1 < len(lines):
                    return lines[i + 1].strip()
        return None
    
    def _extract_location(self, text: str) -> str | None:
        """Extract project location."""
        lines = text.split("\n")
        for line in lines[:30]:
            if "LOCATION" in line.upper():
                if ":" in line:
                    return line.split(":", 1)[1].strip()
                else:
                    idx = lines.index(line)
                    if idx + 1 < len(lines):
                        return lines[idx + 1].strip()
        return None
    
    def _extract_page_number(self, text: str) -> str | None:
        """Extract page number (e.g., 'Page 1 of 5')."""
        match = PAGE_NUMBER_PATTERN.search(text)
        if match:
            return match.group(0)
        return None
    
    def _extract_sheet_count(self, text: str) -> int | None:
        """Extract total sheet count from page number."""
        page_match = PAGE_NUMBER_PATTERN.search(text)
        if page_match:
            # Extract "of Y" part
            of_match = re.search(r"of\s+(\d+)", page_match.group(0), re.IGNORECASE)
            if of_match:
                return int(of_match.group(1))
        return None
    
    def _extract_comments(self, text: str) -> list[dict[str, Any]]:
        """Extract comment/response table."""
        comments = []
        
        # Look for COMMENTS RESPONSE SHEET section
        if "COMMENTS RESPONSE SHEET" not in text.upper():
            return comments
        
        lines = text.split("\n")
        in_comments = False
        current_comment = {}
        
        for line in lines:
            line = line.strip()
            if "COMMENTS RESPONSE SHEET" in line.upper():
                in_comments = True
                continue
            
            if in_comments:
                # Look for table headers
                if "NO." in line and "CLIENT COMMENT" in line.upper():
                    continue
                
                # Look for comment entries
                if line and not line.startswith("NO."):
                    # Try to parse comment row
                    parts = line.split()
                    if parts and parts[0].isdigit():
                        if current_comment:
                            comments.append(current_comment)
                        current_comment = {"comment_ref": parts[0]}
        
        if current_comment:
            comments.append(current_comment)
        
        return comments[:10]  # Limit to 10 comments
    
    def _extract_revision_history(self, text: str) -> list[dict[str, Any]]:
        """Extract revision history table."""
        revisions = []
        
        # Look for RECORD OF REVISION section
        if "RECORD OF REVISION" not in text.upper():
            return revisions
        
        lines = text.split("\n")
        in_revisions = False
        
        for line in lines:
            line = line.strip()
            if "RECORD OF REVISION" in line.upper():
                in_revisions = True
                continue
            
            if in_revisions:
                # Look for revision entries
                match = REVISION_CODE_PATTERN.search(line)
                if match:
                    rev_code = match.group(1)
                    revisions.append({
                        "revision": rev_code,
                        "description": line.strip(),
                    })
        
        return revisions[:20]  # Limit to 20 revisions
    
    def _extract_legend(self, text: str) -> list[dict[str, Any]]:
        """Extract legend/symbol entries."""
        legends = []
        
        # Look for LEGEND section
        if "LEGEND" not in text.upper():
            return legends
        
        lines = text.split("\n")
        in_legend = False
        
        for line in lines:
            line = line.strip()
            if "LEGEND" in line.upper() and ":" in line:
                in_legend = True
                continue
            
            if in_legend:
                # Look for symbol-description pairs
                if line and not line.startswith("LEGEND"):
                    parts = line.split(None, 1)
                    if len(parts) >= 2:
                        legends.append({
                            "symbol": parts[0],
                            "description": parts[1],
                        })
        
        return legends[:50]  # Limit to 50 entries
    
    def _extract_drawing_index(self, text: str) -> list[dict[str, Any]]:
        """Extract drawing index entries."""
        index_entries = []
        
        # Look for DRAWING INDEX section
        if "DRAWING INDEX" not in text.upper() and "INDEX" not in text.upper():
            return index_entries
        
        lines = text.split("\n")
        
        # Look for lines that match document number pattern
        for line in lines:
            match = DOCUMENT_NUMBER_PATTERN.search(line)
            if match:
                parts = line.split()
                if len(parts) >= 2:
                    index_entries.append({
                        "drawing_number": match.group(0),
                        "drawing_title": " ".join(parts[1:]),
                    })
        
        return index_entries[:100]  # Limit to 100 entries
    
    def _extract_equipment_ratings(self, text: str) -> list[dict[str, Any]]:
        """Extract equipment ratings."""
        ratings = []
        
        # Look for voltage/current/power patterns
        # e.g., "24 VDC", "230 V 50 Hz", "10 kW"
        patterns = [
            r"(\d+)\s*(V|kV|A|kW|Hz|W)\s*(DC|AC)?",
            r"(\d+)\s*(VDC|VAC|Hz)",
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                ratings.append({
                    "parameter": "Electrical Rating",
                    "value": match.group(0),
                })
        
        return ratings[:50]  # Limit to 50 ratings
    
    def _check_mandatory_sheets(self, text: str) -> bool:
        """Check if mandatory administrative sheets are present."""
        text_upper = text.upper()
        for sheet in MANDATORY_SHEETS:
            if sheet.upper() in text_upper:
                return True
        return False


# Global parser instance
_deterministic_parser: DeterministicParser | None = None


def get_deterministic_parser() -> DeterministicParser:
    """Get the global deterministic parser instance."""
    global _deterministic_parser
    if _deterministic_parser is None:
        _deterministic_parser = DeterministicParser()
    return _deterministic_parser