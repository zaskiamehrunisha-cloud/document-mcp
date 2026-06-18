"""
DOCON gateway for DOCINTEL.
Orchestrates validation and submission to DOCON.
"""

from typing import Any

from docintel.common.exceptions import DocONError, ValidationError
from docintel.common.logging import get_logger
from docintel.docon.connector import DoconConnector
from docintel.docon.mock_connector import MockDoconConnector
from docintel.validation.rule_engine import get_rule_engine
from docintel.validation.violations import ValidationResult

logger = get_logger(__name__)


class DoconGateway:
    """
    Gateway for DOCON submission.
    Validates documents and routes conforming ones to DOCON.
    """
    
    def __init__(self, connector: DoconConnector | None = None):
        """
        Initialize the DOCON gateway.
        
        Args:
            connector: DOCON connector implementation (defaults to mock)
        """
        self.connector = connector or MockDoconConnector()
        self.rule_engine = get_rule_engine()
    
    async def submit(
        self,
        document_id: int,
        structured_record: dict[str, Any],
        file_path: str,
        discipline: str,
    ) -> dict[str, Any]:
        """
        Validate and submit a document to DOCON.
        
        Args:
            document_id: Database ID of the document
            structured_record: Parsed structured record
            file_path: Path to the document file
            discipline: Submitting discipline
            
        Returns:
            Submission result with outcome and details
        """
        try:
            # Validate the document
            validation_result = self.rule_engine.validate(structured_record)
            
            if not validation_result["conforms"]:
                # Document failed validation - hold back
                logger.warning(
                    "Document failed validation, holding back from DOCON",
                    extra={
                        "document_id": document_id,
                        "violations": len(validation_result["violations"]),
                    },
                )
                
                return {
                    "outcome": "fail",
                    "document_id": document_id,
                    "violations": validation_result["violations"],
                    "matched_rules": validation_result["matched_rules"],
                    "explanation": self._format_violations(validation_result),
                }
            
            # Document passed validation - submit to DOCON
            logger.info(
                "Document passed validation, submitting to DOCON",
                extra={"document_id": document_id, "discipline": discipline},
            )
            
            receipt = await self.connector.submit(
                document_id=document_id,
                structured_record=structured_record,
                file_path=file_path,
                discipline=discipline,
            )
            
            logger.info(
                "Document submitted to DOCON",
                extra={
                    "document_id": document_id,
                    "docon_reference": receipt.get("docon_reference"),
                },
            )
            
            return {
                "outcome": "pass",
                "document_id": document_id,
                "docon_reference": receipt.get("docon_reference"),
                "submitted_at": receipt.get("submitted_at"),
                "status": receipt.get("status"),
            }
            
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            return {
                "outcome": "fail",
                "document_id": document_id,
                "violations": e.violations if hasattr(e, 'violations') else [],
                "explanation": str(e),
            }
        except DocONError as e:
            logger.error(f"DOCON submission error: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            error_msg = f"Docon gateway error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise DocONError(error_msg) from e
    
    def _format_violations(self, validation_result: dict[str, Any]) -> str:
        """
        Format violations into a human-readable explanation.
        
        Args:
            validation_result: Validation result dictionary
            
        Returns:
            Formatted explanation string
        """
        violations = validation_result.get("violations", [])
        
        if not violations:
            return "Document passes all validation checks."
        
        lines = ["Document does not conform to validation rules:", ""]
        
        # Group by severity
        errors = [v for v in violations if v.get("severity") == "error"]
        warnings = [v for v in violations if v.get("severity") == "warning"]
        
        if errors:
            lines.append("ERRORS (must be fixed):")
            for v in errors:
                lines.append(f"  - {v.get('description', 'Unknown error')}")
                if v.get("details"):
                    lines.append(f"    Details: {v['details']}")
            lines.append("")
        
        if warnings:
            lines.append("WARNINGS (should be reviewed):")
            for v in warnings:
                lines.append(f"  - {v.get('description', 'Unknown warning')}")
                if v.get("details"):
                    lines.append(f"    Details: {v['details']}")
            lines.append("")
        
        lines.append("Please correct the above issues and resubmit.")
        
        return "\n".join(lines)
    
    def is_docon_available(self) -> bool:
        """
        Check if DOCON is available.
        
        Returns:
            True if DOCON is available
        """
        return self.connector.is_available()


# Global gateway instance
_gateway: DoconGateway | None = None


def get_docon_gateway(connector: DoconConnector | None = None) -> DoconGateway:
    """Get the global DOCON gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = DoconGateway(connector=connector)
    return _gateway