"""Administracion de recursos (supervisor): puntos de atencion, personal y turnos de trabajo."""
from __future__ import annotations

import re
from collections import Counter as Cnt
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import hash_password
from ..models import ACTIVE_STATUSES, Point, Service, Shift, Turn, User
from . import availability, queueing
from .errors import Conflict, DomainError, NotFound

USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,40}$")
MIN_PASSWORD = 6
STAFF_ROLE = "MEDICO"


# ------------------------------------------------------------------ consultas
def _active_counts(db: Session) -> Cnt:
    rows = db.execute(select(Turn.point_id).where(Turn.day == queueing.today(), Turn.status.in_(ACTIVE_STATUSES))).scalars().all()
    return Cnt(rows)


def list_points(db: Session) -> list[dict]:
    shifts = availability.load_shifts(db)
    counts = _active_counts(db)
    now = availability.local_now()
    out = []
    for p in db.execute(select(Point).order_by(Point.id)).scalars().all():
        own = [s for s in shifts if s.point_id == p.id]
        out.append({
            "point": p, "status": availability.point_status(p, shifts, now), "active_turns": counts.get(p.id, 0),
            "shifts": own, "scheduled": bool(own),
            "on_duty": [s.user for s in own if availability.covers(s, now)],
        })
    return out


def list_staff(db: Session) -> list[dict]:
    shifts = availability.load_shifts(db)
    now = availability.local_now()
    users = db.execute(select(User).where(User.role == STAFF_ROLE).order_by(User.name)).scalars().all()
    return [{
        "user": u, "shifts": [s for s in shifts if s.user_id == u.id],
        "current_point": availability.user_point(db, u, shifts, now),
        "next_shift": availability.next_shift(u, shifts, now),
    } for u in users]


# ------------------------------------------------------------------ puntos
def _services(db: Session, codes: list[str]) -> list[Service]:
    if not codes:
        raise DomainError("Selecciona al menos un servicio para el punto", 422)
    found = db.execute(select(Service).where(Service.code.in_(codes))).scalars().all()
    if len(found) != len(set(codes)):
        raise DomainError("Algun servicio no existe", 422)
    return list(found)


def _name(db: Session, name: str, exclude_id: int | None = None) -> str:
    name = name.strip()
    if len(name) < 2:
        raise DomainError("El nombre del punto es muy corto", 422)
    dup = db.execute(select(Point).where(Point.name == name)).scalar_one_or_none()
    if dup and dup.id != exclude_id:
        raise Conflict(f"Ya existe un punto llamado '{name}'")
    return name


def _get_point(db: Session, point_id: int) -> Point:
    p = db.get(Point, point_id)
    if not p:
        raise NotFound("Punto no existe")
    return p


def _require_no_active_turns(db: Session, p: Point, action: str) -> None:
    n = _active_counts(db).get(p.id, 0)
    if n:
        raise Conflict(f"No se puede {action}: tiene {n} turno(s) activo(s). Reasignalos o atiendelos primero")


def create_point(db: Session, name: str, service_codes: list[str], enabled: bool = True) -> Point:
    p = Point(name=_name(db, name), active=True, enabled=enabled, services=_services(db, service_codes))
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_point(db: Session, point_id: int, changes: dict) -> Point:
    p = _get_point(db, point_id)
    if "name" in changes:
        p.name = _name(db, changes["name"], p.id)
    if "service_codes" in changes:
        new = _services(db, changes["service_codes"])
        removed = {s.code for s in p.services} - {s.code for s in new}
        if removed:
            n = db.execute(select(Turn).join(Service).where(
                Turn.point_id == p.id, Turn.day == queueing.today(), Turn.status.in_(ACTIVE_STATUSES), Service.code.in_(removed)
            )).scalars().first()
            if n:
                raise Conflict("No se puede quitar un servicio con turnos activos en este punto")
        p.services = new
    if "enabled" in changes:
        if changes["enabled"] is False and p.enabled:
            _require_no_active_turns(db, p, "cerrar el punto")
        p.enabled = changes["enabled"]
    db.commit()
    db.refresh(p)
    return p


def delete_point(db: Session, point_id: int) -> None:
    p = _get_point(db, point_id)
    _require_no_active_turns(db, p, "eliminar el punto")
    if db.execute(select(Turn.id).where(Turn.point_id == p.id).limit(1)).first():
        raise Conflict("El punto tiene historial de turnos: ciérralo en lugar de eliminarlo")
    if db.execute(select(User.id).where(User.point_id == p.id).limit(1)).first():
        raise Conflict("Hay usuarios con este punto como asignacion fija")
    db.delete(p)
    db.commit()


# ------------------------------------------------------------------ personal
def _get_staff(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if not u or u.role != STAFF_ROLE:
        raise NotFound("Funcionario no existe")
    return u


def _check_password(pw: str) -> None:
    if len(pw) < MIN_PASSWORD:
        raise DomainError(f"La contrasena debe tener al menos {MIN_PASSWORD} caracteres", 422)


def create_staff(db: Session, name: str, username: str, password: str) -> User:
    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        raise DomainError("Usuario invalido: usa 3 a 40 letras minusculas, numeros, punto, guion o guion bajo", 422)
    if len(name.strip()) < 2:
        raise DomainError("El nombre es muy corto", 422)
    _check_password(password)
    if db.execute(select(User).where(User.username == username)).scalar_one_or_none():
        raise Conflict(f"El usuario '{username}' ya existe")
    u = User(username=username, name=name.strip(), role=STAFF_ROLE, password_hash=hash_password(password), point_id=None)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def update_staff(db: Session, user_id: int, changes: dict) -> User:
    u = _get_staff(db, user_id)
    if changes.get("name"):
        u.name = changes["name"].strip()
    if changes.get("password"):
        _check_password(changes["password"])
        u.password_hash = hash_password(changes["password"])
    db.commit()
    return u


def delete_staff(db: Session, user_id: int) -> None:
    u = _get_staff(db, user_id)
    pt = availability.user_point(db, u)
    if pt and queueing.current_turn(db, pt.id):
        raise Conflict("El funcionario tiene un paciente en atencion en este momento")
    db.execute(Shift.__table__.delete().where(Shift.user_id == u.id))
    db.delete(u)
    db.commit()


# ------------------------------------------------------------------ turnos de trabajo
def create_shift(db: Session, user_id: int, point_id: int, weekdays: list[int], start: time, end: time) -> Shift:
    u = _get_staff(db, user_id)
    p = _get_point(db, point_id)
    days = sorted(set(weekdays))
    if not days or any(d < 0 or d > 6 for d in days):
        raise DomainError("Selecciona al menos un dia de la semana", 422)
    if end <= start:
        raise DomainError("La hora de fin debe ser posterior a la de inicio", 422)
    for s in availability.load_shifts(db):
        if not set(s.days) & set(days) or not availability.overlaps(start, end, s.start_time, s.end_time):
            continue
        if s.user_id == u.id:
            raise Conflict(f"{u.name} ya tiene un turno que se cruza ({s.point.name}, {s.start_time:%H:%M}-{s.end_time:%H:%M})")
        if s.point_id == p.id:
            raise Conflict(f"{p.name} ya tiene a {s.user.name} en ese horario ({s.start_time:%H:%M}-{s.end_time:%H:%M})")
    sh = Shift(user_id=u.id, point_id=p.id, weekdays=",".join(map(str, days)), start_time=start, end_time=end)
    db.add(sh)
    db.commit()
    db.refresh(sh)
    return sh


def delete_shift(db: Session, shift_id: int) -> None:
    sh = db.get(Shift, shift_id)
    if not sh:
        raise NotFound("Turno de trabajo no existe")
    db.delete(sh)
    db.commit()
