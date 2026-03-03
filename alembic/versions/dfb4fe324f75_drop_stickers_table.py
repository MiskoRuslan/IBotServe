"""drop stickers table

Revision ID: dfb4fe324f75
Revises: de15513a28e0
Create Date: 2026-03-03 22:23:57.737602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'dfb4fe324f75'
down_revision: Union[str, Sequence[str], None] = 'de15513a28e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop stickers table (moving to file-based storage)."""
    op.drop_table('stickers')


def downgrade() -> None:
    """Recreate stickers table for rollback."""
    op.create_table('stickers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('userbot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_id', sa.String(), nullable=False),
        sa.Column('emotion', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['userbot_id'], ['userbots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
