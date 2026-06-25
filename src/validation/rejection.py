"""Rejection note builder for validation failures."""
import logging
from typing import Optional
from datetime import datetime

from src.common.exceptions import ValidationError

logger = logging.getLogger(__name__)


class RejectionNoteBuilder:
    """
    Builds JSONB rejection notes formatted as numbered Client Comment /
    Contractor Response tables for validation failures.
    """
    
    def build_rejection_note(
        self,
        failed_rules: list[dict],
        warnings: list[dict],
        document_number: Optional[str] = None,
    ) -> dict:
        """
        Build a structured rejection note.
        
        Args:
            failed_rules: List of failed validation rules
            warnings: List of validation warnings
            document_number: Optional document number for reference
            
        Returns:
            JSONB-compatible rejection note dictionary
        """
        try:
            # Build numbered comment/response table
            comments = []
            
            # Add failed rules as client comments
            for i, rule in enumerate(failed_rules, 1):
                comment = {
                    "seq": i,
                    "client_comment": f"[{rule['rule_name']}] {rule['message']}",
                    "contractor_response": None,
                    "rule_type": rule.get("rule_type", "blocking"),
                    "details": rule.get("details"),
                }
                comments.append(comment)
            
            # Add warnings as informational comments
            for i, warning in enumerate(warnings, len(comments) + 1):
                comment = {
                    "seq": i,
                    "client_comment": f"[WARNING - {warning['rule_name']}] {warning['message']}",
                    "contractor_response": None,
                    "rule_type": "warning",
                    "details": warning.get("details"),
                }
                comments.append(comment)
            
            # Build rejection note
            rejection_note = {
                "document_number": document_number,
                "rejection_date": datetime.utcnow().isoformat(),
                "status": "REJECTED",
                "summary": {
                    "total_issues": len(failed_rules),
                    "total_warnings": len(warnings),
                    "blocking_failures": len([r for r in failed_rules if r.get("rule_type") == "blocking"]),
                },
                "comments_response": comments,
                "format": "numbered_client_comment_contractor_response",
            }
            
            logger.info(
                f"Built rejection note with {len(comments)} items "
                f"({len(failed_rules)} failures, {len(warnings)} warnings)"
            )
            
            return rejection_note
        
        except Exception as e:
            logger.error(f"Failed to build rejection note: {e}")
            raise ValidationError(f"Rejection note generation failed: {e}") from e
    
    def format_for_display(self, rejection_note: dict) -> str:
        """
        Format rejection note as human-readable text for UI display.
        
        Args:
            rejection_note: Rejection note dictionary
            
        Returns:
            Formatted string for display
        """
        lines = []
        
        lines.append("=" * 80)
        lines.append("DOCUMENT VALIDATION REJECTION")
        lines.append("=" * 80)
        lines.append("")
        
        if rejection_note.get("document_number"):
            lines.append(f"Document: {rejection_note['document_number']}")
        
        lines.append(f"Date: {rejection_note.get('rejection_date', 'N/A')}")
        lines.append(f"Status: {rejection_note.get('status', 'REJECTED')}")
        lines.append("")
        
        summary = rejection_note.get("summary", {})
        lines.append("SUMMARY:")
        lines.append(f"  - Blocking failures: {summary.get('blocking_failures', 0)}")
        lines.append(f"  - Warnings: {summary.get('total_warnings', 0)}")
        lines.append("")
        
        lines.append("-" * 80)
        lines.append("CLIENT COMMENT / CONTRACTOR RESPONSE TABLE")
        lines.append("-" * 80)
        lines.append("")
        
        comments = rejection_note.get("comments_response", [])
        for comment in comments:
            seq = comment.get("seq", "?")
            client_comment = comment.get("client_comment", "N/A")
            contractor_response = comment.get("contractor_response", "Pending")
            rule_type = comment.get("rule_type", "unknown")
            
            lines.append(f"{seq}. [{rule_type.upper()}] {client_comment}")
            if contractor_response:
                lines.append(f"   Contractor Response: {contractor_response}")
            else:
                lines.append(f"   Contractor Response: [Awaiting response]")
            lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def to_jsonb(self, rejection_note: dict) -> dict:
        """
        Ensure rejection note is JSONB-compatible.
        
        Args:
            rejection_note: Rejection note dictionary
            
        Returns:
            JSONB-compatible dictionary
        """
        # Ensure all values are JSON-serializable
        import json
        
        try:
            # Test serialization
            json.dumps(rejection_note)
            return rejection_note
        except (TypeError, ValueError) as e:
            logger.error(f"Rejection note is not JSON-serializable: {e}")
            # Return a safe fallback
            return {
                "document_number": rejection_note.get("document_number"),
                "rejection_date": rejection_note.get("rejection_date"),
                "status": "REJECTED",
                "error": "Rejection note serialization failed",
                "comments_response": [],
            }


# Global rejection note builder instance
rejection_builder = RejectionNoteBuilder()