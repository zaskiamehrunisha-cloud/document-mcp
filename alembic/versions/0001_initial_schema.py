"""Initial schema migration - create all 11 tables with pgvector extension and IVFFlat index."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables, pgvector extension, and IVFFlat index."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create reference_documents table
    op.create_table(
        "reference_documents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_number", sa.String(50), index=True),
        sa.Column("title", sa.String(500)),
        sa.Column("revision", sa.String(20)),
        sa.Column("issue_status", sa.String(10)),
        sa.Column("contract_number", sa.String(100)),
        sa.Column("discipline", sa.String(10), index=True),
        sa.Column("page_count", sa.Integer),
        sa.Column("file_hash", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("original_path", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Checking", index=True),
        sa.Column("job_id", sa.String(100), index=True),
        sa.Column("model_version", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    
    # Create revision_history table
    op.create_table(
        "revision_history",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("reference_documents.id"), nullable=False),
        sa.Column("rev", sa.String(20)),
        sa.Column("date", sa.String(50)),
        sa.Column("description", sa.String(1000)),
        sa.Column("prepared_by", sa.String(200)),
        sa.Column("checked_by", sa.String(200)),
        sa.Column("approved_by", sa.String(200)),
    )
    
    # Create comments_response table
    op.create_table(
        "comments_response",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("reference_documents.id"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("client_comment", sa.String(2000)),
        sa.Column("contractor_response", sa.String(2000)),
        sa.UniqueConstraint("document_id", "seq", name="uq_comments_document_seq"),
    )
    
    # Create legend_symbols table
    op.create_table(
        "legend_symbols",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("reference_documents.id"), nullable=True),
        sa.Column("symbol", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("discipline", sa.String(10)),
    )
    
    # Create equipment_ratings table
    op.create_table(
        "equipment_ratings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("reference_documents.id"), nullable=False),
        sa.Column("tag", sa.String(100)),
        sa.Column("rating", sa.String(200)),
        sa.Column("voltage", sa.String(50)),
        sa.Column("phase", sa.String(50)),
        sa.Column("frequency", sa.String(50)),
        sa.Column("power", sa.String(100)),
        sa.Column("sheet", sa.String(50)),
    )
    
    # Create drawing_index table
    op.create_table(
        "drawing_index",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("reference_documents.id"), nullable=False),
        sa.Column("sheet_no", sa.String(20)),
        sa.Column("sheet_title", sa.String(500)),
        sa.Column("drawing_number", sa.String(50)),
    )
    
    # Create validation_rules table
    op.create_table(
        "validation_rules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False),
        sa.Column("rule_type", sa.String(20), nullable=False),
        sa.Column("discipline", sa.String(10), nullable=True),
        sa.Column("definition", postgresql.JSONB, nullable=False),
        sa.Column("active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    
    # Create discipline_submissions table
    op.create_table(
        "discipline_submissions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("reference_documents.id"), nullable=False),
        sa.Column("discipline", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("docon_confirmation_ref", sa.String(200)),
        sa.Column("rejection_note", postgresql.JSONB, nullable=True),
        sa.Column("model_version", sa.String(100)),
        sa.Column("submitted_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    
    # Create low_confidence_regions table
    op.create_table(
        "low_confidence_regions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("reference_documents.id"), nullable=False),
        sa.Column("page", sa.Integer, nullable=False),
        sa.Column("bbox", postgresql.JSONB, nullable=False),
        sa.Column("text", sa.String(2000)),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("reviewed", sa.Boolean, server_default="false", nullable=False),
        sa.Column("reviewed_by", sa.String(100)),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_lowconf_document_page", "low_confidence_regions", ["document_id", "page"])
    
    # Create document_chunks table with pgvector embedding column
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("reference_documents.id"), nullable=False, index=True),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("content", sa.String(10000), nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("embedding", sa.String),  # vector(384) type handled by pgvector
        sa.Column("tsv", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    
    # Create IVFFlat index on embedding column for cosine similarity search
    op.execute("""
        CREATE INDEX idx_document_chunks_embedding 
        ON document_chunks 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)
    """)
    
    # Create GIN index on tsv column for full-text search
    op.execute("""
        CREATE INDEX idx_document_chunks_tsv 
        ON document_chunks 
        USING gin (tsv)
    """)
    
    # Create qa_query_log table
    op.create_table(
        "qa_query_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("query_text", sa.String(2000), nullable=False),
        sa.Column("answer", sa.String(5000), nullable=False),
        sa.Column("confidence_level", sa.String(20), nullable=False),
        sa.Column("cited_document_ids", postgresql.JSONB, nullable=False),
        sa.Column("retrieved_chunk_ids", postgresql.JSONB, nullable=False),
        sa.Column("model_version", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    
    # Create trigger function to update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    # Create triggers for tables with updated_at
    op.execute("""
        CREATE TRIGGER update_reference_documents_updated_at 
        BEFORE UPDATE ON reference_documents 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    
    op.execute("""
        CREATE TRIGGER update_validation_rules_updated_at 
        BEFORE UPDATE ON validation_rules 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Drop all tables and extension."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_validation_rules_updated_at ON validation_rules")
    op.execute("DROP TRIGGER IF EXISTS update_reference_documents_updated_at ON reference_documents")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("qa_query_log")
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_tsv")
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_embedding")
    op.drop_table("document_chunks")
    op.drop_table("low_confidence_regions")
    op.drop_table("discipline_submissions")
    op.drop_table("validation_rules")
    op.drop_table("drawing_index")
    op.drop_table("equipment_ratings")
    op.drop_table("legend_symbols")
    op.drop_table("comments_response")
    op.drop_table("revision_history")
    op.drop_table("reference_documents")
    
    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")