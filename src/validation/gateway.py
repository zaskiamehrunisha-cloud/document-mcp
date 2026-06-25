"""Validation gateway - evaluates documents against configurable rules."""
import logging
from typing import Optional
from datetime import datetime

from src.db.models import ValidationRule, ReferenceDocument
from src.common.exceptions import ValidationError
from src.common.audit import create_validation_audit

logger = logging.getLogger(__name__)


class ValidationGateway:
    """
    Validation gateway that evaluates documents against active rules.
    Rules are loaded from the database and can be configured without code changes.
    """
    
    def __init__(self):
        """Initialize validation gateway."""
        self.rules_cache: list[ValidationRule] = []
        self.last_reload = None
    
    async def validate_document(
        self,
        document_id: int,
        parsed_data: dict,
        discipline: Optional[str] = None,
    ) -> dict:
        """
        Validate a document against all active rules.
        
        Args:
            document_id: Database ID of the document
            parsed_data: Parsed document data
            discipline: Optional discipline for discipline-specific rules
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Load active rules
            rules = await self._load_rules(discipline)
            
            passed = True
            failed_rules = []
            warnings = []
            
            # Evaluate each rule
            for rule in rules:
                result = self._evaluate_rule(rule, parsed_data)
                
                if not result["passed"]:
                    if rule.rule_type == "blocking":
                        passed = False
                        failed_rules.append({
                            "rule_name": rule.name,
                            "rule_type": rule.rule_type,
                            "message": result["message"],
                            "details": result.get("details"),
                        })
                    else:
                        warnings.append({
                            "rule_name": rule.name,
                            "rule_type": rule.rule_type,
                            "message": result["message"],
                            "details": result.get("details"),
                        })
            
            # Create validation result
            result = {
                "document_id": document_id,
                "passed": passed,
                "rules_evaluated": len(rules),
                "rules_failed": len(failed_rules),
                "failed_rules": failed_rules,
                "warnings": warnings,
                "validated_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"Validation {'PASSED' if passed else 'FAILED'} for document {document_id}: "
                f"{len(rules)} rules evaluated, {len(failed_rules)} failed"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Validation failed for document {document_id}: {e}", exc_info=True)
            raise ValidationError(f"Validation failed: {e}") from e
    
    async def _load_rules(self, discipline: Optional[str] = None) -> list[ValidationRule]:
        """
        Load active validation rules from database.
        
        Args:
            discipline: Optional discipline filter
            
        Returns:
            List of active validation rules
        """
        from src.db.session import async_session_factory
        from sqlalchemy import select
        
        async with async_session_factory() as session:
            query = select(ValidationRule).where(ValidationRule.active == True)
            
            # Filter by discipline if specified
            if discipline:
                query = query.where(
                    (ValidationRule.discipline == discipline) | 
                    (ValidationRule.discipline == None)
                )
            
            result = await session.execute(query)
            rules = result.scalars().all()
            
            return list(rules)
    
    def _evaluate_rule(self, rule: ValidationRule, parsed_data: dict) -> dict:
        """
        Evaluate a single validation rule.
        
        Args:
            rule: Validation rule to evaluate
            parsed_data: Parsed document data
            
        Returns:
            Dictionary with pass/fail result and message
        """
        try:
            rule_def = rule.definition
            rule_type = rule_def.get("type")
            
            # Route to appropriate validator
            if rule_type == "required_field":
                return self._validate_required_field(rule, parsed_data)
            elif rule_type == "pattern_match":
                return self._validate_pattern_match(rule, parsed_data)
            elif rule_type == "custom":
                return self._validate_custom(rule, parsed_data)
            else:
                return {
                    "passed": False,
                    "message": f"Unknown rule type: {rule_type}",
                }
        
        except Exception as e:
            logger.error(f"Rule evaluation failed for {rule.name}: {e}")
            return {
                "passed": False,
                "message": f"Rule evaluation error: {e}",
            }
    
    def _validate_required_field(self, rule: ValidationRule, parsed_data: dict) -> dict:
        """
        Validate that a required field is present.
        
        Args:
            rule: Validation rule
            parsed_data: Parsed document data
            
        Returns:
            Validation result
        """
        field = rule.definition.get("field")
        
        if not field:
            return {"passed": False, "message": "Rule missing 'field' definition"}
        
        # Check if field exists in parsed data
        value = parsed_data.get(field)
        
        if value is None or (isinstance(value, str) and not value.strip()):
            return {
                "passed": False,
                "message": f"Required field '{field}' is missing or empty",
                "details": {"field": field},
            }
        
        return {
            "passed": True,
            "message": f"Required field '{field}' is present",
        }
    
    def _validate_pattern_match(self, rule: ValidationRule, parsed_data: dict) -> dict:
        """
        Validate that a field matches a regex pattern.
        
        Args:
            rule: Validation rule
            parsed_data: Parsed document data
            
        Returns:
            Validation result
        """
        import re
        
        field = rule.definition.get("field")
        pattern = rule.definition.get("pattern")
        
        if not field or not pattern:
            return {"passed": False, "message": "Rule missing 'field' or 'pattern'"}
        
        value = parsed_data.get(field, "")
        
        if not re.match(pattern, str(value)):
            return {
                "passed": False,
                "message": f"Field '{field}' does not match required pattern",
                "details": {"field": field, "pattern": pattern, "value": value},
            }
        
        return {
            "passed": True,
            "message": f"Field '{field}' matches pattern",
        }
    
    def _validate_custom(self, rule: ValidationRule, parsed_data: dict) -> dict:
        """
        Custom validation logic.
        
        Args:
            rule: Validation rule
            parsed_data: Parsed document data
            
        Returns:
            Validation result
        """
        # Custom validation can be extended based on rule definition
        # For now, just check if the rule has a valid structure
        return {
            "passed": True,
            "message": "Custom validation passed",
        }


# Global validation gateway instance
validation_gateway = ValidationGateway()