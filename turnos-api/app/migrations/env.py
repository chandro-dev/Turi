"""Entorno de Alembic: usa el mismo motor de la aplicacion."""
from alembic import context

from app.core.database import engine
from app.models import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
