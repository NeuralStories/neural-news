"""invalidación de prompts por hash de guion

Revision ID: b3c1d9e4f7a2
Revises: d4ce8c95781e
Create Date: 2026-11-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'b3c1d9e4f7a2'
down_revision = 'd4ce8c95781e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('prompt_packages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_script_hash', sa.String(length=64), nullable=True))
    with op.batch_alter_table('generated_takes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('needs_review', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table('generated_takes', schema=None) as batch_op:
        batch_op.drop_column('needs_review')
    with op.batch_alter_table('prompt_packages', schema=None) as batch_op:
        batch_op.drop_column('source_script_hash')
