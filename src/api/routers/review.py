"""Review router for admin review queue - low-confidence OCR regions."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from src.db.session import get_db
from src.db.models import LowConfidenceRegion
from src.api.schemas import (
    LowConfidenceRegionResponse,
    ReviewUpdateRequest,
)
from src.common.exceptions import AuthorizationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/flagged", response_model=list[LowConfidenceRegionResponse])
async def get_flagged_regions(
    document_id: Optional[int] = None,
    reviewed: Optional[bool] = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Get low-confidence OCR regions flagged for human review.
    Admin-only endpoint.
    
    Args:
        document_id: Optional document ID filter
        reviewed: Filter by reviewed status (default: false = unreviewed)
        db: Database session
        
    Returns:
        List of low-confidence regions
    """
    try:
        # Build query
        query = select(LowConfidenceRegion).where(LowConfidenceRegion.reviewed == reviewed)
        
        if document_id:
            query = query.where(LowConfidenceRegion.document_id == document_id)
        
        # Order by creation time (oldest first for review)
        query = query.order_by(LowConfidenceRegion.created_at.asc())
        
        # Execute query
        result = await db.execute(query)
        regions = result.scalars().all()
        
        # Transform to response format
        return [
            LowConfidenceRegionResponse(
                id=region.id,
                document_id=region.document_id,
                page=region.page,
                bbox=region.bbox,
                text=region.text,
                confidence=region.confidence,
                reviewed=region.reviewed,
                reviewed_by=region.reviewed_by,
                reviewed_at=region.reviewed_at,
                created_at=region.created_at,
            )
            for region in regions
        ]
    
    except Exception as e:
        logger.error(f"Failed to get flagged regions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get flagged regions: {str(e)}",
        )


@router.patch("/{region_id}", response_model=LowConfidenceRegionResponse)
async def update_review_status(
    region_id: int,
    request: ReviewUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update review status for a low-confidence region.
    Admin-only endpoint.
    
    Args:
        region_id: Region ID to update
        request: Review update request
        db: Database session
        
    Returns:
        Updated region
    """
    try:
        # Get region
        result = await db.execute(
            select(LowConfidenceRegion).where(LowConfidenceRegion.id == region_id)
        )
        region = result.scalar_one_or_none()
        
        if not region:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Region not found: {region_id}",
            )
        
        # Update region
        region.reviewed = request.reviewed
        region.reviewed_by = request.reviewed_by
        region.reviewed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(region)
        
        logger.info(
            f"Region {region_id} marked as {'reviewed' if request.reviewed else 'unreviewed'} "
            f"by {request.reviewed_by}"
        )
        
        return LowConfidenceRegionResponse(
            id=region.id,
            document_id=region.document_id,
            page=region.page,
            bbox=region.bbox,
            text=region.text,
            confidence=region.confidence,
            reviewed=region.reviewed,
            reviewed_by=region.reviewed_by,
            reviewed_at=region.reviewed_at,
            created_at=region.created_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update region {region_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update region: {str(e)}",
        )


@router.get("/stats/summary")
async def get_review_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary statistics for the review queue.
    
    Args:
        db: Database session
        
    Returns:
        Summary statistics
    """
    try:
        from sqlalchemy import func
        
        # Count total flagged regions
        total_query = select(func.count()).select_from(LowConfidenceRegion)
        total_result = await db.execute(total_query)
        total = total_result.scalar()
        
        # Count unreviewed regions
        unreviewed_query = select(func.count()).where(LowConfidenceRegion.reviewed == False)
        unreviewed_result = await db.execute(unreviewed_query)
        unreviewed = unreviewed_result.scalar()
        
        # Count reviewed regions
        reviewed = total - unreviewed
        
        # Get average confidence
        avg_conf_query = select(func.avg(LowConfidenceRegion.confidence))
        avg_conf_result = await db.execute(avg_conf_query)
        avg_confidence = avg_conf_result.scalar() or 0.0
        
        return {
            "total_flagged": total,
            "unreviewed": unreviewed,
            "reviewed": reviewed,
            "average_confidence": round(float(avg_confidence), 3),
            "review_progress": round((reviewed / total * 100) if total > 0 else 0, 1),
        }
    
    except Exception as e:
        logger.error(f"Failed to get review stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review stats: {str(e)}",
        )


# Import datetime for timestamp
from datetime import datetime