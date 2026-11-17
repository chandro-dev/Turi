"""Disponibilidad de puntos y turnos de trabajo (horarios del personal). Logica pura + una consulta.

Estados de un punto:
  closed     cerrado por el supervisor (enabled = False)
  off_hours  tiene turnos de trabajo definidos pero ninguno cubre la hora actual
  paused     el personal lo puso en pausa
  open       disponible para recibir y atender pacientes
Un punto SIN turnos definidos se comporta como siempre abierto (compatible con los puntos de demostracion).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import TZ
from ..models import Point, Shift, User

WEEKDAY_NAMES = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]


def local_now() -> datetime:
    return datetime.now(TZ)


def load_shifts(db: Session) -> list[Shift]:
    return list(db.execute(select(Shift).order_by(Shift.point_id, Shift.start_time)).scalars().all())


def covers(sh: Shift, now: datetime) -> bool:
    t = now.time().replace(second=0, microsecond=0)
    return now.weekday() in sh.days and sh.start_time <= t < sh.end_time


def point_status(p: Point, shifts: list[Shift], now: datetime | None = None) -> str:
    now = now or local_now()
    if not p.enabled:
        return "closed"
    own = [s for s in shifts if s.point_id == p.id]
    if own and not any(covers(s, now) for s in own):
        return "off_hours"
    if not p.active:
        return "paused"
    return "open"


def is_available(p: Point, shifts: list[Shift], now: datetime | None = None) -> bool:
    return point_status(p, shifts, now) == "open"


def user_point(db: Session, user: User, shifts: list[Shift] | None = None, now: datetime | None = None) -> Point | None:
    """Punto que el funcionario atiende AHORA: el de su turno vigente; sin turnos definidos, el punto fijo asignado."""
    shifts = load_shifts(db) if shifts is None else shifts
    now = now or local_now()
    mine = [s for s in shifts if s.user_id == user.id]
    if mine:
        cur = next((s for s in mine if covers(s, now)), None)
        return cur.point if cur else None
    return user.point


def next_shift(user: User, shifts: list[Shift], now: datetime | None = None) -> dict | None:
    """Proximo turno de trabajo del funcionario (dentro de los siguientes 7 dias)."""
    now = now or local_now()
    mine = [s for s in shifts if s.user_id == user.id]
    best = None
    for add in range(8):
        day = now + timedelta(days=add)
        for s in mine:
            if day.weekday() not in s.days:
                continue
            start = day.replace(hour=s.start_time.hour, minute=s.start_time.minute, second=0, microsecond=0)
            if start > now and (best is None or start < best[0]):
                best = (start, s)
    if not best:
        return None
    start, s = best
    return {"weekday": WEEKDAY_NAMES[start.weekday()], "date": start.date().isoformat(), "start": s.start_time.strftime("%H:%M"),
            "end": s.end_time.strftime("%H:%M"), "point": s.point.name}


def overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end
