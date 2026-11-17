from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint

from ..core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


class TrainingLog(Base):
    """Una fila por atencion aprendida: lo que el modelo predijo ANTES de ver el dato real.

    Permite medir la efectividad (error de prediccion) y dibujar la curva de aprendizaje.
    prior / prior_error son la linea base: el valor inicial del servicio sin aprender.
    """

    __tablename__ = "training_log"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime(timezone=True), default=_now, nullable=False)
    service = Column(String(32), nullable=False, index=True)
    point_id = Column(String(32), nullable=False)
    grp = Column(String(16), nullable=False)
    predicted = Column(Float, nullable=False)
    actual = Column(Float, nullable=False)
    prior = Column(Float, nullable=True)
    abs_error = Column(Float, nullable=False)
    prior_error = Column(Float, nullable=True)
    n_before = Column(Integer, nullable=False, default=0)
