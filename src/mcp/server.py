"""MCP server implementation exposing 4 tools for document ingestion and validation."""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP(
    name="Engineering Document Control",
    description="Document ingestion, validation, search, and submission tools for engineering documents",
)

# Tool definitions (will be registered with decorators)


@mcp.tool()
async def ingest_document(
    file_path: str,
    discipline: str | None = None,
) -> dict[str, Any]:
    """
    Upload and process a document through the ingestion pipeline.

    Args:
        file_path: Path to the document file (PDF, DWG, DXF, DOCX, XLSX, PPTX, PNG, JPG, TIFF)
        discipline: Optional discipline tag (ELC/MEC/INS/SIM)

    Returns:
        Dictionary with job_id, document_id, and processing status
    """
    import uuid
    from pathlib import Path

    from src.common.hashing import compute_file_hash
    from src.db.models import ReferenceDocument
    from src.db.session import async_session_factory
    from src.ingestion.orchestrator import ingestion_orchestrator
    from src.storage.files import file_storage

    try:
        path = Path(file_path)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
            }

        # Compute hash for idempotency
        file_hash = compute_file_hash(path)

        async with async_session_factory() as session:
            # Check if document already exists
            from sqlalchemy import select

            result = await session.execute(
                select(ReferenceDocument).where(ReferenceDocument.file_hash == file_hash)
            )
            existing = result.scalar_one_or_none()

            if existing:
                return {
                    "success": True,
                    "job_id": existing.job_id,
                    "document_id": existing.id,
                    "status": existing.status,
                    "message": "Document already exists in the system",
                }

            # Create document record
            job_id = str(uuid.uuid4())
            file_path_saved = file_storage.save_upload(path.read_bytes(), path.name, file_hash)

            document = ReferenceDocument(
                file_hash=file_hash,
                original_path=str(file_path_saved),
                status="Checking",
                job_id=job_id,
                discipline=discipline,
            )

            session.add(document)
            await session.commit()
            await session.refresh(document)

            # Process document
            try:
                result = await ingestion_orchestrator.process_document(
                    file_path=path,
                    document_id=document.id,
                    discipline=discipline,
                )

                # Update status to approved
                document.status = "Approved"
                await session.commit()

                return {
                    "success": True,
                    "job_id": job_id,
                    "document_id": document.id,
                    "status": "Approved",
                    "message": "Document processed and approved",
                    "extracted_data": {
                        "document_number": result.get("parsed_data", {}).get("document_number"),
                        "title": result.get("parsed_data", {}).get("title"),
                        "revision": result.get("parsed_data", {}).get("revision"),
                        "chunks_created": len(result.get("child_chunks", [])),
                    },
                }
            except Exception as e:
                document.status = "Rejected"
                await session.commit()
                return {
                    "success": False,
                    "job_id": job_id,
                    "document_id": document.id,
                    "status": "Rejected",
                    "error": str(e),
                }

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Ingestion failed: {str(e)}",
        }


@mcp.tool()
async def validate_document(
    document_id: int,
) -> dict[str, Any]:
    """
    Validate a document against configured validation rules.

    Args:
        document_id: ID of the document to validate

    Returns:
        Dictionary with validation results (passed/failed status and rule details)
    """
    from sqlalchemy import select

    from src.db.models import ReferenceDocument
    from src.db.session import async_session_factory
    from src.validation.gateway import validation_gateway

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(ReferenceDocument).where(ReferenceDocument.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                return {
                    "success": False,
                    "error": f"Document not found: {document_id}",
                }

            # Build parsed data from document
            parsed_data = {
                "document_number": document.document_number,
                "title": document.title,
                "revision": document.revision,
                "issue_status": document.issue_status,
                "contract_number": document.contract_number,
                "discipline": document.discipline,
                "page_count": document.page_count,
            }

            # Run validation
            validation_result = await validation_gateway.validate_document(
                document_id=document_id,
                parsed_data=parsed_data,
                discipline=document.discipline,
            )

            return {
                "success": True,
                "document_id": document_id,
                "passed": validation_result["passed"],
                "rules_evaluated": validation_result["rules_evaluated"],
                "rules_failed": validation_result["rules_failed"],
                "failed_rules": validation_result["failed_rules"],
                "warnings": validation_result["warnings"],
                "validated_at": validation_result["validated_at"],
            }

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Validation failed: {str(e)}",
        }


@mcp.tool()
async def search_knowledge_base(
    query: str,
    limit: int = 10,
    discipline: str | None = None,
    document_ids: list[int] | None = None,
) -> dict[str, Any]:
    """
    Search the knowledge base using hybrid search (vector + full-text).

    Args:
        query: Search query string
        limit: Maximum number of results (default: 10)
        discipline: Optional discipline filter (ELC/MEC/INS/SIM)
        document_ids: Optional list of document IDs to search within

    Returns:
        Dictionary with search results and relevance scores
    """
    from src.search.qa import qa_service

    try:
        result = await qa_service.search(
            query=query,
            limit=limit,
            discipline=discipline,
            document_ids=document_ids,
        )

        return {
            "success": True,
            "query": result["query"],
            "results": result["results"],
            "total": result["total"],
        }

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
        }


@mcp.tool()
async def submit_to_docon(
    document_id: int,
    discipline: str | None = None,
) -> dict[str, Any]:
    """
    Submit an approved document to the Document Controller.

    Args:
        document_id: ID of the document to submit
        discipline: Discipline for submission (uses document's discipline if not specified)

    Returns:
        Dictionary with submission status and confirmation reference
    """
    from datetime import datetime

    from sqlalchemy import select

    from src.db.models import DisciplineSubmission, ReferenceDocument
    from src.db.session import async_session_factory
    from src.submission.docon_client import docon_client

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(ReferenceDocument).where(ReferenceDocument.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                return {
                    "success": False,
                    "error": f"Document not found: {document_id}",
                }

            if document.status != "Approved":
                return {
                    "success": False,
                    "error": f"Document must be approved before submission. Current status: {document.status}",
                }

            submission_discipline = discipline or document.discipline

            # Call Document Controller API
            docon_result = await docon_client.submit_document(
                document_id=document_id,
                file_hash=document.file_hash,
                document_number=document.document_number,
                discipline=submission_discipline,
            )

            # Log submission
            submission = DisciplineSubmission(
                document_id=document_id,
                discipline=submission_discipline,
                status="pass",
                file_hash=document.file_hash,
                docon_confirmation_ref=docon_result.get("confirmation_ref"),
                model_version=settings.ollama_model,
                submitted_at=datetime.utcnow(),
            )

            session.add(submission)
            await session.commit()

            return {
                "success": True,
                "document_id": document_id,
                "discipline": submission_discipline,
                "submission_id": submission.id,
                "confirmation_ref": docon_result.get("confirmation_ref"),
                "submitted_at": submission.submitted_at.isoformat(),
            }

    except Exception as e:
        logger.error(f"Submission failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Submission failed: {str(e)}",
        }


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await mcp.server.run(
            read_stream,
            write_stream,
            mcp.server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_server())
