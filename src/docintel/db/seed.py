"""
Database seeding for DOCINTEL.
Seeds reference documents at startup.
"""

import asyncio
from pathlib import Path
from typing import Any

from docintel.common.logging import get_logger
from docintel.config.settings import settings
from docintel.ingestion.pipeline import get_pipeline
from docintel.validation.reference_rules import get_rule_deriver

logger = get_logger(__name__)


async def seed_reference_documents() -> dict[str, Any]:
    """
    Seed the database with reference documents.
    
    Returns:
        Seeding result summary
    """
    try:
        reference_dir = Path(settings.reference_docs_dir)
        
        if not reference_dir.exists():
            logger.warning(f"Reference documents directory not found: {reference_dir}")
            return {
                "status": "skipped",
                "reason": "Reference directory not found",
                "documents_seeded": 0,
            }
        
        # Find PDF files in reference directory
        pdf_files = list(reference_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {reference_dir}")
            return {
                "status": "skipped",
                "reason": "No PDF files found",
                "documents_seeded": 0,
            }
        
        logger.info(f"Found {len(pdf_files)} reference documents to seed")
        
        pipeline = get_pipeline()
        rule_deriver = get_rule_deriver()
        
        reference_documents = []
        seeded_count = 0
        
        for pdf_file in pdf_files:
            try:
                logger.info(f"Seeding reference document: {pdf_file.name}")
                
                # Ingest the document
                result = await pipeline.ingest(
                    file_path=str(pdf_file),
                    discipline="REF",  # Reference documents
                    metadata={"is_reference": True},
                )
                
                reference_documents.append(result["structured_record"])
                seeded_count += 1
                
                logger.info(
                    f"Successfully seeded: {pdf_file.name}",
                    extra={"document_id": result["document_id"]},
                )
                
            except Exception as e:
                logger.error(f"Failed to seed {pdf_file.name}: {str(e)}", exc_info=True)
        
        # Derive validation rules from reference documents
        if reference_documents:
            try:
                rules = rule_deriver.derive_rules(reference_documents)
                logger.info(f"Derived {len(rules)} validation rules from reference documents")
                
                # TODO: Save rules to database
                # For now, just log them
                for rule in rules:
                    logger.debug(f"Rule: {rule['rule_key']}")
                    
            except Exception as e:
                logger.error(f"Failed to derive validation rules: {str(e)}", exc_info=True)
        
        logger.info(f"Reference document seeding complete: {seeded_count}/{len(pdf_files)} documents")
        
        return {
            "status": "completed",
            "documents_seeded": seeded_count,
            "total_documents": len(pdf_files),
            "rules_derived": len(reference_documents) if reference_documents else 0,
        }
        
    except Exception as e:
        error_msg = f"Reference document seeding failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "failed",
            "error": error_msg,
            "documents_seeded": 0,
        }


def get_seeding_status() -> dict[str, Any]:
    """
    Get the status of reference document seeding.
    
    Returns:
        Seeding status information
    """
    try:
        reference_dir = Path(settings.reference_docs_dir)
        
        if not reference_dir.exists():
            return {
                "status": "not_configured",
                "reference_dir": str(reference_dir),
            }
        
        pdf_files = list(reference_dir.glob("*.pdf"))
        
        return {
            "status": "configured",
            "reference_dir": str(reference_dir),
            "reference_documents_found": len(pdf_files),
            "documents": [f.name for f in pdf_files],
        }
        
    except Exception as e:
        logger.error(f"Failed to get seeding status: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }