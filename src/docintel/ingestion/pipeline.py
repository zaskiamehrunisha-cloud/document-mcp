"""
Ingestion pipeline coordinator for DOCINTEL.
Orchestrates the ingest → extract → parse → persist → validate → route flow.
"""

from typing import Any

from docintel.common.exceptions import ExtractionError, ParseError, ValidationError
from docintel.common.logging import get_logger
from docintel.ingestion.dispatcher import get_dispatcher
from docintel.parser.deterministic import get_deterministic_parser
from docintel.parser.llm_extractor import get_llm_extractor
from docintel.parser.merge import get_parser_merger
from docintel.validation.rule_engine import get_rule_engine

logger = get_logger(__name__)


class IngestionPipeline:
    """
    Coordinates the full ingestion pipeline.
    """
    
    def __init__(self):
        """Initialize the pipeline."""
        self.dispatcher = get_dispatcher()
        self.det_parser = get_deterministic_parser()
        self.llm_extractor = get_llm_extractor()
        self.merger = get_parser_merger()
        self.rule_engine = get_rule_engine()
    
    async def ingest(
        self,
        file_path: str,
        discipline: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run the full ingestion pipeline.
        
        Args:
            file_path: Path to the document file
            discipline: Submitting discipline
            metadata: Optional metadata
            
        Returns:
            Ingestion result with document_id and structured_record
        """
        try:
            # Step 1: Dispatch and extract
            logger.info("Pipeline: Starting extraction")
            extracted = self.dispatcher.dispatch(file_path)
            
            # Step 2: Parse (deterministic + LLM)
            logger.info("Pipeline: Starting parsing")
            det_result = self.det_parser.parse(extracted["text"], extracted["file_type"])
            
            # Try LLM extraction (non-blocking)
            llm_result = {}
            try:
                llm_result = await self.llm_extractor.extract(extracted["text"])
            except Exception as e:
                logger.warning(f"LLM extraction failed, using deterministic only: {str(e)}")
            
            # Step 3: Merge results
            logger.info("Pipeline: Merging results")
            record = self.merger.merge(
                deterministic_result=det_result,
                llm_result=llm_result,
                source_layer=extracted["source_layer"],
            )
            
            # Step 4: Persist to database (simplified - would need DB repo)
            document_id = metadata.get("document_id") if metadata else None
            if document_id is None:
                # Would create document in DB
                document_id = 0  # Placeholder
            
            logger.info(
                "Pipeline: Ingestion complete",
                extra={
                    "document_id": document_id,
                    "confidence": record.confidence,
                    "doc_number": record.document_number,
                },
            )
            
            return {
                "document_id": document_id,
                "structured_record": record.model_dump(),
                "confidence": record.confidence,
                "source_layer": record.source_layer,
            }
            
        except ExtractionError:
            raise
        except Exception as e:
            error_msg = f"Ingestion pipeline failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ParseError(error_msg) from e
    
    async def validate(
        self,
        structured_record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate a structured record.
        
        Args:
            structured_record: Structured record to validate
            
        Returns:
            Validation result
        """
        try:
            logger.info("Pipeline: Starting validation")
            
            result = self.rule_engine.validate(structured_record)
            
            logger.info(
                "Pipeline: Validation complete",
                extra={"conforms": result["conforms"]},
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Validation pipeline failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValidationError(error_msg) from e
    
    async def validate_and_submit(
        self,
        file_path: str,
        discipline: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run full pipeline: ingest → validate → submit to DOCON.
        
        Args:
            file_path: Path to the document file
            discipline: Submitting discipline
            metadata: Optional metadata
            
        Returns:
            Submission result with outcome
        """
        try:
            # Ingest
            ingest_result = await self.ingest(file_path, discipline, metadata)
            
            # Validate
            validation_result = await self.validate(ingest_result["structured_record"])
            
            if not validation_result["conforms"]:
                return {
                    "outcome": "fail",
                    "document_id": ingest_result["document_id"],
                    "violations": validation_result["violations"],
                    "matched_rules": validation_result["matched_rules"],
                    "explanation": self._format_violations(validation_result),
                }
            
            # TODO: Submit to DOCON if validation passes
            # For now, just return validation success
            return {
                "outcome": "pass",
                "document_id": ingest_result["document_id"],
                "validation_passed": True,
                "structured_record": ingest_result["structured_record"],
            }
            
        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "outcome": "fail",
                "error": error_msg,
            }
    
    def _format_violations(self, validation_result: dict[str, Any]) -> str:
        """Format violations into a human-readable explanation."""
        violations = validation_result.get("violations", [])
        
        if not violations:
            return "Document passes all validation checks."
        
        lines = ["Document does not conform to validation rules:", ""]
        
        errors = [v for v in violations if v.get("severity") == "error"]
        warnings = [v for v in violations if v.get("severity") == "warning"]
        
        if errors:
            lines.append("ERRORS (must be fixed):")
            for v in errors:
                lines.append(f"  - {v.get('description', 'Unknown error')}")
            lines.append("")
        
        if warnings:
            lines.append("WARNINGS (should be reviewed):")
            for v in warnings:
                lines.append(f"  - {v.get('description', 'Unknown warning')}")
            lines.append("")
        
        lines.append("Please correct the above issues and resubmit.")
        
        return "\n".join(lines)


# Global pipeline instance
_pipeline: IngestionPipeline | None = None


def get_pipeline() -> IngestionPipeline:
    """Get the global pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline