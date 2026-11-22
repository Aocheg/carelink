"""Add SHA-256 audit hash chaining for NDPA 2023 statutory compliance

Revision ID: a1b2c3d4e5f6
Revises: f3f9a776b0c5
Create Date: 2026-11-22 10:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3f9a776b0c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add cryptographic hash chaining columns."""
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'previous_hash',
                sa.String(length=64),
                nullable=False,
                server_default='0000000000000000000000000000000000000000000000000000000000000000'
            )
        )
        batch_op.add_column(
            sa.Column(
                'current_hash',
                sa.String(length=64),
                nullable=False,
                server_default='0000000000000000000000000000000000000000000000000000000000000000'
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_column('current_hash')
        batch_op.drop_column('previous_hash')
