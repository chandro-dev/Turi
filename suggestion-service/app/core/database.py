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


def init_db(retries: int = 30) -> None:
    from ..models import entities  # noqa: F401  (registra las tablas)

    for i in range(retries):
        try:
            Base.metadata.create_all(engine)
            return
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1)
