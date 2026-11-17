"""Consultas de solo lectura: indicadores del supervisor, pantalla publica y consulta del paciente."""
from __future__ import annotations

import random
from collections import Counter as Cnt

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.config import TZ
from ..models import CALLED, CANCELLED, DONE, IN_SERVICE, NO_SHOW, PREFERENCIAL, WAITING, Point, Service, Turn
from . import queueing, suggest_client, turn_service
from .errors import NotFound

UPCOMING_PER_POINT = 4  # turnos proximos que muestra la pantalla de espera


def _mins(a, b) -> float:
    return (b - a).total_seconds() / 60


def _avg(xs):
    return round(sum(xs) / len(xs), 1) if xs else None


def stats(db: Session) -> dict:
    turns = turn_service.list_turns(db, include_closed=True)
    points = db.execute(select(Point).order_by(Point.id)).scalars().all()
    waits = [_mins(t.created_at, t.called_at) for t in turns if t.called_at]
    durs = [_mins(t.started_at, t.finished_at) for t in turns if t.status == DONE and t.started_at and t.finished_at]
    hourly = Cnt(t.created_at.astimezone(TZ).hour for t in turns)

    per_point = []
    for p in points:
        pt = [t for t in turns if t.point_id == p.id]
        pd = [_mins(t.started_at, t.finished_at) for t in pt if t.status == DONE and t.started_at and t.finished_at]
        per_point.append({
            "id": p.id, "name": p.name, "active": p.active,
            "waiting": sum(t.status == WAITING for t in pt),
            "in_attention": sum(t.status in (CALLED, IN_SERVICE) for t in pt),
            "done": sum(t.status == DONE for t in pt),
            "no_show": sum(t.status == NO_SHOW for t in pt),
            "avg_service_min": _avg(pd),
        })
    per_service = [
        {"code": s.code, "name": s.name, "color": s.color,
         "total": sum(t.service_id == s.id for t in turns),
         "done": sum(t.service_id == s.id and t.status == DONE for t in turns)}
        for s in db.execute(select(Service).order_by(Service.id)).scalars().all()
    ]
    prio = [t for t in turns if t.priority_class == PREFERENCIAL or t.priority_reasons]
    prio_ids = {t.id for t in prio}
    return {
        "total": len(turns),
        "by_status": dict(Cnt(t.status for t in turns)),
        "avg_wait_min": _avg(waits),
        "avg_service_min": _avg(durs),
        "priority": {
            "total": len(prio),
            "avg_wait_min": _avg([_mins(t.created_at, t.called_at) for t in prio if t.called_at]),
            "avg_wait_normal_min": _avg([_mins(t.created_at, t.called_at) for t in turns if t.called_at and t.id not in prio_ids]),
            "reasons": dict(Cnt(r for t in prio for r in t.priority_reasons.split(",") if r)),
        },
        "reassigned": sum(t.reassign_count > 0 for t in turns),
        "no_shows_total": sum(t.no_show_count > 0 for t in turns),
        "per_point": per_point,
        "per_service": per_service,
        "hourly": [{"hour": h, "count": hourly.get(h, 0)} for h in range(6, 21)],
    }


def display(db: Session) -> dict:
    """Datos de la pantalla de espera: llamados vigentes y proximos turnos por punto (solo codigos)."""
    day = queueing.today()
    calling = db.execute(
        select(Turn).where(Turn.day == day, Turn.status.in_([CALLED, IN_SERVICE])).order_by(Turn.called_at.desc())
    ).scalars().all()
    points = db.execute(select(Point).order_by(Point.id)).scalars().all()
    rows = []
    for p in points:
        queue = queueing.waiting_turns(db, p.id)
        rows.append({
            "point": p,
            "waiting": len(queue),
            "upcoming": queue[:UPCOMING_PER_POINT],
        })
    return {"calling": calling, "points": rows}


def lookup(db: Session, q: str) -> tuple[Turn, dict | None]:
    q = q.strip()
    t = db.execute(
        select(Turn).where(Turn.day == queueing.today(), or_(Turn.code == q.upper(), Turn.doc_number == q))
        .order_by(Turn.id.desc())
    ).scalars().first()
    if not t:
        raise NotFound("No encontramos un turno de hoy con ese dato")
    est = suggest_client.estimate_point(db, t.point).get(t.id) if t.status == WAITING else None
    return t, est


NAMES = ["Maria Lopez", "Juan Perez", "Ana Torres", "Carlos Diaz", "Lucia Fernandez", "Pedro Gomez", "Sofia Ramirez",
         "Jorge Castillo", "Valentina Ruiz", "Miguel Herrera", "Isabel Moreno", "Andres Vargas", "Rosa Mendoza",
         "Camilo Ortiz", "Elena Rojas", "Tomas Navarro", "Paula Medina", "Ricardo Suarez"]


def simulate(db: Session, count: int, username: str) -> int:
    from .errors import DomainError

    services = db.execute(select(Service)).scalars().all()
    created = 0
    for _ in range(count):
        age = random.choice([random.randint(3, 17), random.randint(18, 59), random.randint(18, 59), random.randint(60, 88)])
        data = {
            "doc_number": str(random.randint(10_000_000, 1_099_999_999)),
            "patient_name": random.choice(NAMES),
            "age": age,
            "pregnant": 10 <= age <= 55 and random.random() < 0.08,
            "disability": random.random() < 0.07,
            "service_code": random.choices(services, weights=[5, 3, 3, 2])[0].code,
        }
        try:
            turn_service.create_turn(db, data, username)
            created += 1
        except DomainError:
            db.rollback()
    return created
