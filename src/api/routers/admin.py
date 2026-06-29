"""Admin router for system metrics and agent action logs."""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    AgentAction,
    DisciplineSubmission,
    LowConfidenceRegion,
    QAQueryLog,
    ReferenceDocument,
)
from src.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics")
async def get_system_metrics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get system-wide metrics for admin dashboard.

    Returns:
        System metrics including queue lengths, document counts, and statistics
    """
    try:
        # Document counts by status
        status_counts = {}
        for status in ["Checking", "Approved", "Rejected"]:
            query = select(func.count()).where(ReferenceDocument.status == status)
            result = await db.execute(query)
            status_counts[status] = result.scalar() or 0

        # Total documents
        total_query = select(func.count()).select_from(ReferenceDocument)
        total_result = await db.execute(total_query)
        total_documents = total_result.scalar() or 0

        # Low confidence regions
        unreviewed_query = select(func.count()).where(not LowConfidenceRegion.reviewed)
        unreviewed_result = await db.execute(unreviewed_query)
        unreviewed_regions = unreviewed_result.scalar() or 0

        # Recent agent actions (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_actions_query = select(func.count()).where(AgentAction.created_at >= yesterday)
        recent_actions_result = await db.execute(recent_actions_query)
        recent_actions = recent_actions_result.scalar() or 0

        # Recent Q&A queries
        recent_qa_query = select(func.count()).where(QAQueryLog.created_at >= yesterday)
        recent_qa_result = await db.execute(recent_qa_query)
        recent_qa = recent_qa_result.scalar() or 0

        # Discipline submissions
        submissions_query = select(func.count()).select_from(DisciplineSubmission)
        submissions_result = await db.execute(submissions_query)
        total_submissions = submissions_result.scalar() or 0

        return {
            "documents": {
                "total": total_documents,
                "by_status": status_counts,
            },
            "review_queue": {
                "unreviewed_regions": unreviewed_regions,
            },
            "activity": {
                "recent_agent_actions": recent_actions,
                "recent_qa_queries": recent_qa,
                "total_submissions": total_submissions,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}",
        )


@router.get("/actions")
async def get_agent_actions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    action_type: str | None = None,
    document_id: int | None = None,
    job_id: str | None = None,
    success: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get agent action logs with filtering.

    Args:
        limit: Maximum number of results
        offset: Offset for pagination
        action_type: Filter by action type
        document_id: Filter by document ID
        job_id: Filter by job ID
        success: Filter by success status
        db: Database session

    Returns:
        Paginated list of agent actions
    """
    try:
        # Build query
        query = select(AgentAction)

        # Apply filters
        if action_type:
            query = query.where(AgentAction.action_type == action_type)
        if document_id:
            query = query.where(AgentAction.document_id == document_id)
        if job_id:
            query = query.where(AgentAction.job_id == job_id)
        if success is not None:
            query = query.where(AgentAction.success == success)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        query = query.offset(offset).limit(limit).order_by(AgentAction.created_at.desc())

        # Execute query
        result = await db.execute(query)
        actions = result.scalars().all()

        return {
            "actions": [
                {
                    "id": action.id,
                    "document_id": action.document_id,
                    "job_id": action.job_id,
                    "action_type": action.action_type,
                    "decision": action.decision,
                    "reasoning": action.reasoning,
                    "context": action.context,
                    "model_version": action.model_version,
                    "confidence": action.confidence,
                    "success": action.success,
                    "created_at": action.created_at.isoformat() if action.created_at else None,
                }
                for action in actions
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Failed to get agent actions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent actions: {str(e)}",
        )


@router.get("/actions/stats")
async def get_agent_action_stats(
    hours: int = Query(24, ge=1, le=168),  # Default: last 24 hours, max: 7 days
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics about agent actions over a time period.

    Args:
        hours: Number of hours to look back
        db: Database session

    Returns:
        Statistics about agent actions
    """
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Total actions in period
        total_query = select(func.count()).where(AgentAction.created_at >= cutoff)
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        # Success rate
        success_query = select(func.count()).where(
            AgentAction.created_at >= cutoff,
            AgentAction.success,
        )
        success_result = await db.execute(success_query)
        successful = success_result.scalar() or 0

        # Actions by type
        type_query = (
            select(
                AgentAction.action_type,
                func.count().label("count"),
            )
            .where(
                AgentAction.created_at >= cutoff,
            )
            .group_by(AgentAction.action_type)
        )
        type_result = await db.execute(type_query)
        by_type = {row.action_type: row.count for row in type_result}

        # Decisions breakdown
        decision_query = (
            select(
                AgentAction.decision,
                func.count().label("count"),
            )
            .where(
                AgentAction.created_at >= cutoff,
            )
            .group_by(AgentAction.decision)
        )
        decision_result = await db.execute(decision_query)
        by_decision = {row.decision: row.count for row in decision_result}

        # Average confidence
        avg_conf_query = select(func.avg(AgentAction.confidence)).where(
            AgentAction.created_at >= cutoff,
            AgentAction.confidence.isnot(None),
        )
        avg_conf_result = await db.execute(avg_conf_query)
        avg_confidence = avg_conf_result.scalar()

        return {
            "period_hours": hours,
            "total_actions": total,
            "successful_actions": successful,
            "success_rate": round((successful / total * 100) if total > 0 else 0, 1),
            "by_action_type": by_type,
            "by_decision": by_decision,
            "average_confidence": round(float(avg_confidence), 3) if avg_confidence else None,
            "cutoff": cutoff.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get agent action stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent action stats: {str(e)}",
        )
