"""Add agent_actions table for orchestrator audit logging."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_agent_actions_table"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent_actions table for orchestrator decision logging."""
    op.create_table(
        "agent_actions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("reference_documents.id"), nullable=True),
        sa.Column("job_id", sa.String(100), index=True),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("reasoning", sa.String(2000), nullable=True),
        sa.Column("context", postgresql.JSONB, nullable=True),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("success", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes
    op.create_index("idx_agent_actions_document", "agent_actions", ["document_id"])
    op.create_index("idx_agent_actions_job", "agent_actions", ["job_id"])
    op.create_index("idx_agent_actions_type", "agent_actions", ["action_type"])


def downgrade() -> None:
    """Drop agent_actions table."""
    op.drop_index("idx_agent_actions_type", table_name="agent_actions")
    op.drop_index("idx_agent_actions_job", table_name="agent_actions")
    op.drop_index("idx_agent_actions_document", table_name="agent_actions")
    op.drop_table("agent_actions")