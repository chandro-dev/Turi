"""Cliente del microservicio de sugerencia (IA) con degradacion elegante si no responde."""
from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import SUGGEST_URL
from ..models import PREFERENCIAL, Point, Service, Turn
from . import queueing

log = logging.getLogger("turi")
TIMEOUT = 3.0


def priors(db: Session) -> dict[str, float]:
    return {s.code: s.prior_minutes for s in db.execute(select(Service)).scalars().all()}


def point_payload(db: Session, p: Point, queue: list[Turn] | None = None) -> dict:
    queue = queueing.waiting_turns(db, p.id) if queue is None else queue
    cur = queueing.current_turn(db, p.id)
    in_service = None
    if cur:
        ref = cur.started_at or queueing.now()
        in_service = {
            "service": cur.service.code,
            "preferential": cur.priority_class == PREFERENCIAL,
            "elapsed_min": max((queueing.now() - ref).total_seconds() / 60, 0.0),
        }
    return {
        "id": p.id,
        "name": p.name,
        "services": [s.code for s in p.services],
        "active": p.active,
        "queue": [
            {"id": t.id, "service": t.service.code, "preferential": t.priority_class == PREFERENCIAL, "key": queueing.turn_key(t)}
            for t in queue
        ],
        "in_service": in_service,
    }


def _fallback_suggest(service_code: str, new_key: float, points: list[dict], prior: dict[str, float]) -> list[dict]:
    opts = []
    for p in points:
        if not p["active"] or service_code not in p["services"]:
            continue
        ahead = [q for q in p["queue"] if q["key"] <= new_key]
        wait = sum(prior.get(q["service"], 10.0) for q in ahead)
        wait += prior.get(p["in_service"]["service"], 10.0) / 2 if p["in_service"] else 0
        opts.append({
            "point_id": p["id"], "name": p["name"], "est_wait_min": round(wait, 1),
            "est_service_min": prior.get(service_code, 10.0), "queue_ahead": len(ahead), "score": wait,
            "reason": f"{len(ahead)} por delante, espera aprox. {round(wait)} min (estimacion basica)",
            "recommended": False,
        })
    opts.sort(key=lambda o: (o["score"], o["queue_ahead"], o["point_id"]))
    if opts:
        opts[0]["recommended"] = True
    return opts


def suggest_points(db: Session, service: Service, priority_class: str) -> tuple[list[dict], str]:
    points = [point_payload(db, p) for p in db.execute(select(Point)).scalars().all()]
    prior = priors(db)
    nk = queueing.key_for(priority_class, queueing.now())
    body = {
        "service": service.code, "preferential": priority_class == PREFERENCIAL,
        "new_key": nk, "prior_minutes": prior, "points": points,
    }
    try:
        r = httpx.post(f"{SUGGEST_URL}/suggest", json=body, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return data["options"], data.get("model", "ia")
    except Exception as e:  # noqa: BLE001
        log.warning("suggestion-service no disponible, usando respaldo: %s", e)
        return _fallback_suggest(service.code, nk, points, prior), "respaldo-basico"


def estimate_point(db: Session, p: Point) -> dict[int, dict]:
    """turn_id -> {pos, wait_min} para los turnos en espera de un punto."""
    queue = queueing.waiting_turns(db, p.id)
    if not queue:
        return {}
    payload = point_payload(db, p, queue)
    prior = priors(db)
    waits: dict[int, float] = {}
    try:
        r = httpx.post(f"{SUGGEST_URL}/estimate", json={"prior_minutes": prior, "point": payload}, timeout=TIMEOUT)
        r.raise_for_status()
        waits = {int(k): v for k, v in r.json()["waits"].items()}
    except Exception as e:  # noqa: BLE001
        log.warning("estimate respaldo: %s", e)
        acc = 0.0
        for t in queue:
            waits[t.id] = acc
            acc += prior.get(t.service.code, 10.0)
    return {t.id: {"pos": i + 1, "wait_min": waits.get(t.id, 0.0)} for i, t in enumerate(queue)}


def estimates_for(db: Session, points: list[Point]) -> dict[int, dict]:
    est: dict[int, dict] = {}
    for p in points:
        est.update(estimate_point(db, p))
    return est


def learn(service_code: str, point_id: int, preferential: bool, minutes: float) -> None:
    try:
        httpx.post(
            f"{SUGGEST_URL}/learn",
            json={"service": service_code, "point_id": point_id, "preferential": preferential, "minutes": minutes},
            timeout=TIMEOUT,
        ).raise_for_status()
    except Exception as e:  # noqa: BLE001
        log.warning("learn fallo (se ignora): %s", e)
