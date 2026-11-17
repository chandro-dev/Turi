"""turns.bonus_min (prioridad otorgada por el modelo) y points.enabled (abierto/cerrado por supervision).

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE turns ADD COLUMN IF NOT EXISTS bonus_min DOUBLE PRECISION")
    op.execute("ALTER TABLE points ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE")


def downgrade() -> None:
    op.execute("ALTER TABLE points DROP COLUMN IF EXISTS enabled")
    op.execute("ALTER TABLE turns DROP COLUMN IF EXISTS bonus_min")
