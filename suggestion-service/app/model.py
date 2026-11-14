"""Modelo de estimacion de duracion de atencion.

Idea (intencionalmente simple y explicable):
  * Se aprende online la duracion media por (servicio, punto, grupo).
  * Cada nivel se "encoge" hacia el nivel mas general con un prior bayesiano
    ligero:  est = (n*media + K*padre) / (n + K).
  * Cadena: prior del servicio -> (srv,*,grupo) -> (srv,punto,*) -> (srv,punto,grupo).
    Un punto nuevo hereda lo aprendido del servicio y converge a su propia
    realidad conforme acumula datos.
  * El numero efectivo de muestras se limita (CAP) para que el modelo siga
    adaptandose si el comportamiento cambia.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Stat

K = 3.0
CAP = 50
MIN_MINUTES = 0.5
MAX_MINUTES = 240.0

Table = dict[tuple[str, str], tuple[int, float]]


def group_of(preferential: bool) -> str:
    return "pref" if preferential else "normal"


def load_table(db: Session, service: str) -> Table:
    rows = db.execute(select(Stat).where(Stat.service == service)).scalars().all()
    return {(r.point_id, r.grp): (r.n, r.mean) for r in rows}


def estimate(table: Table, point_id: str, preferential: bool, prior: float) -> float:
    g = group_of(preferential)
    est = float(prior)
    for key in (("*", "*"), ("*", g), (point_id, "*"), (point_id, g)):
        row = table.get(key)
        if row:
            n, mean = row
            est = (n * mean + K * est) / (n + K)
    return est


def learn(db: Session, service: str, point_id: str, preferential: bool, minutes: float) -> None:
    minutes = min(max(minutes, MIN_MINUTES), MAX_MINUTES)
    g = group_of(preferential)
    for p, grp in ((point_id, g), (point_id, "*"), ("*", g), ("*", "*")):
        row = db.execute(
            select(Stat).where(Stat.service == service, Stat.point_id == p, Stat.grp == grp)
        ).scalar_one_or_none()
        if row is None:
            row = Stat(service=service, point_id=p, grp=grp, n=0, mean=0.0)
            db.add(row)
        row.n = (row.n or 0) + 1
        if row.n == 1:
            row.mean = minutes
        else:
            row.mean = row.mean + (minutes - row.mean) / min(row.n, CAP)
    db.commit()
