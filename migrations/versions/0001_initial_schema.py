"""
Initial schema migration for DOCINTEL.
Creates all core tables for the knowledge base.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# Revision identifiers
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""
    
    # -------------------------------------------------------------------------
    # reference_documents
    # -------------------------------------------------------------------------
    op.create_table(
        "reference_documents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_number", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("contract_number", sa.String(100), nullable=True),
        sa.Column("discipline", sa.String(10), nullable=True),
        sa.Column("drawing_type", sa.String(10), nullable=True),
        sa.Column("area_code", sa.String(10), nullable=True),
        sa.Column("current_revision", sa.String(10), nullable=True),
        sa.Column("issue_status", sa.String(20), nullable=True),
        sa.Column("is_reference", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("sheet_count", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_reference_documents_document_number", "reference_documents", ["document_number"])
    op.create_index("ix_reference_documents_contract_number", "reference_documents", ["contract_number"])
    op.create_index("ix_reference_documents_discipline", "reference_documents", ["discipline"])
    op.create_index("ix_reference_documents_is_reference", "reference_documents", ["is_reference"])
    op.create_unique_constraint("uq_doc_revision", "reference_documents", ["document_number", "current_revision"])
    
    # -------------------------------------------------------------------------
    # document_revisions
    # -------------------------------------------------------------------------
    op.create_table(
        "document_revisions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, nullable=False),
        sa.Column("revision", sa.String(10), nullable=False),
        sa.Column("issue_code", sa.String(10), nullable=True),
        sa.Column("revision_date", sa.Date, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("prepared_by", sa.String(100), nullable=True),
        sa.Column("checked_by", sa.String(100), nullable=True),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["document_id"], ["reference_documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_document_revisions_document_id", "document_revisions", ["document_id"])
    
    # -------------------------------------------------------------------------
    # structured_records
    # -------------------------------------------------------------------------
    op.create_table(
        "structured_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, nullable=False),
        sa.Column("document_number", sa.String(50), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("revision", sa.String(10), nullable=True),
        sa.Column("contract_number", sa.String(100), nullable=True),
        sa.Column("issue_status", sa.String(20), nullable=True),
        sa.Column("client", sa.String(200), nullable=True),
        sa.Column("project_title", sa.Text, nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("drawing_type", sa.String(10), nullable=True),
        sa.Column("discipline", sa.String(10), nullable=True),
        sa.Column("page", sa.String(50), nullable=True),
        sa.Column("sheet_count", sa.Integer, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("extraction_method", sa.String(50), nullable=True),
        sa.Column("source_layer", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["document_id"], ["reference_documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_structured_records_document_id", "structured_records", ["document_id"])
    op.create_index("ix_structured_records_document_number", "structured_records", ["document_number"])
    op.create_index("ix_structured_records_confidence", "structured_records", ["confidence"])
    
    # -------------------------------------------------------------------------
    # comment_responses
    # -------------------------------------------------------------------------
    op.create_table(
        "comment_responses",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("record_id", sa.Integer, nullable=False),
        sa.Column("comment_ref", sa.String(50), nullable=True),
        sa.Column("comment_text", sa.Text, nullable=True),
        sa.Column("response_text", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["record_id"], ["structured_records.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_comment_responses_record_id", "comment_responses", ["record_id"])
    
    # -------------------------------------------------------------------------
    # legend_entries
    # -------------------------------------------------------------------------
    op.create_table(
        "legend_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("record_id", sa.Integer, nullable=False),
        sa.Column("symbol", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["record_id"], ["structured_records.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_legend_entries_record_id", "legend_entries", ["record_id"])
    
    # -------------------------------------------------------------------------
    # drawing_index_entries
    # -------------------------------------------------------------------------
    op.create_table(
        "drawing_index_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("record_id", sa.Integer, nullable=False),
        sa.Column("drawing_number", sa.String(50), nullable=True),
        sa.Column("drawing_title", sa.String(500), nullable=True),
        sa.Column("revision", sa.String(10), nullable=True),
        sa.Column("sheet_count", sa.Integer, nullable=True),
        sa.ForeignKeyConstraint(["record_id"], ["structured_records.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_drawing_index_entries_record_id", "drawing_index_entries", ["record_id"])
    op.create_index("ix_drawing_index_entries_drawing_number", "drawing_index_entries", ["drawing_number"])
    
    # -------------------------------------------------------------------------
    # equipment_ratings
    # -------------------------------------------------------------------------
    op.create_table(
        "equipment_ratings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("record_id", sa.Integer, nullable=False),
        sa.Column("equipment_tag", sa.String(100), nullable=True),
        sa.Column("parameter", sa.String(200), nullable=True),
        sa.Column("value", sa.String(100), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["record_id"], ["structured_records.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_equipment_ratings_record_id", "equipment_ratings", ["record_id"])
    op.create_index("ix_equipment_ratings_equipment_tag", "equipment_ratings", ["equipment_tag"])
    
    # -------------------------------------------------------------------------
    # validation_rules
    # -------------------------------------------------------------------------
    op.create_table(
        "validation_rules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("rule_key", sa.String(100), nullable=False, unique=True),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("definition", JSONB, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_validation_rules_rule_key", "validation_rules", ["rule_key"])
    op.create_index("ix_validation_rules_rule_type", "validation_rules", ["rule_type"])
    op.create_index("ix_validation_rules_active", "validation_rules", ["active"])
    
    # -------------------------------------------------------------------------
    # submission_logs
    # -------------------------------------------------------------------------
    op.create_table(
        "submission_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, nullable=True),
        sa.Column("discipline", sa.String(10), nullable=True),
        sa.Column("submitter", sa.String(100), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("violations", JSONB, nullable=True),
        sa.Column("docon_reference", sa.String(200), nullable=True),
        sa.Column("submitted_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["document_id"], ["reference_documents.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_submission_logs_document_id", "submission_logs", ["document_id"])
    op.create_index("ix_submission_logs_discipline", "submission_logs", ["discipline"])
    op.create_index("ix_submission_logs_outcome", "submission_logs", ["outcome"])
    op.create_index("ix_submission_logs_submitted_at", "submission_logs", ["submitted_at"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("submission_logs")
    op.drop_table("validation_rules")
    op.drop_table("equipment_ratings")
    op.drop_table("drawing_index_entries")
    op.drop_table("legend_entries")
    op.drop_table("comment_responses")
    op.drop_table("structured_records")
    op.drop_table("document_revisions")
    op.drop_table("reference_documents")