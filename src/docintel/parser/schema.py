"""
Pydantic schemas for structured records in DOCINTEL.
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CommentResponse(BaseModel):
    """Comment/response table entry."""
    comment_ref: Optional[str] = None
    comment_text: Optional[str] = None
    response_text: Optional[str] = None
    status: Optional[str] = None


class LegendEntry(BaseModel):
    """Legend/symbol entry from a drawing."""
    symbol: Optional[str] = None
    description: Optional[str] = None


class DrawingIndexEntry(BaseModel):
    """Drawing index entry."""
    drawing_number: Optional[str] = None
    drawing_title: Optional[str] = None
    revision: Optional[str] = None
    sheet_count: Optional[int] = None


class EquipmentRating(BaseModel):
    """Equipment rating entry."""
    equipment_tag: Optional[str] = None
    parameter: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None


class RevisionHistoryEntry(BaseModel):
    """Revision history entry."""
    revision: str
    date: Optional[str] = None
    description: Optional[str] = None
    prepared_by: Optional[str] = None
    checked_by: Optional[str] = None
    approved_by: Optional[str] = None


class StructuredRecord(BaseModel):
    """Structured record produced by the parser."""
    document_number: Optional[str] = None
    title: Optional[str] = None
    revision: Optional[str] = None
    contract_number: Optional[str] = None
    issue_status: Optional[str] = None
    client: Optional[str] = None
    project_title: Optional[str] = None
    location: Optional[str] = None
    contractor: Optional[str] = None
    consortium: Optional[str] = None
    discipline: Optional[str] = None
    drawing_type: Optional[str] = None
    area_code: Optional[str] = None
    page: Optional[str] = None
    sheet_count: Optional[int] = None
    description: Optional[str] = None
    comments: list[CommentResponse] = []
    revision_history: list[RevisionHistoryEntry] = []
    legend_entries: list[LegendEntry] = []
    drawing_index: list[DrawingIndexEntry] = []
    equipment_ratings: list[EquipmentRating] = []
    confidence: float = 0.0
    extraction_method: Optional[str] = None
    source_layer: Optional[str] = None


class StructuredRecordCreate(BaseModel):
    """Schema for creating a structured record."""
    document_id: int
    payload: dict[str, Any]
    confidence: float = 0.0
    extraction_method: Optional[str] = None
    source_layer: Optional[str] = None


class StructuredRecordUpdate(BaseModel):
    """Schema for updating a structured record."""
    payload: Optional[dict[str, Any]] = None
    confidence: Optional[float] = None
    extraction_method: Optional[str] = None
    source_layer: Optional[str] = None