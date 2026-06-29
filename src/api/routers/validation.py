"""Validation router for document validation."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ValidationRequest, ValidationResponse
from src.db.models import ReferenceDocument
from src.db.session import get_db
from src.validation.gateway import validation_gateway

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validate", tags=["validation"])


@router.post("/", response_model=ValidationResponse)
async def validate_document(
    request: ValidationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate a document against configured validation rules.

    Args:
        request: Validation request with document ID
        db: Database session

    Returns:
        Validation result with passed/failed status
    """
    try:
        # Get document
        result = await db.execute(
            select(ReferenceDocument).where(ReferenceDocument.id == request.document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {request.document_id}",
            )

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
            document_id=request.document_id,
            parsed_data=parsed_data,
            discipline=document.discipline,
        )

        return ValidationResponse(
            document_id=validation_result["document_id"],
            passed=validation_result["passed"],
            rules_evaluated=validation_result["rules_evaluated"],
            rules_failed=validation_result["rules_failed"],
            failed_rules=validation_result["failed_rules"],
            warnings=validation_result["warnings"],
            validated_at=validation_result["validated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )
