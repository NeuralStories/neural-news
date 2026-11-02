"""secretos de proveedor cifrados (bóveda)

Revision ID: d5e3f9a2b7c1
Revises: c4d2e8f1a5b6
Create Date: 2026-11-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'd5e3f9a2b7c1'
down_revision = 'c4d2e8f1a5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'provider_secrets',
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('ciphertext', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('provider'),
    )


def downgrade() -> None:
    op.drop_table('provider_secrets')
