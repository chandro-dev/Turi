"""Prueba del modelo de IA para el supervisor: estado del entrenamiento, efectividad y consultas puntuales."""
from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import SUGGEST_URL
from ..models import NORMAL, PREFERENCIAL, Point, Service
from . import suggest_client, turn_service
from .suggest_client import fmt_min
from .errors import DomainError

TIMEOUT = 5.0


def _call(path: str, body: dict) -> dict:
    try:
        r = httpx.post(f"{SUGGEST_URL}{path}", json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        raise DomainError("El servicio de IA no esta disponible en este momento", 503) from e


def report(db: Session) -> dict:
    """Reporte de entrenamiento y efectividad, con nombres legibles de servicios y puntos."""
    services = {s.code: s for s in db.execute(select(Service)).scalars().all()}
    points = {str(p.id): p.name for p in db.execute(select(Point)).scalars().all()}
    data = _call("/model/report", {"prior_minutes": suggest_client.priors(db)})
    for row in data["by_service"]:
        row["name"] = services[row["service"]].name if row["service"] in services else row["service"]
    for c in data["cells"]:
        c["service_name"] = services[c["service"]].name if c["service"] in services else c["service"]
        c["point_name"] = points.get(c["point_id"], f"Punto {c['point_id']}")
    data["policy"] = suggest_client.policy()
    return data


def predict(db: Session, service_code: str, preferential: bool, point_id: int | None) -> dict:
    """Responde: cuanto tardara la atencion y a que punto enviar a un paciente con este perfil ahora mismo."""
    service = turn_service.get_service(db, service_code)
    priors = suggest_client.priors(db)
    cls = PREFERENCIAL if preferential else NORMAL
    options, model = suggest_client.suggest_points(db, service, cls)
    by_point = {o["point_id"]: o for o in options}

    rows = []
    for p in db.execute(select(Point).order_by(Point.id)).scalars().all():
        if service_code not in [s.code for s in p.services]:
            continue
        if point_id is not None and p.id != point_id:
            continue
        pr = _call("/predict", {"service": service_code, "point_id": p.id, "preferential": preferential,
                                "prior_minutes": priors.get(service_code, 10.0)})
        o = by_point.get(p.id)
        rows.append({
            "point_id": p.id, "name": p.name, "active": p.active,
            "minutes": pr["minutes"], "low": pr["low"], "high": pr["high"], "margin": pr["margin"],
            "samples": pr["samples"], "confidence_pct": pr["confidence_pct"], "levels": pr["levels"],
            "est_wait_min": o["est_wait_min"] if o else None,
            "est_wait_normal_min": o["est_wait_normal_min"] if o else None,
            "bonus_min": o["bonus_min"] if o else 0,
            "saved_min": o["saved_min"] if o else 0,
            "meets_target": o["meets_target"] if o else None,
            "recommended": bool(o and o["recommended"]),
        })
    rows.sort(key=lambda r: (not r["recommended"], r["est_wait_min"] if r["est_wait_min"] is not None else 1e9))

    best = next((r for r in rows if r["recommended"]), None)
    who = "paciente preferencial" if preferential else "paciente normal"
    if not rows:
        answer = f"No hay puntos que atiendan {service.name}."
    elif not best:
        answer = f"Ningun punto de {service.name} esta disponible ahora: todos estan en pausa."
    else:
        answer = (f"Para un {who} en {service.name}, el modelo recomienda {best['name']}: "
                  f"atencion de ~{fmt_min(best['minutes'])} (entre {fmt_min(best['low'])} y {fmt_min(best['high'])}) "
                  f"y espera de ~{fmt_min(best['est_wait_min'])}.")
        if preferential and best["saved_min"] > 0:
            answer += (f" La prioridad le ahorra {fmt_min(best['saved_min'])} frente a un turno normal"
                       f" (adelanto aplicado: {fmt_min(best['bonus_min'])}).")
        if preferential and best["meets_target"] is False:
            answer += f" Aun asi no se alcanza la meta de {fmt_min(suggest_client.policy()['target_wait_min'])}."
    return {"service": {"code": service.code, "name": service.name}, "preferential": preferential,
            "answer": answer, "points": rows, "policy": suggest_client.policy(), "model": model}
