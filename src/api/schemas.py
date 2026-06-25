"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import Optional, Any
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
    message: Optional[str] = None
    rejection_note: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    """Request for search."""
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)
    discipline: Optional[str] = None
    document_ids: Optional[list[int]] = None


class SearchResult(BaseModel):
    """Single search result."""
    chunk_id: int
    content: str
    document_id: int
    document_number: Optional[str]
    title: Optional[str]
    discipline: Optional[str]
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
    discipline: Optional[str] = None
    document_ids: Optional[list[int]] = None


class Citation(BaseModel):
    """Citation in answer."""
    document_number: str
    title: Optional[str]
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
    document_number: Optional[str]
    title: Optional[str]
    revision: Optional[str]
    issue_status: Optional[str]
    contract_number: Optional[str]
    discipline: Optional[str]
    page_count: Optional[int]
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
    text: Optional[str]
    confidence: float
    reviewed: bool
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
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
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    ollama: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)