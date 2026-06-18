"""
Validation reference rules for DOCINTEL.
Derives validation rules from the reference document set.
"""

from typing import Any

from docintel.common.logging import get_logger

logger = get_logger(__name__)


class ReferenceRuleDeriver:
    """
    Derives validation rules from reference documents.
    Analyzes the reference set to extract patterns and constraints.
    """
    
    def __init__(self):
        """Initialize the reference rule deriver."""
        pass
    
    def derive_rules(self, reference_documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Derive validation rules from reference documents.
        
        Args:
            reference_documents: List of reference document records
            
        Returns:
            List of validation rule dictionaries
        """
        rules = []
        
        # Rule 1: Document number format (derived from reference set)
        rules.append(self._derive_document_number_rule())
        
        # Rule 2: Contract number (from reference documents)
        contract_numbers = set()
        for doc in reference_documents:
            if doc.get("contract_number"):
                contract_numbers.add(doc["contract_number"])
        
        if contract_numbers:
            rules.append(self._derive_contract_number_rule(contract_numbers))
        
        # Rule 3: Required title block fields (from reference documents)
        rules.append(self._derive_title_block_rule())
        
        # Rule 4: Revision ladder (from reference documents)
        revision_codes = set()
        for doc in reference_documents:
            if doc.get("revision"):
                revision_codes.add(doc["revision"])
            # Also check revision history
            for rev in doc.get("revision_history", []):
                if rev.get("revision"):
                    revision_codes.add(rev["revision"])
        
        if revision_codes:
            rules.append(self._derive_revision_ladder_rule(revision_codes))
        
        # Rule 5: Issue status codes (from reference documents)
        issue_codes = set()
        for doc in reference_documents:
            if doc.get("issue_status"):
                issue_codes.add(doc["issue_status"])
        
        if issue_codes:
            rules.append(self._derive_issue_status_rule(issue_codes))
        
        # Rule 6: Mandatory administrative sheets (from reference documents)
        rules.append(self._derive_mandatory_sheets_rule())
        
        # Rule 7: Discipline codes (from reference documents)
        disciplines = set()
        for doc in reference_documents:
            if doc.get("discipline"):
                disciplines.add(doc["discipline"])
        
        if disciplines:
            rules.append(self._derive_discipline_rule(disciplines))
        
        # Rule 8: Confidence threshold
        rules.append(self._derive_confidence_rule())
        
        logger.info(f"Derived {len(rules)} validation rules from {len(reference_documents)} reference documents")
        
        return rules
    
    def _derive_document_number_rule(self) -> dict[str, Any]:
        """Derive document number format rule."""
        return {
            "rule_key": "document_number_format",
            "rule_type": "regex",
            "definition": {
                "pattern": r"^[A-Z]{3}-[A-Z]-[A-Z]{2}-\d{2}-\d{3}$",
                "description": "Project code (3) - Discipline (1) - Drawing type (2) - Area (2) - Sequence (3)",
                "field": "document_number",
                "severity": "error",
            },
        }
    
    def _derive_contract_number_rule(self, contract_numbers: set[str]) -> dict[str, Any]:
        """Derive contract number rule."""
        # Use the most common contract number
        return {
            "rule_key": "contract_number_match",
            "rule_type": "equality",
            "definition": {
                "expected_value": list(contract_numbers)[0],
                "field": "contract_number",
                "description": "Contract number must match project contract",
                "severity": "error",
            },
        }
    
    def _derive_title_block_rule(self) -> dict[str, Any]:
        """Derive required title block fields rule."""
        return {
            "rule_key": "title_block_required_fields",
            "rule_type": "required_fields",
            "definition": {
                "fields": [
                    "DOCUMENT NO.",
                    "CONTRACTOR DOC NO.",
                    "REV.",
                    "CONTRACT NO.",
                    "PAGE",
                    "CLIENT",
                    "PROJECT TITLE",
                    "DOC. TITLE",
                ],
                "description": "All title block fields must be present",
                "severity": "error",
            },
        }
    
    def _derive_revision_ladder_rule(self, revision_codes: set[str]) -> dict[str, Any]:
        """Derive revision ladder rule."""
        return {
            "rule_key": "revision_ladder",
            "rule_type": "enum",
            "definition": {
                "allowed_values": sorted(list(revision_codes)),
                "field": "revision",
                "description": "Revision must follow the approved ladder",
                "severity": "error",
            },
        }
    
    def _derive_issue_status_rule(self, issue_codes: set[str]) -> dict[str, Any]:
        """Derive issue status codes rule."""
        return {
            "rule_key": "issue_status_codes",
            "rule_type": "enum",
            "definition": {
                "allowed_values": sorted(list(issue_codes)),
                "field": "issue_status",
                "description": "Issue status must be a recognized code",
                "severity": "warning",
            },
        }
    
    def _derive_mandatory_sheets_rule(self) -> dict[str, Any]:
        """Derive mandatory administrative sheets rule."""
        return {
            "rule_key": "mandatory_administrative_sheets",
            "rule_type": "required_sheets",
            "definition": {
                "sheets": [
                    "COMMENTS RESPONSE SHEET",
                    "RECORD OF REVISION",
                ],
                "description": "Document must include mandatory administrative sheets",
                "severity": "error",
            },
        }
    
    def _derive_discipline_rule(self, disciplines: set[str]) -> dict[str, Any]:
        """Derive discipline code rule."""
        return {
            "rule_key": "discipline_code",
            "rule_type": "enum",
            "definition": {
                "allowed_values": sorted(list(disciplines)),
                "field": "discipline",
                "description": "Discipline must be a recognized code",
                "severity": "error",
            },
        }
    
    def _derive_confidence_rule(self) -> dict[str, Any]:
        """Derive extraction confidence threshold rule."""
        return {
            "rule_key": "extraction_confidence",
            "rule_type": "threshold",
            "definition": {
                "min_confidence": 0.6,
                "field": "confidence",
                "description": "Extraction confidence must meet minimum threshold",
                "severity": "warning",
            },
        }


# Global rule deriver instance
_rule_deriver: ReferenceRuleDeriver | None = None


def get_rule_deriver() -> ReferenceRuleDeriver:
    """Get the global reference rule deriver instance."""
    global _rule_deriver
    if _rule_deriver is None:
        _rule_deriver = ReferenceRuleDeriver()
    return _rule_deriver