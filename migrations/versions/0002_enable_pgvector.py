"""
Enable pgvector extension and add vector column with HNSW index.
This migration must run after the initial schema is created.
"""

from typing import Sequence, Union

from alembic import op


# Revision identifiers
revision: str = "0002_enable_pgvector"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pgvector and add embedding column with HNSW index."""
    
    # Enable the pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Add the embedding column to document_chunks
    # Dimension 1024 matches BAAI/bge-large-en-v1.5
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(1024)"
    )
    
    # Create HNSW index for cosine similarity search
    # HNSW is the 2026 default: higher recall, lower latency than IVFFlat
    # m=16 is a good balance between index size and search quality
    # ef_construction=64 provides good recall during index build
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    # Add chunk_metadata column for flexible metadata storage
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS chunk_metadata JSONB"
    )


def downgrade() -> None:
    """Remove pgvector extension and related objects."""
    
    # Drop the HNSW index
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    
    # Drop the embedding column
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS chunk_metadata")
    
    # Note: We don't drop the vector extension itself as other objects might depend on it
    # op.execute("DROP EXTENSION IF EXISTS vector")