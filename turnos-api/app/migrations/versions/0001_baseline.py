"""Esquema base (tablas originales).

Las bases creadas antes de usar Alembic ya tienen estas tablas: create_all es idempotente (checkfirst),
por lo que esta revision es segura tanto en bases nuevas como en existentes.
Las migraciones posteriores agregan columnas con IF NOT EXISTS por la misma razon.

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    pass
