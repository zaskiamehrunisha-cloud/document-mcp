"""
SQLAlchemy ORM models for DOCINTEL.
Defines the complete database schema for the knowledge base.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# Reference Documents
# ---------------------------------------------------------------------------

class ReferenceDocument(Base):
    """
    Master record for a reference or submitted document.
    Reference documents are the seeded controlled standards;
    submitted documents are user uploads validated against them.
    """
    __tablename__ = "reference_documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    contract_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    discipline: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    drawing_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    area_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    current_revision: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    issue_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_reference: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    sheet_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    revisions: Mapped[list["DocumentRevision"]] = relationship(
        "DocumentRevision", back_populates="document", cascade="all, delete-orphan"
    )
    structured_records: Mapped[list["StructuredRecord"]] = relationship(
        "StructuredRecord", back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    submission_logs: Mapped[list["SubmissionLog"]] = relationship(
        "SubmissionLog", back_populates="document", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        UniqueConstraint("document_number", "current_revision", name="uq_doc_revision"),
    )


class DocumentRevision(Base):
    """Revision history for a document."""
    __tablename__ = "document_revisions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("reference_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision: Mapped[str] = mapped_column(String(10), nullable=False)
    issue_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    revision_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prepared_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    checked_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document: Mapped["ReferenceDocument"] = relationship("ReferenceDocument", back_populates="revisions")


# ---------------------------------------------------------------------------
# Structured Records (Parsed Output)
# ---------------------------------------------------------------------------

class StructuredRecord(Base):
    """
    The structured record produced by the parser for a document.
    Contains the parsed fields plus a JSONB payload for flexible/auxiliary data.
    """
    __tablename__ = "structured_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("reference_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Core extracted fields (denormalized for query performance)
    document_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    revision: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    contract_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    issue_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    client: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    project_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    drawing_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    discipline: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    page: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sheet_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Flexible payload for auxiliary/array fields
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # Quality signals
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    extraction_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_layer: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document: Mapped["ReferenceDocument"] = relationship("ReferenceDocument", back_populates="structured_records")
    comment_responses: Mapped[list["CommentResponse"]] = relationship(
        "CommentResponse", back_populates="record", cascade="all, delete-orphan"
    )
    legend_entries: Mapped[list["LegendEntry"]] = relationship(
        "LegendEntry", back_populates="record", cascade="all, delete-orphan"
    )
    drawing_index_entries: Mapped[list["DrawingIndexEntry"]] = relationship(
        "DrawingIndexEntry", back_populates="record", cascade="all, delete-orphan"
    )
    equipment_ratings: Mapped[list["EquipmentRating"]] = relationship(
        "EquipmentRating", back_populates="record", cascade="all, delete-orphan"
    )


class CommentResponse(Base):
    """Comment/response table entry extracted from a document."""
    __tablename__ = "comment_responses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("structured_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    comment_ref: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    comment_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    record: Mapped["StructuredRecord"] = relationship("StructuredRecord", back_populates="comment_responses")


class LegendEntry(Base):
    """Legend/symbol entry extracted from a drawing."""
    __tablename__ = "legend_entries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("structured_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    record: Mapped["StructuredRecord"] = relationship("StructuredRecord", back_populates="legend_entries")


class DrawingIndexEntry(Base):
    """Drawing index entry extracted from an index document."""
    __tablename__ = "drawing_index_entries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("structured_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    drawing_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    drawing_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    revision: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    sheet_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    record: Mapped["StructuredRecord"] = relationship("StructuredRecord", back_populates="drawing_index_entries")


class EquipmentRating(Base):
    """Equipment rating entry extracted from a document."""
    __tablename__ = "equipment_ratings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("structured_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipment_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    parameter: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    record: Mapped["StructuredRecord"] = relationship("StructuredRecord", back_populates="equipment_ratings")


# ---------------------------------------------------------------------------
# Validation Rules
# ---------------------------------------------------------------------------

class ValidationRule(Base):
    """
    Validation rules derived from the reference document set.
    These rules are applied to new submissions to check conformance.
    """
    __tablename__ = "validation_rules"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# ---------------------------------------------------------------------------
# Submission Audit Log
# ---------------------------------------------------------------------------

class SubmissionLog(Base):
    """
    Audit log for every submission decision (pass/fail, violations, DOCON reference).
    Provides full traceability for compliance.
    """
    __tablename__ = "submission_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("reference_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    discipline: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    submitter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    violations: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    docon_reference: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    document: Mapped[Optional["ReferenceDocument"]] = relationship("ReferenceDocument", back_populates="submission_logs")


# ---------------------------------------------------------------------------
# Document Chunks (for RAG / pgvector)
# ---------------------------------------------------------------------------

class DocumentChunk(Base):
    """
    A chunk of text from a document, with its embedding vector.
    Used for semantic search and RAG retrieval.
    """
    __tablename__ = "document_chunks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("reference_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_or_sheet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    source_layer: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1024), nullable=True)
    chunk_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document: Mapped["ReferenceDocument"] = relationship("ReferenceDocument", back_populates="chunks")
    
    __table_args__ = (
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )