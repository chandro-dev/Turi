from sqlalchemy import Column, Float, Integer, String, UniqueConstraint

from ..core.database import Base


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
