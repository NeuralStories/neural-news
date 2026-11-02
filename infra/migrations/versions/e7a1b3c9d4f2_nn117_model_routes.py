"""rutas de modelo por tarea + instantánea en el trabajo

Port de `model_routes` (migración `c0f68f32807d` del hermano congelado,
`archive/neuralnews-20261101`).

Una ruta es la combinación (tarea, proveedor, modelo, prioridad). El trabajo
**resuelve** la ruta al encolarse y guarda una **instantánea**: cambiar las
rutas después no altera un trabajo que ya está en marcha.

Además, el trabajo guarda la instantánea en una columna propia
(`jobs.model_snapshot`), no dentro del payload: el payload es la entrada del
trabajo y mezclarla con la configuración la haría ilegible.

Revision ID: e7a1b3c9d4f2
Revises: d5e3f9a2b7c1
Create Date: 2026-11-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'e7a1b3c9d4f2'
down_revision = 'd5e3f9a2b7c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'model_routes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('model', sa.String(length=128), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True),
        sa.Column('config_revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task', 'provider', name='uq_model_routes_task_provider'),
    )
    op.create_index('ix_model_routes_task', 'model_routes', ['task'])
    op.add_column('jobs', sa.Column('model_snapshot', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'model_snapshot')
    op.drop_index('ix_model_routes_task', table_name='model_routes')
    op.drop_table('model_routes')
