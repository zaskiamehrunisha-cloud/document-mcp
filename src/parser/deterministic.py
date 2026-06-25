"""Deterministic parser for engineering documents - regex and position-based extraction."""
import logging
import re
from typing import Optional
from dataclasses import dataclass, field

from src.common.constants import (
    DOCUMENT_NUMBER_PATTERN,
    ISSUE_STATUS_LABELS,
    SIGNATURE_ROLES,
)
from src.common.exceptions import ParseError

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    """Structured data extracted from an engineering document."""
    document_number: Optional[str] = None
    title: Optional[str] = None
    revision: Optional[str] = None
    issue_status: Optional[str] = None
    contract_number: Optional[str] = None
    page_count: Optional[int] = None
    revision_history: list[dict] = field(default_factory=list)
    comments: list[dict] = field(default_factory=list)
    legend_symbols: list[dict] = field(default_factory=list)
    equipment_ratings: list[dict] = field(default_factory=list)
    drawing_index: list[dict] = field(default_factory=list)
    signature_block: dict = field(default_factory=dict)
    raw_text: str = ""
    extraction_metadata: dict = field(default_factory=dict)


class DeterministicParser:
    """
    Deterministic parser for engineering documents.
    Extracts structured data using regex patterns and position-based heuristics.
    No LLM involved - pure rule-based extraction.
    """
    
    def __init__(self):
        """Initialize parser with compiled regex patterns."""
        # Document number pattern: [A-Z]{2,4}-[A-Z]-[A-Z]{2}-\d{2}-\d{3}
        self.doc_number_regex = re.compile(DOCUMENT_NUMBER_PATTERN)
        
        # Issue status patterns
        self.issue_status_patterns = {}
        for status, labels in ISSUE_STATUS_LABELS.items():
            for label in labels:
                self.issue_status_patterns[label] = status
        
        # Revision pattern: typically "Rev A", "Revision 0", etc.
        self.revision_regex = re.compile(r"(?:Rev(?:ision)?\.?\s*)([A-Z0-9]+)", re.IGNORECASE)
        
        # Contract number pattern: varies, but often contains "CONTRACT" or "CTR"
        self.contract_regex = re.compile(
            r"(?:Contract|CTR|Agreement)[\s#:]+([A-Z0-9\-]+)",
            re.IGNORECASE
        )
        
        # Page count pattern
        self.page_count_regex = re.compile(r"(?:Page|Sheet)\s+(?:of|/)\s*(\d+)", re.IGNORECASE)
        self.page_count_regex_alt = re.compile(r"(\d+)\s*(?:of|/)\s*(\d+)\s*(?:pages|sheets)", re.IGNORECASE)
        
        # Title block patterns
        self.title_patterns = [
            re.compile(r"Title[:\s]+(.+)", re.IGNORECASE),
            re.compile(r"Document Title[:\s]+(.+)", re.IGNORECASE),
            re.compile(r"Drawing Title[:\s]+(.+)", re.IGNORECASE),
        ]
    
    def parse(self, text: str, **kwargs) -> ParsedDocument:
        """
        Parse engineering document text and extract structured data.
        
        Args:
            text: Full text content of the document
            **kwargs: Additional context (file_path, page_count, etc.)
            
        Returns:
            ParsedDocument with extracted structured data
        """
        doc = ParsedDocument(raw_text=text)
        
        try:
            # Extract core fields
            doc.document_number = self._extract_document_number(text)
            doc.title = self._extract_title(text)
            doc.revision = self._extract_revision(text)
            doc.issue_status = self._extract_issue_status(text)
            doc.contract_number = self._extract_contract_number(text)
            doc.page_count = self._extract_page_count(text, kwargs.get("page_count"))
            
            # Extract structured sections
            doc.revision_history = self._extract_revision_history(text)
            doc.comments = self._extract_comments(text)
            doc.legend_symbols = self._extract_legend_symbols(text)
            doc.equipment_ratings = self._extract_equipment_ratings(text)
            doc.drawing_index = self._extract_drawing_index(text)
            doc.signature_block = self._extract_signature_block(text)
            
            # Record extraction metadata
            doc.extraction_metadata = {
                "parser": "deterministic",
                "text_length": len(text),
                "fields_extracted": self._count_extracted_fields(doc),
            }
            
            logger.info(f"Deterministic parsing complete: {doc.extraction_metadata['fields_extracted']} fields extracted")
            
        except Exception as e:
            logger.error(f"Deterministic parsing failed: {e}", exc_info=True)
            raise ParseError(f"Deterministic parsing failed: {e}") from e
        
        return doc
    
    def _extract_document_number(self, text: str) -> Optional[str]:
        """Extract document number using regex pattern."""
        matches = self.doc_number_regex.findall(text)
        if matches:
            # Return first match (usually in title block)
            return matches[0]
        return None
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract document title from title block."""
        # Try each pattern
        for pattern in self.title_patterns:
            match = pattern.search(text)
            if match:
                title = match.group(1).strip()
                # Clean up title - remove excessive whitespace
                title = " ".join(title.split())
                if len(title) > 5:  # Minimum title length
                    return title
        
        # Fallback: look for text after document number
        doc_num_match = self.doc_number_regex.search(text)
        if doc_num_match:
            # Get text after document number
            start = doc_num_match.end()
            next_lines = text[start:start + 200].split("\n")[:3]
            for line in next_lines:
                line = line.strip()
                if line and len(line) > 5 and not re.match(r"^[A-Z0-9\-]+$", line):
                    return line
        
        return None
    
    def _extract_revision(self, text: str) -> Optional[str]:
        """Extract document revision."""
        match = self.revision_regex.search(text)
        if match:
            return match.group(1).upper()
        return None
    
    def _extract_issue_status(self, text: str) -> Optional[str]:
        """Extract issue status (IFR, IFA, IFC, ASB, IFI)."""
        text_upper = text.upper()
        
        # Look for tick-box patterns or status labels
        for label, status in self.issue_status_patterns.items():
            if label.upper() in text_upper:
                # Check if it appears to be checked/selected
                # Look for patterns like "[X] IFR" or "☑ IFR"
                pattern = rf"(?:\[X\]|☑|✓|✔)\s*{re.escape(label.upper())}"
                if re.search(pattern, text_upper):
                    return status
        
        # If no checked box found, return first status found (may be default)
        for label, status in self.issue_status_patterns.items():
            if label.upper() in text_upper:
                return status
        
        return None
    
    def _extract_contract_number(self, text: str) -> Optional[str]:
        """Extract contract number."""
        match = self.contract_regex.search(text)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_page_count(self, text: str, provided_count: Optional[int]) -> Optional[int]:
        """Extract total page count."""
        # Use provided count if available
        if provided_count:
            return provided_count
        
        # Try to extract from text
        match = self.page_count_regex.search(text)
        if match:
            return int(match.group(1))
        
        match = self.page_count_regex_alt.search(text)
        if match:
            # Return second group (total pages)
            return int(match.group(2))
        
        return None
    
    def _extract_revision_history(self, text: str) -> list[dict]:
        """
        Extract revision history table rows.
        Typical format: Rev | Date | Description | Prepared | Checked | Approved
        """
        revisions = []
        
        # Look for revision history section
        rev_section_match = re.search(
            r"(?:Revision History|Rev(?:ision)? History|REVISION RECORD)(.*?)(?:\n\n|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        
        if not rev_section_match:
            return revisions
        
        rev_section = rev_section_match.group(1)
        
        # Split into lines and look for revision entries
        lines = rev_section.split("\n")
        for line in lines:
            # Look for revision identifier (A, B, 0, 1, etc.)
            rev_match = re.match(r"^\s*([A-Z0-9]+)\s+\d{2}/\d{2}/\d{2,4}", line)
            if rev_match:
                parts = line.split()
                if len(parts) >= 2:
                    revisions.append({
                        "rev": rev_match.group(1),
                        "date": parts[1] if len(parts) > 1 else None,
                        "description": " ".join(parts[2:]) if len(parts) > 2 else None,
                        "raw": line.strip(),
                    })
        
        return revisions
    
    def _extract_comments(self, text: str) -> list[dict]:
        """
        Extract comment/response rows.
        Typical format: sequential numbered comments with contractor responses.
        """
        comments = []
        
        # Look for comments section
        comments_section_match = re.search(
            r"(?:Comments|COMMENTS|Comment/Response)(.*?)(?:\n\n|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        
        if not comments_section_match:
            return comments
        
        comments_section = comments_section_match.group(1)
        
        # Look for numbered comment patterns
        comment_pattern = re.compile(
            r"(\d+)[\.\)]\s*(.*?)(?:\n|$)\s*(?:Response[:\s]+)?(.*?)(?=\n\d+[\.\)]|\Z)",
            re.DOTALL,
        )
        
        for match in comment_pattern.finditer(comments_section):
            seq = int(match.group(1))
            client_comment = match.group(2).strip()
            contractor_response = match.group(3).strip() if match.group(3) else None
            
            if client_comment:
                comments.append({
                    "seq": seq,
                    "client_comment": client_comment,
                    "contractor_response": contractor_response,
                })
        
        return comments
    
    def _extract_legend_symbols(self, text: str) -> list[dict]:
        """Extract legend symbols and descriptions."""
        symbols = []
        
        # Look for legend section
        legend_match = re.search(
            r"(?:Legend|LEGEND|Symbol.*?Description)(.*?)(?:\n\n|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        
        if not legend_match:
            return symbols
        
        legend_section = legend_match.group(1)
        
        # Look for symbol-description pairs
        # Pattern: SYMBOL - Description or SYMBOL Description
        symbol_pattern = re.compile(
            r"^([A-Za-z0-9_\-]+)\s*[-–]\s*(.+)$",
            re.MULTILINE,
        )
        
        for match in symbol_pattern.finditer(legend_section):
            symbol = match.group(1).strip()
            description = match.group(2).strip()
            
            if symbol and description and len(symbol) > 1:
                symbols.append({
                    "symbol": symbol,
                    "description": description,
                })
        
        return symbols
    
    def _extract_equipment_ratings(self, text: str) -> list[dict]:
        """Extract equipment ratings from SLD sheets."""
        ratings = []
        
        # Look for equipment rating patterns
        # Typical: TAG: RATING, VOLTAGE, PHASE, FREQUENCY, POWER
        equipment_pattern = re.compile(
            r"([A-Z]{2,4}-\d{3})\s*[:]\s*"  # Equipment tag
            r"(.+?)(?:,\s*|\n)"  # Rating
            r"(\d+(?:\.\d+)?\s*(?:V|kV|VAC|VDC))?"  # Voltage
            r"(?:,\s*|\n)?"
            r"(\d+(?:-)?(?:phase|PH))?"  # Phase
            r"(?:,\s*|\n)?"
            r"(\d+(?:\.\d+)?\s*(?:Hz|Hz))?"  # Frequency
            r"(?:,\s*|\n)?"
            r"(\d+(?:\.\d+)?\s*(?:kW|MW|kVA|MVA))?",  # Power
            re.IGNORECASE,
        )
        
        for match in equipment_pattern.finditer(text):
            ratings.append({
                "tag": match.group(1),
                "rating": match.group(2).strip() if match.group(2) else None,
                "voltage": match.group(3),
                "phase": match.group(4),
                "frequency": match.group(5),
                "power": match.group(6),
            })
        
        return ratings
    
    def _extract_drawing_index(self, text: str) -> list[dict]:
        """Extract drawing index entries for multi-sheet documents."""
        index_entries = []
        
        # Look for drawing index section
        index_match = re.search(
            r"(?:Drawing Index|DRAWING INDEX|Sheet Index|SHEET INDEX)(.*?)(?:\n\n|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        
        if not index_match:
            return index_entries
        
        index_section = index_match.group(1)
        
        # Look for sheet number patterns
        sheet_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*[-–]\s*(.+?)(?:\n|$)",
        )
        
        for match in sheet_pattern.finditer(index_section):
            sheet_no = match.group(1)
            sheet_title = match.group(2).strip()
            
            if sheet_no and sheet_title:
                index_entries.append({
                    "sheet_no": sheet_no,
                    "sheet_title": sheet_title,
                })
        
        return index_entries
    
    def _extract_signature_block(self, text: str) -> dict:
        """Extract signature block (prepared by, checked by, approved by)."""
        signature_block = {}
        
        # Look for signature section
        sig_match = re.search(
            r"(?:Signature|SIGNATURE|Approved by|PREPARED|CHECKED|APPROVED)(.*?)(?:\n\n|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        
        if not sig_match:
            return signature_block
        
        sig_section = sig_match.group(1)
        
        # Extract each role
        for role in SIGNATURE_ROLES:
            # Pattern: Role: Name or Role Name
            role_pattern = re.compile(
                rf"{role.replace('_', ' ').title()}[:\s]+(.+?)(?:\n|$)",
                re.IGNORECASE,
            )
            match = role_pattern.search(sig_section)
            if match:
                signature_block[role] = match.group(1).strip()
        
        return signature_block
    
    def _count_extracted_fields(self, doc: ParsedDocument) -> int:
        """Count number of successfully extracted fields."""
        count = 0
        if doc.document_number:
            count += 1
        if doc.title:
            count += 1
        if doc.revision:
            count += 1
        if doc.issue_status:
            count += 1
        if doc.contract_number:
            count += 1
        if doc.page_count:
            count += 1
        count += len(doc.revision_history)
        count += len(doc.comments)
        count += len(doc.legend_symbols)
        count += len(doc.equipment_ratings)
        count += len(doc.drawing_index)
        count += len(doc.signature_block)
        return count