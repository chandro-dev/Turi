"""Fila: orden, numeracion de turnos, bitacora y consultas de estado por punto."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..core.config import PRIORITY_BASE_BONUS_MIN, TZ
from ..models import BAJA, CALLED, IN_SERVICE, NORMAL, PREFERENCIAL, WAITING, Counter, Service, Turn, TurnEvent

# Ventaja (minutos de espera "virtual") por clase de prioridad.
# Preferencial se adelanta hasta 20 min a un turno normal; BAJA (no se presento) cede 15 min.
BONUS_MIN = {PREFERENCIAL: PRIORITY_BASE_BONUS_MIN, NORMAL: 0, BAJA: -15}


def now() -> datetime:
    return datetime.now(timezone.utc)


def today() -> date:
    return datetime.now(TZ).date()


def key_for(priority_class: str, queued_at: datetime, bonus_min: float | None = None) -> float:
    """Clave de orden: menor = se atiende antes. `bonus_min` (otorgado por el modelo) reemplaza al valor por defecto."""
    bonus = BONUS_MIN[priority_class] if bonus_min is None else bonus_min
    return queued_at.timestamp() - bonus * 60


def turn_key(t: Turn) -> float:
    return key_for(t.priority_class, t.queued_at, t.bonus_min if t.priority_class == PREFERENCIAL else None)


def next_code(db: Session, service: Service) -> tuple[str, date]:
    day = today()
    db.execute(pg_insert(Counter).values(service_id=service.id, day=day, last=0).on_conflict_do_nothing())
    c = db.execute(
        select(Counter).where(Counter.service_id == service.id, Counter.day == day).with_for_update()
    ).scalar_one()
    c.last += 1
    return f"{service.code}-{c.last:03d}", day


def add_event(db: Session, turn: Turn, type_: str, detail: str = "", username: str | None = None) -> None:
    db.add(TurnEvent(turn_id=turn.id, type=type_, detail=detail, username=username))


def waiting_turns(db: Session, point_id: int) -> list[Turn]:
    rows = db.execute(
        select(Turn).where(Turn.point_id == point_id, Turn.status == WAITING, Turn.day == today())
    ).scalars().all()
    return sorted(rows, key=turn_key)


def current_turn(db: Session, point_id: int) -> Turn | None:
    return db.execute(
        select(Turn)
        .where(Turn.point_id == point_id, Turn.status.in_([CALLED, IN_SERVICE]), Turn.day == today())
        .order_by(Turn.called_at.desc())
    ).scalars().first()
