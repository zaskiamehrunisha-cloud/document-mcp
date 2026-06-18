"""
MCP tools for DOCINTEL.
Implements the four required MCP tools: ingest_document, validate_document,
search_knowledge_base, submit_to_docon.
"""

from typing import Any

from docintel.common.exceptions import DocONError, ExtractionError, ValidationError
from docintel.common.logging import get_logger
from docintel.docon.gateway import get_docon_gateway
from docintel.ingestion.pipeline import IngestionPipeline
from docintel.retrieval.qa import get_qa

logger = get_logger(__name__)


# Global pipeline instance
_pipeline: IngestionPipeline | None = None


def get_pipeline() -> IngestionPipeline:
    """Get the global ingestion pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline


async def ingest_document(
    file_path: str,
    discipline: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Ingest a document into the system.
    
    Args:
        file_path: Path to the document file
        discipline: Submitting discipline (ELC, MEC, INS, SIM, etc.)
        metadata: Optional metadata
        
    Returns:
        Ingestion result with document_id and structured_record
    """
    try:
        logger.info(
            "MCP ingest_document called",
            extra={"file": file_path, "discipline": discipline},
        )
        
        pipeline = get_pipeline()
        result = await pipeline.ingest(
            file_path=file_path,
            discipline=discipline,
            metadata=metadata,
        )
        
        return {
            "document_id": result["document_id"],
            "structured_record": result["structured_record"],
            "confidence": result["confidence"],
            "source_layer": result["source_layer"],
        }
        
    except ExtractionError as e:
        logger.error(f"Ingestion failed: {str(e)}")
        return {
            "error": str(e),
            "error_type": "extraction_error",
        }
    except Exception as e:
        error_msg = f"Ingestion failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "error": error_msg,
            "error_type": "unknown_error",
        }


async def validate_document(
    document_id: int | None = None,
    structured_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Validate a document against reference rules.
    
    Args:
        document_id: Database ID of the document (alternative to structured_record)
        structured_record: Structured record to validate (alternative to document_id)
        
    Returns:
        Validation result with conforms flag and violations
    """
    try:
        logger.info(
            "MCP validate_document called",
            extra={"document_id": document_id},
        )
        
        pipeline = get_pipeline()
        
        # If document_id provided, load from database
        if document_id is not None and structured_record is None:
            # This would load from DB - for now, require structured_record
            return {
                "error": "document_id lookup not yet implemented, provide structured_record",
                "error_type": "not_implemented",
            }
        
        if structured_record is None:
            return {
                "error": "Must provide either document_id or structured_record",
                "error_type": "invalid_input",
            }
        
        result = await pipeline.validate(structured_record)
        
        return {
            "conforms": result["conforms"],
            "violations": result["violations"],
            "matched_rules": result["matched_rules"],
        }
        
    except ValidationError as e:
        logger.error(f"Validation failed: {str(e)}")
        return {
            "conforms": False,
            "violations": e.violations if hasattr(e, 'violations') else [],
            "error": str(e),
        }
    except Exception as e:
        error_msg = f"Validation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "conforms": False,
            "violations": [],
            "error": error_msg,
        }


async def search_knowledge_base(
    question: str,
    discipline: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Search the knowledge base and answer a question.
    
    Args:
        question: Natural-language engineering question
        discipline: Optional discipline filter
        top_k: Number of results to retrieve
        
    Returns:
        Answer with citations and sources
    """
    try:
        logger.info(
            "MCP search_knowledge_base called",
            extra={"question_length": len(question), "discipline": discipline},
        )
        
        qa = get_qa()
        result = await qa.answer_question(
            question=question,
            top_k=top_k,
            discipline=discipline,
        )
        
        return {
            "answer": result["answer"],
            "citations": result["citations"],
            "sources": result["sources"],
            "confidence": result["confidence"],
        }
        
    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "answer": f"Search failed: {str(e)}",
            "citations": [],
            "sources": [],
            "confidence": 0.0,
            "error": error_msg,
        }


async def submit_to_docon(
    document_id: int,
) -> dict[str, Any]:
    """
    Validate and submit a document to DOCON.
    
    Args:
        document_id: Database ID of the document
        
    Returns:
        Submission result with outcome and DOCON reference if successful
    """
    try:
        logger.info(
            "MCP submit_to_docon called",
            extra={"document_id": document_id},
        )
        
        gateway = get_docon_gateway()
        
        # Load document from database (simplified - would need proper DB lookup)
        # For now, return error
        return {
            "error": "Document loading from database not yet implemented",
            "error_type": "not_implemented",
        }
        
    except DocONError as e:
        logger.error(f"DOCON submission failed: {str(e)}")
        return {
            "outcome": "fail",
            "error": str(e),
            "error_type": "docon_error",
        }
    except Exception as e:
        error_msg = f"Submission failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "outcome": "fail",
            "error": error_msg,
            "error_type": "unknown_error",
        }