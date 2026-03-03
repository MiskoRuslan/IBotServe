"""add_slang_and_typos_to_style_settings

Revision ID: 5ee54345a58a
Revises: 33edd7811e71
Create Date: 2026-03-03 20:34:20.238937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ee54345a58a'
down_revision: Union[str, Sequence[str], None] = '33edd7811e71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new slang and typos fields to existing style_settings."""
    # Update all existing userbots to include new fields in style_settings
    op.execute("""
        UPDATE userbots
        SET style_settings = style_settings ||
            '{"use_youth_slang": false, "use_illiterate_slang": false, "use_typos": false}'::jsonb
        WHERE NOT (style_settings ? 'use_youth_slang')
    """)


def downgrade() -> None:
    """Remove slang and typos fields from style_settings."""
    # Remove the new fields from style_settings
    op.execute("""
        UPDATE userbots
        SET style_settings = style_settings - 'use_youth_slang' - 'use_illiterate_slang' - 'use_typos'
    """)
