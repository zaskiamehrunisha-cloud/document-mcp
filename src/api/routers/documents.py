"""Documents router for listing and retrieving document details."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from src.db.session import get_db
from src.db.models import ReferenceDocument
from src.api.schemas import DocumentResponse, DocumentListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List approved documents with pagination.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of documents per page
        discipline: Optional discipline filter
        status: Optional status filter
        db: Database session
        
    Returns:
        Paginated list of documents
    """
    try:
        # Build query
        query = select(ReferenceDocument)
        
        # Apply filters
        if discipline:
            query = query.where(ReferenceDocument.discipline == discipline)
        
        if status:
            query = query.where(ReferenceDocument.status == status)
        else:
            # Default to approved documents
            query = query.where(ReferenceDocument.status == "Approved")
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(ReferenceDocument.created_at.desc())
        
        # Execute query
        result = await db.execute(query)
        documents = result.scalars().all()
        
        # Transform to response format
        doc_responses = [
            DocumentResponse(
                id=doc.id,
                document_number=doc.document_number,
                title=doc.title,
                revision=doc.revision,
                issue_status=doc.issue_status,
                contract_number=doc.contract_number,
                discipline=doc.discipline,
                page_count=doc.page_count,
                status=doc.status,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ]
        
        return DocumentListResponse(
            documents=doc_responses,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get details for a specific document.
    
    Args:
        document_id: Document ID
        db: Database session
        
    Returns:
        Document details
    """
    try:
        result = await db.execute(
            select(ReferenceDocument).where(ReferenceDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}",
            )
        
        return DocumentResponse(
            id=document.id,
            document_number=document.document_number,
            title=document.title,
            revision=document.revision,
            issue_status=document.issue_status,
            contract_number=document.contract_number,
            discipline=document.discipline,
            page_count=document.page_count,
            status=document.status,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}",
        )