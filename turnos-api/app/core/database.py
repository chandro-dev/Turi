import time
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db


def run_migrations(retries: int = 30) -> None:
    """Aplica las migraciones de Alembic (upgrade head). Reintenta mientras la base arranca."""
    from alembic import command
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parent.parent / "migrations"))
    for i in range(retries):
        try:
            command.upgrade(cfg, "head")
            return
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1)
