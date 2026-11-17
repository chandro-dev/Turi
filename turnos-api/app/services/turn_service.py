"""Casos de uso sobre turnos: recepcion (crear/editar/cancelar/reasignar) y atencion (llamar/iniciar/cerrar)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    ACTIVE_STATUSES,
    BAJA,
    CALLED,
    CANCELLED,
    DONE,
    IN_SERVICE,
    NO_SHOW,
    PREFERENCIAL,
    WAITING,
    Point,
    Service,
    Turn,
    User,
)
from . import priority, queueing, suggest_client
from .errors import Conflict, DomainError, NotFound


# ------------------------------------------------------------------ consultas
def get_service(db: Session, code: str) -> Service:
    s = db.execute(select(Service).where(Service.code == code)).scalar_one_or_none()
    if not s:
        raise NotFound("Servicio no existe")
    return s


def get_turn(db: Session, turn_id: int) -> Turn:
    t = db.get(Turn, turn_id)
    if not t:
        raise NotFound("Turno no existe")
    return t


def list_turns(db: Session, include_closed: bool = False) -> list[Turn]:
    q = select(Turn).where(Turn.day == queueing.today())
    if not include_closed:
        q = q.where(Turn.status.in_(ACTIVE_STATUSES))
    return list(db.execute(q.order_by(Turn.created_at)).scalars().all())


# ------------------------------------------------------------------ recepcion
def preview(db: Session, service_code: str, age: int, pregnant: bool, disability: bool) -> dict:
    service = get_service(db, service_code)
    cls, reasons = _classify(age, pregnant, disability)
    options, model = suggest_client.suggest_points(db, service, cls)
    return {"priority_class": cls, "priority_reasons": reasons, "options": options, "model": model,
            "policy": suggest_client.policy()}


def _classify(age: int, pregnant: bool, disability: bool):
    try:
        return priority.classify(age, pregnant, disability)
    except priority.PatientRuleError as e:
        raise DomainError(str(e), 422) from e


def create_turn(db: Session, data: dict, username: str) -> tuple[Turn, str]:
    service = get_service(db, data["service_code"])
    cls, reasons = _classify(data["age"], data["pregnant"], data["disability"])
    doc = data["doc_number"].strip()
    dup = db.execute(
        select(Turn).where(Turn.doc_number == doc, Turn.day == queueing.today(), Turn.status.in_(ACTIVE_STATUSES))
    ).scalars().first()
    if dup:
        raise Conflict(f"El paciente ya tiene un turno activo: {dup.code} ({dup.point.name})")

    options, model = suggest_client.suggest_points(db, service, cls)
    point_id = data.get("point_id")
    if point_id is None:
        if not options:
            raise Conflict("No hay puntos de atencion disponibles para este servicio")
        point_id = options[0]["point_id"]
    point = db.get(Point, point_id)
    if not point or service.code not in [s.code for s in point.services]:
        raise DomainError("El punto no atiende este servicio", 400)
    chosen = next((o for o in options if o["point_id"] == point_id), None)

    code, day = queueing.next_code(db, service)
    t = Turn(
        code=code, day=day, service_id=service.id, point_id=point.id, doc_number=doc,
        patient_name=data["patient_name"].strip(), phone=(data.get("phone") or "").strip() or None,
        age=data["age"], pregnant=data["pregnant"], disability=data["disability"],
        priority_class=cls, priority_reasons=",".join(reasons), status=WAITING,
        initial_wait_est=chosen["est_wait_min"] if chosen else None, created_by=username,
        bonus_min=chosen["bonus_min"] if chosen and cls == PREFERENCIAL else None,  # prioridad decidida por el modelo
    )
    db.add(t)
    db.flush()
    suggested = options[0]["name"] if options else "-"
    queueing.add_event(db, t, "CREATED", f"Asignado a {point.name} (sugerido: {suggested}; modelo: {model})", username)
    db.commit()
    db.refresh(t)
    return t, model


def patch_turn(db: Session, turn_id: int, changes: dict, username: str) -> Turn:
    t = get_turn(db, turn_id)
    if t.status not in (WAITING, NO_SHOW):
        raise Conflict("Solo se pueden editar turnos en espera o no presentados")
    age = changes.get("age", t.age)
    pregnant = changes.get("pregnant", t.pregnant)
    disability = changes.get("disability", t.disability)
    cls, reasons = _classify(age, pregnant, disability)  # valida la combinacion final
    for k, v in changes.items():
        if k == "phone":
            v = (v or "").strip() or None
        elif isinstance(v, str):
            v = v.strip()
        setattr(t, k, v)
    if t.priority_class != BAJA:  # un reincorporado conserva su prioridad baja
        t.priority_class = cls
    t.priority_reasons = ",".join(reasons)
    queueing.add_event(db, t, "EDITED", ", ".join(changes.keys()), username)
    db.commit()
    return t


def cancel_turn(db: Session, turn_id: int, username: str) -> Turn:
    t = get_turn(db, turn_id)
    if t.status not in (WAITING, NO_SHOW, CALLED):
        raise Conflict("El turno no se puede cancelar en su estado actual")
    t.status = CANCELLED
    t.finished_at = queueing.now()
    queueing.add_event(db, t, "CANCELLED", "", username)
    db.commit()
    return t


def reassign_turn(db: Session, turn_id: int, point_id: int, username: str) -> Turn:
    t = get_turn(db, turn_id)
    if t.status not in (WAITING, NO_SHOW):
        raise Conflict("Solo se reasignan turnos en espera o no presentados")
    p = db.get(Point, point_id)
    if not p or t.service.code not in [s.code for s in p.services]:
        raise DomainError("El punto no atiende este servicio", 400)
    detail = f"{t.point.name} -> {p.name}"
    if t.status == NO_SHOW:  # reincorporacion: vuelve a la fila con prioridad baja
        t.status = WAITING
        t.priority_class = BAJA
        t.bonus_min = None
        t.queued_at = queueing.now()
        queueing.add_event(db, t, "REQUEUED", f"Reincorporado en prioridad baja: {detail}", username)
    else:
        queueing.add_event(db, t, "REASSIGNED", detail, username)
    if p.id != t.point_id:
        t.reassign_count += 1
    t.point_id = p.id
    db.commit()
    db.refresh(t)
    return t


# ------------------------------------------------------------------ atencion
def _point_of(user: User) -> Point:
    if not user.point:
        raise DomainError("Tu usuario no tiene punto de atencion asignado", 400)
    return user.point


def _own_turn(db: Session, user: User, turn_id: int, *statuses: str) -> Turn:
    t = get_turn(db, turn_id)
    if t.point_id != _point_of(user).id:
        raise DomainError("El turno pertenece a otro punto de atencion", 403)
    if t.status not in statuses:
        raise Conflict(f"Accion no valida: el turno esta en estado {t.status}")
    return t


def doctor_panel(db: Session, user: User) -> dict:
    p = _point_of(user)
    db.refresh(p)
    day = queueing.today()
    by_status = lambda s: list(db.execute(  # noqa: E731
        select(Turn).where(Turn.point_id == p.id, Turn.day == day, Turn.status == s)).scalars().all())
    return {
        "point": p,
        "current": queueing.current_turn(db, p.id),
        "queue": queueing.waiting_turns(db, p.id),
        "estimates": suggest_client.estimate_point(db, p),
        "no_shows": by_status(NO_SHOW),
        "done_today": len(by_status(DONE)),
    }


def set_point_active(db: Session, user: User, active: bool) -> bool:
    p = db.get(Point, _point_of(user).id)
    p.active = active
    db.commit()
    return p.active


def call_next(db: Session, user: User) -> Turn:
    p = _point_of(user)
    if queueing.current_turn(db, p.id):
        raise Conflict("Ya hay un paciente llamado o en atencion. Finaliza ese turno primero")
    queue = queueing.waiting_turns(db, p.id)
    if not queue:
        raise NotFound("No hay pacientes en espera")
    t = queue[0]
    t.status = CALLED
    t.called_at = queueing.now()
    queueing.add_event(db, t, "CALLED", p.name, user.username)
    db.commit()
    return t


def recall(db: Session, user: User, turn_id: int) -> Turn:
    t = _own_turn(db, user, turn_id, CALLED)
    t.called_at = queueing.now()
    queueing.add_event(db, t, "RECALLED", "", user.username)
    db.commit()
    return t


def start(db: Session, user: User, turn_id: int) -> Turn:
    t = _own_turn(db, user, turn_id, CALLED)
    t.status = IN_SERVICE
    t.started_at = queueing.now()
    queueing.add_event(db, t, "STARTED", "", user.username)
    db.commit()
    return t


def no_show(db: Session, user: User, turn_id: int) -> Turn:
    t = _own_turn(db, user, turn_id, CALLED)
    t.status = NO_SHOW
    t.no_show_count += 1
    queueing.add_event(db, t, "NO_SHOW", f"Intento {t.no_show_count}", user.username)
    db.commit()
    return t


def finish(db: Session, user: User, turn_id: int) -> Turn:
    t = _own_turn(db, user, turn_id, IN_SERVICE)
    t.status = DONE
    t.finished_at = queueing.now()
    minutes = (t.finished_at - t.started_at).total_seconds() / 60
    queueing.add_event(db, t, "FINISHED", f"{minutes:.1f} min", user.username)
    db.commit()
    suggest_client.learn(t.service.code, t.point_id, t.priority_class == PREFERENCIAL, minutes,
                         suggest_client.priors(db).get(t.service.code))  # alimenta la IA
    return t
