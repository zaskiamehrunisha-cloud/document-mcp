"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response for document upload."""

    job_id: str
    document_id: int
    filename: str
    status: str
    message: str


class StatusResponse(BaseModel):
    """Response for upload status check."""

    job_id: str
    document_id: int
    status: str  # Checking, Approved, Rejected
    progress: int  # 0-100
    message: str | None = None
    rejection_note: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    """Request for search."""

    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)
    discipline: str | None = None
    document_ids: list[int] | None = None


class SearchResult(BaseModel):
    """Single search result."""

    chunk_id: int
    content: str
    document_id: int
    document_number: str | None
    title: str | None
    discipline: str | None
    score: float
    search_type: str


class SearchResponse(BaseModel):
    """Response for search."""

    query: str
    results: list[SearchResult]
    total: int


class AskRequest(BaseModel):
    """Request for Q&A."""

    query: str = Field(..., min_length=1, max_length=2000)
    discipline: str | None = None
    document_ids: list[int] | None = None


class Citation(BaseModel):
    """Citation in answer."""

    document_number: str
    title: str | None
    page_or_sheet: str


class AskResponse(BaseModel):
    """Response for Q&A."""

    answer: str
    confidence: str  # High, Medium, Low
    citations: list[Citation]
    query: str
    context_chunks_used: int


class DocumentResponse(BaseModel):
    """Response for document details."""

    id: int
    document_number: str | None
    title: str | None
    revision: str | None
    issue_status: str | None
    contract_number: str | None
    discipline: str | None
    page_count: int | None
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Response for document list."""

    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class LowConfidenceRegionResponse(BaseModel):
    """Response for low-confidence region."""

    id: int
    document_id: int
    page: int
    bbox: dict[str, Any]
    text: str | None
    confidence: float
    reviewed: bool
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ReviewUpdateRequest(BaseModel):
    """Request to update review status."""

    reviewed: bool = True
    reviewed_by: str = Field(..., min_length=1, max_length=100)


class ValidationRequest(BaseModel):
    """Request for document validation."""

    document_id: int


class ValidationResponse(BaseModel):
    """Response for validation."""

    document_id: int
    passed: bool
    rules_evaluated: int
    rules_failed: int
    failed_rules: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    validated_at: str


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
    ollama: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Agent Action Schemas
class AgentActionResponse(BaseModel):
    """Response for an agent action."""

    id: int
    document_id: int | None
    job_id: str | None
    action_type: str
    decision: str
    reasoning: str | None
    context: dict[str, Any] | None
    model_version: str | None
    confidence: float | None
    success: bool
    created_at: datetime


class AgentActionsListResponse(BaseModel):
    """Response for listing agent actions."""

    actions: list[AgentActionResponse]
    total: int
    limit: int
    offset: int


class AgentActionStatsResponse(BaseModel):
    """Response for agent action statistics."""

    period_hours: int
    total_actions: int
    successful_actions: int
    success_rate: float
    by_action_type: dict[str, int]
    by_decision: dict[str, int]
    average_confidence: float | None
    cutoff: str


# System Metrics Schemas
class DocumentMetrics(BaseModel):
    """Document metrics."""

    total: int
    by_status: dict[str, int]


class ReviewQueueMetrics(BaseModel):
    """Review queue metrics."""

    unreviewed_regions: int


class ActivityMetrics(BaseModel):
    """Activity metrics."""

    recent_agent_actions: int
    recent_qa_queries: int
    total_submissions: int


class SystemMetricsResponse(BaseModel):
    """Response for system metrics."""

    documents: DocumentMetrics
    review_queue: ReviewQueueMetrics
    activity: ActivityMetrics
    timestamp: str


# WebSocket Status Update
class WebSocketStatusUpdate(BaseModel):
    """WebSocket status update message."""

    type: str = "status_update"
    job_id: str
    document_id: int | None = None
    status: str
    progress: int
    rejection_note: dict[str, Any] | None = None
    updated_at: str | None = None
