"""SQLAlchemy 2.0 async models for all 11 database tables."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Self, mapped_column, relationship

if TYPE_CHECKING:
    from . import ReferenceDocument


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class ReferenceDocument(Base):
    """Root entity for all ingested documents."""

    __tablename__ = "reference_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_number: Mapped[str | None] = mapped_column(String(50), index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    revision: Mapped[str | None] = mapped_column(String(20))
    issue_status: Mapped[str | None] = mapped_column(String(10))
    contract_number: Mapped[str | None] = mapped_column(String(100))
    discipline: Mapped[str | None] = mapped_column(String(10), index=True)
    page_count: Mapped[int | None] = mapped_column(Integer)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    original_path: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="Checking", index=True)
    job_id: Mapped[str | None] = mapped_column(String(100), index=True)
    model_version: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    revision_history: Mapped[list[RevisionHistory]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    comments_response: Mapped[list[CommentsResponse]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    legend_symbols: Mapped[list[LegendSymbol]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    equipment_ratings: Mapped[list[EquipmentRating]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    drawing_index: Mapped[list[DrawingIndex]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    discipline_submissions: Mapped[list[DisciplineSubmission]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    low_confidence_regions: Mapped[list[LowConfidenceRegion]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    document_chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    agent_actions: Mapped[list[AgentAction]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class RevisionHistory(Base):
    """Revision history rows extracted from documents."""

    __tablename__ = "revision_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("reference_documents.id"))
    rev: Mapped[str | None] = mapped_column(String(20))
    date: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(1000))
    prepared_by: Mapped[str | None] = mapped_column(String(200))
    checked_by: Mapped[str | None] = mapped_column(String(200))
    approved_by: Mapped[str | None] = mapped_column(String(200))

    # Relationships
    document: Mapped[ReferenceDocument] = relationship(back_populates="revision_history")


class CommentsResponse(Base):
    """Comment/response rows for rejection notes and review tracking."""

    __tablename__ = "comments_response"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("reference_documents.id"))
    seq: Mapped[int] = mapped_column(Integer)
    client_comment: Mapped[str | None] = mapped_column(String(2000))
    contractor_response: Mapped[str | None] = mapped_column(String(2000))

    # Relationships
    document: Mapped[ReferenceDocument] = relationship(back_populates="comments_response")

    __table_args__ = (UniqueConstraint("document_id", "seq", name="uq_comments_document_seq"),)


class LegendSymbol(Base):
    """Legend symbols extracted from drawings."""

    __tablename__ = "legend_symbols"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("reference_documents.id"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500))
    discipline: Mapped[str | None] = mapped_column(String(10))

    # Relationships
    document: Mapped[ReferenceDocument | None] = relationship(back_populates="legend_symbols")


class EquipmentRating(Base):
    """Equipment ratings extracted from SLD sheets."""

    __tablename__ = "equipment_ratings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("reference_documents.id"))
    tag: Mapped[str | None] = mapped_column(String(100))
    rating: Mapped[str | None] = mapped_column(String(200))
    voltage: Mapped[str | None] = mapped_column(String(50))
    phase: Mapped[str | None] = mapped_column(String(50))
    frequency: Mapped[str | None] = mapped_column(String(50))
    power: Mapped[str | None] = mapped_column(String(100))
    sheet: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    document: Mapped[ReferenceDocument] = relationship(back_populates="equipment_ratings")


class DrawingIndex(Base):
    """Drawing index entries for multi-sheet documents."""

    __tablename__ = "drawing_index"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("reference_documents.id"))
    sheet_no: Mapped[str | None] = mapped_column(String(20))
    sheet_title: Mapped[str | None] = mapped_column(String(500))
    drawing_number: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    document: Mapped[ReferenceDocument] = relationship(back_populates="drawing_index")


class ValidationRule(Base):
    """Configurable validation rules for document validation."""

    __tablename__ = "validation_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    rule_type: Mapped[str] = mapped_column(String(20))  # warning or blocking
    discipline: Mapped[str | None] = mapped_column(String(10), nullable=True)
    definition: Mapped[dict] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class DisciplineSubmission(Base):
    """Log of document submissions to the Document Controller."""

    __tablename__ = "discipline_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("reference_documents.id"))
    discipline: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10))  # pass or fail
    file_hash: Mapped[str] = mapped_column(String(64))
    docon_confirmation_ref: Mapped[str | None] = mapped_column(String(200))
    rejection_note: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100))
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document: Mapped[ReferenceDocument] = relationship(back_populates="discipline_submissions")


class LowConfidenceRegion(Base):
    """Low-confidence OCR regions flagged for human review."""

    __tablename__ = "low_confidence_regions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("reference_documents.id"))
    page: Mapped[int] = mapped_column(Integer)
    bbox: Mapped[dict] = mapped_column(JSONB)  # [x1, y1, x2, y2]
    text: Mapped[str | None] = mapped_column(String(2000))
    confidence: Mapped[float] = mapped_column(Float)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document: Mapped[ReferenceDocument] = relationship(back_populates="low_confidence_regions")

    __table_args__ = (Index("idx_lowconf_document_page", "document_id", "page"),)


class DocumentChunk(Base):
    """Parent and child chunks with embeddings for retrieval."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("reference_documents.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(10))  # parent or child
    content: Mapped[str] = mapped_column(String(10000))
    token_count: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    tsv: Mapped[str | None] = mapped_column(String, nullable=True)  # tsvector
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document: Mapped[ReferenceDocument] = relationship(back_populates="document_chunks")
    parent: Mapped[Self | None] = relationship(
        remote_side="DocumentChunk.id",
        back_populates="children",
    )
    children: Mapped[list[Self]] = relationship(back_populates="parent")

    __table_args__ = (
        Index(
            "idx_document_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("idx_document_chunks_tsv", "tsv", postgresql_using="gin"),
    )


class QAQueryLog(Base):
    """Audit log for Q&A queries."""

    __tablename__ = "qa_query_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query_text: Mapped[str] = mapped_column(String(2000))
    answer: Mapped[str] = mapped_column(String(5000))
    confidence_level: Mapped[str] = mapped_column(String(20))  # High/Medium/Low
    cited_document_ids: Mapped[list[int]] = mapped_column(JSONB)
    retrieved_chunk_ids: Mapped[list[int]] = mapped_column(JSONB)
    model_version: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentAction(Base):
    """Orchestrator agent decision logging for auditing and debugging."""

    __tablename__ = "agent_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("reference_documents.id"), nullable=True
    )
    job_id: Mapped[str | None] = mapped_column(String(100), index=True)
    action_type: Mapped[str] = mapped_column(
        String(50)
    )  # ocr_quality_eval, parse_strategy, validation_decision, etc.
    decision: Mapped[str] = mapped_column(
        String(50)
    )  # retry, fallback, proceed, flag_for_review, etc.
    reasoning: Mapped[str | None] = mapped_column(String(2000))
    context: Mapped[dict | None] = mapped_column(JSONB)  # Additional context data
    model_version: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float | None] = mapped_column(Float)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document: Mapped[ReferenceDocument | None] = relationship(back_populates="agent_actions")

    __table_args__ = (
        Index("idx_agent_actions_document", "document_id"),
        Index("idx_agent_actions_job", "job_id"),
        Index("idx_agent_actions_type", "action_type"),
    )
