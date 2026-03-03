"""add_language_to_style_settings

Revision ID: 6a2259fc3a14
Revises: 5ee54345a58a
Create Date: 2026-03-03 20:41:37.825472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a2259fc3a14'
down_revision: Union[str, Sequence[str], None] = '5ee54345a58a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add language field to existing style_settings."""
    # Update all existing userbots to include language field (default: ukrainian)
    op.execute("""
        UPDATE userbots
        SET style_settings = style_settings || '{"language": "ukrainian"}'::jsonb
        WHERE NOT (style_settings ? 'language')
    """)


def downgrade() -> None:
    """Remove language field from style_settings."""
    # Remove the language field from style_settings
    op.execute("""
        UPDATE userbots
        SET style_settings = style_settings - 'language'
    """)
