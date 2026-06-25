"""Upload router for document ingestion."""
import logging
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.db.models import ReferenceDocument
from src.api.schemas import UploadResponse, StatusResponse
from src.storage.files import file_storage
from src.common.hashing import compute_content_hash
from src.common.exceptions import IngestionError, FileStorageError
from src.common.constants import SUPPORTED_EXTENSIONS, Discipline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    discipline: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for processing.
    
    Args:
        file: Uploaded file
        discipline: Optional discipline tag (ELC/MEC/INS/SIM)
        db: Database session
        
    Returns:
        Upload response with job_id and initial status
    """
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: {file_ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )
        
        # Validate discipline if provided
        if discipline and discipline not in [d.value for d in Discipline]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid discipline: {discipline}. Must be one of: ELC, MEC, INS, SIM",
            )
        
        # Read file content
        file_content = await file.read()
        
        # Compute hash for idempotency
        file_hash = compute_content_hash(file_content)
        
        # Check if file already exists (idempotent upload)
        existing_doc = await db.execute(
            select(ReferenceDocument).where(ReferenceDocument.file_hash == file_hash)
        )
        existing = existing_doc.scalar_one_or_none()
        
        if existing:
            logger.info(f"Duplicate upload detected: {file_hash[:16]}... (document_id={existing.id})")
            return UploadResponse(
                job_id=existing.job_id or str(uuid.uuid4()),
                document_id=existing.id,
                filename=file.filename,
                status=existing.status,
                message="Document already exists in the system",
            )
        
        # Save file to storage
        try:
            file_path = file_storage.save_upload(file_content, file.filename, file_hash)
        except FileStorageError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {e}",
            )
        
        # Create document record
        job_id = str(uuid.uuid4())
        document = ReferenceDocument(
            file_hash=file_hash,
            original_path=str(file_path),
            status="Checking",
            job_id=job_id,
            discipline=discipline,
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        logger.info(
            f"Document uploaded: id={document.id}, job_id={job_id}, "
            f"filename={file.filename}, discipline={discipline}"
        )
        
        # TODO: Enqueue background processing task (Celery)
        # For now, processing will be triggered separately
        
        return UploadResponse(
            job_id=job_id,
            document_id=document.id,
            filename=file.filename,
            status="Checking",
            message="Document uploaded successfully. Processing will begin shortly.",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_upload_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get processing status for an uploaded document.
    
    Args:
        job_id: Job ID from upload response
        db: Database session
        
    Returns:
        Status response with current processing state
    """
    try:
        # Find document by job_id
        result = await db.execute(
            select(ReferenceDocument).where(ReferenceDocument.job_id == job_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}",
            )
        
        # Calculate progress
        progress = 100 if document.status in ["Approved", "Rejected"] else 50
        
        return StatusResponse(
            job_id=job_id,
            document_id=document.id,
            status=document.status,
            progress=progress,
            message=None,
            rejection_note=None,  # TODO: Fetch from discipline_submissions if rejected
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}",
        )


# Import at bottom to avoid circular imports
from sqlalchemy import select