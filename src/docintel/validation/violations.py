"""
Validation violations for DOCINTEL.
Models and utilities for validation violation reporting.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ViolationSeverity(Enum):
    """Severity levels for validation violations."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Violation:
    """
    Represents a single validation violation.
    """
    rule: str
    field: str
    description: str
    severity: ViolationSeverity = ViolationSeverity.ERROR
    details: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rule": self.rule,
            "field": self.field,
            "description": self.description,
            "severity": self.severity.value,
            "details": self.details,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Violation":
        """Create from dictionary."""
        severity = ViolationSeverity(data.get("severity", "error"))
        return cls(
            rule=data.get("rule", ""),
            field=data.get("field", ""),
            description=data.get("description", ""),
            severity=severity,
            details=data.get("details", ""),
        )


@dataclass
class ValidationResult:
    """
    Result of validating a document against rules.
    """
    conforms: bool
    violations: list[Violation] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        """Count of error-level violations."""
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level violations."""
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.WARNING)
    
    @property
    def info_count(self) -> int:
        """Count of info-level violations."""
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.INFO)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conforms": self.conforms,
            "violations": [v.to_dict() for v in self.violations],
            "matched_rules": self.matched_rules,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
        }
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        if self.conforms:
            return "Document conforms to all validation rules"
        
        parts = []
        if self.error_count > 0:
            parts.append(f"{self.error_count} error(s)")
        if self.warning_count > 0:
            parts.append(f"{self.warning_count} warning(s)")
        if self.info_count > 0:
            parts.append(f"{self.info_count} info(s)")
        
        return f"Document has {', '.join(parts)}"
    
    def get_cited_explanation(self) -> str:
        """
        Get a detailed explanation of violations for the submitter.
        """
        if self.conforms:
            return "Document passes all validation checks and is ready for submission."
        
        lines = ["Document does not conform to validation rules:", ""]
        
        # Group by severity
        errors = [v for v in self.violations if v.severity == ViolationSeverity.ERROR]
        warnings = [v for v in self.violations if v.severity == ViolationSeverity.WARNING]
        
        if errors:
            lines.append("ERRORS (must be fixed):")
            for v in errors:
                lines.append(f"  - {v.description}")
                if v.details:
                    lines.append(f"    Details: {v.details}")
            lines.append("")
        
        if warnings:
            lines.append("WARNINGS (should be reviewed):")
            for v in warnings:
                lines.append(f"  - {v.description}")
                if v.details:
                    lines.append(f"    Details: {v.details}")
            lines.append("")
        
        lines.append("Please correct the above issues and resubmit.")
        
        return "\n".join(lines)