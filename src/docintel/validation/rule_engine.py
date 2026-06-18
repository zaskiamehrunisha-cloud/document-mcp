"""
Validation rule engine for DOCINTEL.
Applies derived rules to structured records to check conformance.
"""

import re
from typing import Any

from docintel.common.constants import DOCUMENT_NUMBER_PATTERN
from docintel.common.exceptions import ValidationError
from docintel.common.logging import get_logger

logger = get_logger(__name__)


class ValidationRuleEngine:
    """
    Applies validation rules to structured records.
    Rules are derived from the reference document set.
    """
    
    def __init__(self):
        """Initialize the validation rule engine."""
        self.rules: list[dict[str, Any]] = []
    
    def load_rules(self, rules: list[dict[str, Any]]) -> None:
        """
        Load validation rules.
        
        Args:
            rules: List of rule dictionaries with 'rule_key', 'rule_type', 'definition'
        """
        self.rules = [r for r in rules if r.get("active", True)]
        logger.info(f"Loaded {len(self.rules)} active validation rules")
    
    def validate(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Validate a structured record against all loaded rules.
        
        Args:
            record: Structured record dictionary
            
        Returns:
            Validation result with 'conforms', 'violations', and 'matched_rules'
        """
        violations = []
        matched_rules = []
        
        for rule in self.rules:
            rule_type = rule.get("rule_type")
            definition = rule.get("definition", {})
            rule_key = rule.get("rule_key")
            severity = definition.get("severity", "error")
            
            violation = None
            
            if rule_type == "regex":
                violation = self._check_regex(record, definition)
            elif rule_type == "equality":
                violation = self._check_equality(record, definition)
            elif rule_type == "required_fields":
                violation = self._check_required_fields(record, definition)
            elif rule_type == "enum":
                violation = self._check_enum(record, definition)
            elif rule_type == "required_sheets":
                violation = self._check_required_sheets(record, definition)
            elif rule_type == "threshold":
                violation = self._check_threshold(record, definition)
            
            if violation:
                violations.append(violation)
                matched_rules.append(rule_key)
        
        result = {
            "conforms": len(violations) == 0,
            "violations": violations,
            "matched_rules": matched_rules,
        }
        
        logger.info(
            "Validation complete",
            extra={
                "conforms": result["conforms"],
                "violation_count": len(violations),
                "rules_checked": len(self.rules),
            },
        )
        
        return result
    
    def _check_regex(self, record: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any] | None:
        """Check a field against a regex pattern."""
        field = definition.get("field")
        pattern = definition.get("pattern")
        description = definition.get("description", "")
        
        if not field or not pattern:
            return None
        
        value = record.get(field)
        if not value:
            return {
                "rule": "regex",
                "field": field,
                "description": description,
                "severity": definition.get("severity", "error"),
                "details": f"Field '{field}' is missing or empty",
            }
        
        if not re.match(pattern, str(value)):
            return {
                "rule": "regex",
                "field": field,
                "description": description,
                "severity": definition.get("severity", "error"),
                "details": f"Value '{value}' does not match pattern '{pattern}'",
            }
        
        return None
    
    def _check_equality(self, record: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any] | None:
        """Check a field equals an expected value."""
        field = definition.get("field")
        expected = definition.get("expected_value")
        description = definition.get("description", "")
        
        if not field or expected is None:
            return None
        
        value = record.get(field)
        if value != expected:
            return {
                "rule": "equality",
                "field": field,
                "description": description,
                "severity": definition.get("severity", "error"),
                "details": f"Expected '{expected}', got '{value}'",
            }
        
        return None
    
    def _check_required_fields(self, record: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any] | None:
        """Check that required fields are present."""
        required = definition.get("fields", [])
        description = definition.get("description", "")
        
        missing = [f for f in required if not record.get(f)]
        
        if missing:
            return {
                "rule": "required_fields",
                "field": "multiple",
                "description": description,
                "severity": definition.get("severity", "error"),
                "details": f"Missing required fields: {', '.join(missing)}",
            }
        
        return None
    
    def _check_enum(self, record: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any] | None:
        """Check a field value is in an allowed list."""
        field = definition.get("field")
        allowed = definition.get("allowed_values", [])
        description = definition.get("description", "")
        
        if not field or not allowed:
            return None
        
        value = record.get(field)
        if not value:
            return None  # Missing fields handled by required_fields rule
        
        if str(value).upper() not in [str(v).upper() for v in allowed]:
            return {
                "rule": "enum",
                "field": field,
                "description": description,
                "severity": definition.get("severity", "error"),
                "details": f"Value '{value}' not in allowed values: {', '.join(allowed)}",
            }
        
        return None
    
    def _check_required_sheets(self, record: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any] | None:
        """Check that mandatory sheets are present."""
        required_sheets = definition.get("sheets", [])
        description = definition.get("description", "")
        
        # Check if the record indicates mandatory sheets are present
        has_sheets = record.get("mandatory_sheets_present", False)
        
        if not has_sheets:
            return {
                "rule": "required_sheets",
                "field": "mandatory_sheets",
                "description": description,
                "severity": definition.get("severity", "error"),
                "details": f"Missing mandatory sheets: {', '.join(required_sheets)}",
            }
        
        return None
    
    def _check_threshold(self, record: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any] | None:
        """Check a numeric field meets a minimum threshold."""
        field = definition.get("field")
        min_value = definition.get("min_confidence", 0.0)
        description = definition.get("description", "")
        
        if not field:
            return None
        
        value = record.get(field)
        if value is None:
            return None
        
        try:
            if float(value) < float(min_value):
                return {
                    "rule": "threshold",
                    "field": field,
                    "description": description,
                    "severity": definition.get("severity", "warning"),
                    "details": f"Value {value:.2f} is below minimum {min_value:.2f}",
                }
        except (ValueError, TypeError):
            pass
        
        return None


# Global rule engine instance
_rule_engine: ValidationRuleEngine | None = None


def get_rule_engine() -> ValidationRuleEngine:
    """Get the global validation rule engine instance."""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = ValidationRuleEngine()
    return _rule_engine