from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Estados del turno
WAITING = "WAITING"
CALLED = "CALLED"
IN_SERVICE = "IN_SERVICE"
DONE = "DONE"
CANCELLED = "CANCELLED"
NO_SHOW = "NO_SHOW"
ACTIVE_STATUSES = (WAITING, CALLED, IN_SERVICE, NO_SHOW)

# Clases de prioridad
PREFERENCIAL = "PREFERENCIAL"
NORMAL = "NORMAL"
BAJA = "BAJA"  # reincorporado tras no presentarse

point_services = Table(
    "point_services",
    Base.metadata,
    Column("point_id", ForeignKey("points.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    prior_minutes: Mapped[float] = mapped_column(Float, default=10.0)
    color: Mapped[str] = mapped_column(String(9), default="#0f766e")


class Point(Base):
    __tablename__ = "points"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    services: Mapped[list[Service]] = relationship(secondary=point_services, lazy="selectin")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))  # RECEPCION | MEDICO | SUPERVISOR
    password_hash: Mapped[str] = mapped_column(String(200))
    point_id: Mapped[int | None] = mapped_column(ForeignKey("points.id"), nullable=True)
    point: Mapped[Point | None] = relationship(lazy="joined")


class Counter(Base):
    __tablename__ = "counters"
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    last: Mapped[int] = mapped_column(Integer, default=0)


class Turn(Base):
    __tablename__ = "turns"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16))
    day: Mapped[date] = mapped_column(Date)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    point_id: Mapped[int] = mapped_column(ForeignKey("points.id"))
    doc_number: Mapped[str] = mapped_column(String(30))
    patient_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    age: Mapped[int] = mapped_column(Integer)
    pregnant: Mapped[bool] = mapped_column(Boolean, default=False)
    disability: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_class: Mapped[str] = mapped_column(String(14), default=NORMAL)
    priority_reasons: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(12), default=WAITING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    no_show_count: Mapped[int] = mapped_column(Integer, default=0)
    reassign_count: Mapped[int] = mapped_column(Integer, default=0)
    initial_wait_est: Mapped[float | None] = mapped_column(Float, nullable=True)
    bonus_min: Mapped[float | None] = mapped_column(Float, nullable=True)  # prioridad otorgada por el modelo (min de adelanto)
    created_by: Mapped[str | None] = mapped_column(String(40), nullable=True)

    service: Mapped[Service] = relationship(lazy="joined")
    point: Mapped[Point] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_turns_day_code", "day", "code", unique=True),
        Index("ix_turns_point_status", "point_id", "status"),
        Index("ix_turns_doc", "doc_number"),
    )


class TurnEvent(Base):
    """Bitacora de auditoria de cada turno."""

    __tablename__ = "turn_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    turn_id: Mapped[int] = mapped_column(ForeignKey("turns.id", ondelete="CASCADE"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    type: Mapped[str] = mapped_column(String(24))
    detail: Mapped[str] = mapped_column(Text, default="")
    username: Mapped[str | None] = mapped_column(String(40), nullable=True)
