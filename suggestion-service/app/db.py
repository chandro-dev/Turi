import os
import time

from sqlalchemy import Column, Float, Integer, String, UniqueConstraint, create_engine
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


class Stat(Base):
    """Media online de duracion (minutos) por servicio / punto / grupo.

    point_id y grp valen '*' para las agregaciones generales.
    """

    __tablename__ = "stats"
    id = Column(Integer, primary_key=True)
    service = Column(String(32), nullable=False)
    point_id = Column(String(32), nullable=False, default="*")
    grp = Column(String(16), nullable=False, default="*")  # normal | pref | *
    n = Column(Integer, nullable=False, default=0)
    mean = Column(Float, nullable=False, default=0.0)
    __table_args__ = (UniqueConstraint("service", "point_id", "grp", name="uq_stat"),)


def init_db(retries: int = 30) -> None:
    for i in range(retries):
        try:
            Base.metadata.create_all(engine)
            return
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1)
