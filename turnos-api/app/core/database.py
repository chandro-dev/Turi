import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db


def _ensure_columns() -> None:
    """Migracion minima: agrega columnas nuevas a tablas ya existentes (Postgres)."""
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE turns ADD COLUMN IF NOT EXISTS bonus_min DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE points ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE"))


def init_db(base, retries: int = 30) -> None:
    for i in range(retries):
        try:
            base.metadata.create_all(engine)
            _ensure_columns()
            return
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1)
