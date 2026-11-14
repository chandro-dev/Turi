"""Reglas de negocio: prioridad, ordenamiento de fila, numeracion y cliente del servicio de IA."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .config import SUGGEST_URL, TZ
from .models import (
    BAJA,
    CALLED,
    IN_SERVICE,
    NORMAL,
    PREFERENCIAL,
    WAITING,
    Counter,
    Point,
    Service,
    Turn,
    TurnEvent,
)

log = logging.getLogger("turi")

# Ventaja (en minutos de espera "virtual") segun clase de prioridad.
# Preferencial se adelanta hasta 20 min a un turno normal; BAJA (no se presento) cede 15 min.
BONUS_MIN = {PREFERENCIAL: 20, NORMAL: 0, BAJA: -15}
SENIOR_AGE = 60


def now() -> datetime:
    return datetime.now(timezone.utc)


def today() -> date:
    return datetime.now(TZ).date()


def classify(age: int, pregnant: bool, disability: bool) -> tuple[str, list[str]]:
    reasons = []
    if age >= SENIOR_AGE:
        reasons.append("Adulto mayor")
    if pregnant:
        reasons.append("Gestante")
    if disability:
        reasons.append("Discapacidad")
    return (PREFERENCIAL if reasons else NORMAL), reasons


def key_for(priority_class: str, queued_at: datetime) -> float:
    return queued_at.timestamp() - BONUS_MIN[priority_class] * 60


def turn_key(t: Turn) -> float:
    return key_for(t.priority_class, t.queued_at)


def next_code(db: Session, service: Service) -> tuple[str, date]:
    day = today()
    db.execute(
        pg_insert(Counter).values(service_id=service.id, day=day, last=0).on_conflict_do_nothing()
    )
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


def priors(db: Session) -> dict[str, float]:
    return {s.code: s.prior_minutes for s in db.execute(select(Service)).scalars().all()}


def point_payload(db: Session, p: Point, queue: list[Turn] | None = None) -> dict:
    queue = waiting_turns(db, p.id) if queue is None else queue
    cur = current_turn(db, p.id)
    in_service = None
    if cur:
        ref = cur.started_at or now()
        in_service = {
            "service": cur.service.code,
            "preferential": cur.priority_class == PREFERENCIAL,
            "elapsed_min": max((now() - ref).total_seconds() / 60, 0.0),
        }
    return {
        "id": p.id,
        "name": p.name,
        "services": [s.code for s in p.services],
        "active": p.active,
        "queue": [
            {
                "id": t.id,
                "service": t.service.code,
                "preferential": t.priority_class == PREFERENCIAL,
                "key": turn_key(t),
            }
            for t in queue
        ],
        "in_service": in_service,
    }


# ---- Cliente del microservicio de sugerencia, con degradacion elegante ----

def _fallback_suggest(service_code: str, new_key: float, points: list[dict], prior: dict[str, float]) -> list[dict]:
    opts = []
    for p in points:
        if not p["active"] or service_code not in p["services"]:
            continue
        ahead = [q for q in p["queue"] if q["key"] <= new_key]
        wait = sum(prior.get(q["service"], 10.0) for q in ahead) + (prior.get(p["in_service"]["service"], 10.0) / 2 if p["in_service"] else 0)
        opts.append(
            {
                "point_id": p["id"],
                "name": p["name"],
                "est_wait_min": round(wait, 1),
                "est_service_min": prior.get(service_code, 10.0),
                "queue_ahead": len(ahead),
                "score": wait,
                "reason": f"{len(ahead)} por delante, espera aprox. {round(wait)} min (estimacion basica)",
                "recommended": False,
            }
        )
    opts.sort(key=lambda o: (o["score"], o["queue_ahead"], o["point_id"]))
    if opts:
        opts[0]["recommended"] = True
    return opts


def suggest_points(db: Session, service: Service, priority_class: str) -> tuple[list[dict], str]:
    points = [point_payload(db, p) for p in db.execute(select(Point)).scalars().all()]
    prior = priors(db)
    nk = key_for(priority_class, now())
    body = {
        "service": service.code,
        "preferential": priority_class == PREFERENCIAL,
        "new_key": nk,
        "prior_minutes": prior,
        "points": points,
    }
    try:
        r = httpx.post(f"{SUGGEST_URL}/suggest", json=body, timeout=3.0)
        r.raise_for_status()
        data = r.json()
        return data["options"], data.get("model", "ia")
    except Exception as e:  # noqa: BLE001
        log.warning("suggestion-service no disponible, usando respaldo: %s", e)
        return _fallback_suggest(service.code, nk, points, prior), "respaldo-basico"


def estimate_point(db: Session, p: Point) -> dict[int, dict]:
    """turn_id -> {pos, wait_min} para los turnos en espera de un punto."""
    queue = waiting_turns(db, p.id)
    if not queue:
        return {}
    payload = point_payload(db, p, queue)
    prior = priors(db)
    waits: dict[int, float] = {}
    try:
        r = httpx.post(f"{SUGGEST_URL}/estimate", json={"prior_minutes": prior, "point": payload}, timeout=3.0)
        r.raise_for_status()
        waits = {int(k): v for k, v in r.json()["waits"].items()}
    except Exception as e:  # noqa: BLE001
        log.warning("estimate respaldo: %s", e)
        acc = 0.0
        for t in queue:
            waits[t.id] = acc
            acc += prior.get(t.service.code, 10.0)
    return {t.id: {"pos": i + 1, "wait_min": waits.get(t.id, 0.0)} for i, t in enumerate(queue)}


def learn(service_code: str, point_id: int, preferential: bool, minutes: float) -> None:
    try:
        httpx.post(
            f"{SUGGEST_URL}/learn",
            json={"service": service_code, "point_id": point_id, "preferential": preferential, "minutes": minutes},
            timeout=3.0,
        ).raise_for_status()
    except Exception as e:  # noqa: BLE001
        log.warning("learn fallo (se ignora): %s", e)
