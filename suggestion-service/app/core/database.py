import os
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")

_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy.pool import StaticPool

    _kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, **_kwargs)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        yield db


def _ensure_columns() -> None:
    """Migracion minima de columnas nuevas en tablas existentes (solo Postgres; en pruebas la base es nueva)."""
    if engine.dialect.name != "postgresql":
        return
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE training_log ADD COLUMN IF NOT EXISTS pred_ema DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE training_log ADD COLUMN IF NOT EXISTS pred_sk DOUBLE PRECISION"))


def init_db(retries: int = 30) -> None:
    from ..models import entities  # noqa: F401  (registra las tablas)

    for i in range(retries):
        try:
            Base.metadata.create_all(engine)
            _ensure_columns()
            return
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1)
