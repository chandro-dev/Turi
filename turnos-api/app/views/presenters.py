"""VISTA (V) - presentadores: convierten entidades del modelo en JSON para el cliente."""
from __future__ import annotations

from datetime import datetime

from ..core.config import TZ
from ..models import PREFERENCIAL, Point, Turn, User


def iso(d: datetime | None) -> str | None:
    return d.astimezone(TZ).isoformat() if d else None


def _minutes(a: datetime | None, b: datetime | None) -> float | None:
    return round((b - a).total_seconds() / 60, 1) if a and b else None


def mask_name(name: str) -> str:
    parts = name.split()
    return parts[0] + (f" {parts[1][0]}." if len(parts) > 1 else "")


def turn(t: Turn, est: dict | None = None, public: bool = False) -> dict:
    est = est or {}
    out = {
        "id": t.id,
        "code": t.code,
        "status": t.status,
        "service": {"code": t.service.code, "name": t.service.name, "color": t.service.color},
        "point": {"id": t.point.id, "name": t.point.name},
        "priority_class": t.priority_class,
        "priority_reasons": [r for r in t.priority_reasons.split(",") if r],
        "position": est.get("pos"),
        "eta_min": round(est["wait_min"]) if "wait_min" in est else None,
        "created_at": iso(t.created_at),
        "called_at": iso(t.called_at),
        "started_at": iso(t.started_at),
        "finished_at": iso(t.finished_at),
        "wait_min": _minutes(t.created_at, t.called_at),          # llegada -> llamado
        "duration_min": _minutes(t.started_at, t.finished_at),    # tiempo de atencion
        "bonus_min": t.bonus_min,
        "no_show_count": t.no_show_count,
        "reassign_count": t.reassign_count,
    }
    if public:
        out["patient_name"] = mask_name(t.patient_name)
    else:
        out.update(patient_name=t.patient_name, doc_number=t.doc_number, phone=t.phone, age=t.age,
                   pregnant=t.pregnant, disability=t.disability)
    return out


def user(u: User, point: Point | None = None) -> dict:
    point = point if point is not None else u.point
    return {
        "id": u.id, "username": u.username, "name": u.name, "role": u.role,
        "point": {"id": point.id, "name": point.name} if point else None,
    }


def point_row(p: Point, waiting: int, busy: bool, status: str = "open") -> dict:
    return {"id": p.id, "name": p.name, "active": status == "open", "status": status,
            "services": [s.code for s in p.services], "waiting": waiting, "busy": busy}


def display(data: dict) -> dict:
    """Pantalla publica: solo codigos y puntos, sin datos personales."""
    return {
        "calls": [
            {"code": t.code, "point": t.point.name, "status": t.status, "called_at": iso(t.called_at),
             "preferential": t.priority_class == PREFERENCIAL, "color": t.service.color}
            for t in data["calling"]
        ],
        "points": [
            {"name": r["point"].name, "active": r["status"] == "open", "status": r["status"], "waiting": r["waiting"],
             "upcoming": [{"code": t.code, "preferential": t.priority_class == PREFERENCIAL, "color": t.service.color}
                          for t in r["upcoming"]]}
            for r in data["points"]
        ],
    }


def doctor_panel(d: dict) -> dict:
    if d.get("off_shift"):
        return {"off_shift": True, "next_shift": d["next_shift"]}
    p = d["point"]
    est = d["estimates"]
    return {
        "off_shift": False,
        "point": {"id": p.id, "name": p.name, "active": p.active, "status": d["status"], "services": [s.name for s in p.services]},
        "current": turn(d["current"]) if d["current"] else None,
        "queue": [turn(t, est.get(t.id)) for t in d["queue"]],
        "no_shows": [turn(t) for t in d["no_shows"]],
        "done_today": d["done_today"],
    }


# ------------------------------------------------------------ administracion de recursos
def shift(s) -> dict:
    return {"id": s.id, "user_id": s.user_id, "user_name": s.user.name, "point_id": s.point_id, "point_name": s.point.name,
            "weekdays": s.days, "start": s.start_time.strftime("%H:%M"), "end": s.end_time.strftime("%H:%M"),
            "overnight": s.end_time <= s.start_time}


def admin_point(d: dict) -> dict:
    p = d["point"]
    return {
        "id": p.id, "name": p.name, "enabled": p.enabled, "paused": not p.active, "status": d["status"],
        "services": [{"code": s.code, "name": s.name, "color": s.color} for s in p.services],
        "active_turns": d["active_turns"], "scheduled": d["scheduled"],
        "shifts": [shift(s) for s in d["shifts"]],
        "on_duty": [u.name for u in d["on_duty"]],
    }


def admin_user(d: dict) -> dict:
    u = d["user"]
    cp = d["current_point"]
    return {
        "id": u.id, "name": u.name, "username": u.username, "role": u.role, "active": u.active,
        "fixed_point": u.point.name if u.point else None,
        "current_point": cp.name if cp else None,
        "shifts": [shift(s) for s in d["shifts"]],
        "next_shift": d["next_shift"],
    }


def admin_service(s) -> dict:
    return {"id": s.id, "code": s.code, "name": s.name, "prior_minutes": s.prior_minutes, "color": s.color}
