"""
Seed baseline validation rules derived from reference documents.
Inserts initial rules for document number format, title block fields, etc.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# Revision identifiers
revision: str = "0003_seed_validation_rules"
down_revision: Union[str, None] = "0002_enable_pgvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert baseline validation rules."""
    
    # Document number format rule
    op.execute("""
        INSERT INTO validation_rules (rule_key, rule_type, definition, active)
        VALUES (
            'document_number_format',
            'regex',
            '{"pattern": "^[A-Z]{3}-[A-Z]-[A-Z]{2}-\\d{2}-\\d{3}$", "description": "Project code (3) - Discipline (1) - Drawing type (2) - Area (2) - Sequence (3)", "field": "document_number", "severity": "error"}'::jsonb,
            true
        )
    """)
    
    # Contract number rule
    op.execute("""
        INSERT INTO validation_rules (rule_key, rule_type, definition, active)
        VALUES (
            'contract_number_match',
            'equality',
            '{"expected_value": "3500003752", "field": "contract_number", "description": "Contract number must match project contract", "severity": "error"}'::jsonb,
            true
        )
    """)
    
    # Required title block fields
    op.execute("""
        INSERT INTO validation_rules (rule_key, rule_type, definition, active)
        VALUES (
            'title_block_required_fields',
            'required_fields',
            '{"fields": ["DOCUMENT NO.", "CONTRACTOR DOC NO.", "REV.", "CONTRACT NO.", "PAGE", "CLIENT", "PROJECT TITLE", "DOC. TITLE"], "description": "All title block fields must be present", "severity": "error"}'::jsonb,
            true
        )
    """)
    
    # Revision ladder validation
    op.execute("""
        INSERT INTO validation_rules (rule_key, rule_type, definition, active)
        VALUES (
            'revision_ladder',
            'enum',
            '{"allowed_values": ["A", "B", "0", "1", "ASB", "IFI"], "field": "revision", "description": "Revision must follow the approved ladder", "severity": "error"}'::jsonb,
            true
        )
    """)
    
    # Issue status codes
    op.execute("""
        INSERT INTO validation_rules (rule_key, rule_type, definition, active)
        VALUES (
            'issue_status_codes',
            'enum',
            '{"allowed_values": ["IFR", "IFA", "IFC", "ASB", "IFI", "Re-IFC"], "field": "issue_status", "description": "Issue status must be a recognized code", "severity": "warning"}'::jsonb,
            true
        )
    """)
    
    # Mandatory administrative sheets
    op.execute("""
        INSERT INTO validation_rules (rule_key, rule_type, definition, active)
        VALUES (
            'mandatory_administrative_sheets',
            'required_sheets',
            '{"sheets": ["COMMENTS RESPONSE SHEET", "RECORD OF REVISION"], "description": "Document must include mandatory administrative sheets", "severity": "error"}'::jsonb,
            true
        )
    """)
    
    # Confidence threshold
    op.execute("""
        INSERT INTO validation_rules (rule_key, rule_type, definition, active)
        VALUES (
            'extraction_confidence',
            'threshold',
            '{"min_confidence": 0.6, "field": "confidence", "description": "Extraction confidence must meet minimum threshold", "severity": "warning"}'::jsonb,
            true
        )
    """)
    
    # Discipline code validation
    op.execute("""
        INSERT INTO validation_rules (rule_key, rule_type, definition, active)
        VALUES (
            'discipline_code',
            'enum',
            '{"allowed_values": ["E", "M", "I", "S", "C", "P", "ST"], "field": "discipline", "description": "Discipline must be a recognized code", "severity": "error"}'::jsonb,
            true
        )
    """)


def downgrade() -> None:
    """Remove seeded validation rules."""
    op.execute("DELETE FROM validation_rules WHERE rule_key IN (
        'document_number_format',
        'contract_number_match',
        'title_block_required_fields',
        'revision_ladder',
        'issue_status_codes',
        'mandatory_administrative_sheets',
        'extraction_confidence',
        'discipline_code'
    )")