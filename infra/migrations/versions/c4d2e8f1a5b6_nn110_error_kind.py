"""motivo normalizado del fallo de un trabajo

Revision ID: c4d2e8f1a5b6
Revises: b3c1d9e4f7a2
Create Date: 2026-11-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'c4d2e8f1a5b6'
down_revision = 'b3c1d9e4f7a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('error_kind', sa.String(length=24), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('error_kind')
