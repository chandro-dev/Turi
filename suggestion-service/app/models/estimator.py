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
  * Cada aprendizaje registra la prediccion previa (TrainingLog) para medir efectividad.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .entities import Stat, TrainingLog

K = 3.0
CAP = 50
MIN_MINUTES = 0.5
MAX_MINUTES = 240.0
MATURE_SAMPLES = 20  # muestras por (servicio, punto, grupo) para considerar el aprendizaje "maduro"

Table = dict[tuple[str, str], tuple[int, float]]


def group_of(preferential: bool) -> str:
    return "pref" if preferential else "normal"


def load_table(db: Session, service: str) -> Table:
    rows = db.execute(select(Stat).where(Stat.service == service)).scalars().all()
    return {(r.point_id, r.grp): (r.n, r.mean) for r in rows}


def _chain(point_id: str, g: str):
    return (
        ("*", "*", "Todo el servicio"),
        ("*", g, "Todo el servicio, mismo tipo de paciente"),
        (point_id, "*", "Este punto"),
        (point_id, g, "Este punto y tipo de paciente"),
    )


def estimate(table: Table, point_id: str, preferential: bool, prior: float) -> float:
    est = float(prior)
    for p, g, _ in _chain(point_id, group_of(preferential)):
        row = table.get((p, g))
        if row:
            n, mean = row
            est = (n * mean + K * est) / (n + K)
    return est


def explain(table: Table, point_id: str, preferential: bool, prior: float) -> dict:
    """Desglose paso a paso de la estimacion, para mostrar al supervisor como se llego al numero."""
    est = float(prior)
    levels = [{"label": "Valor inicial del servicio", "samples": 0, "mean": round(prior, 2), "estimate": round(est, 2)}]
    samples = 0
    for p, g, label in _chain(point_id, group_of(preferential)):
        row = table.get((p, g))
        if row:
            n, mean = row
            est = (n * mean + K * est) / (n + K)
            levels.append({"label": label, "samples": n, "mean": round(mean, 2), "estimate": round(est, 2)})
            samples = n
    return {"minutes": est, "levels": levels, "samples": samples, "confidence": samples / (samples + K) if samples else 0.0}


def learn(db: Session, service: str, point_id: str, preferential: bool, minutes: float, prior: float | None = None) -> None:
    minutes = min(max(minutes, MIN_MINUTES), MAX_MINUTES)
    g = group_of(preferential)

    # 1) prediccion ANTES de aprender (evaluacion honesta)
    table = load_table(db, service)
    base = prior if prior is not None else (table[("*", "*")][1] if ("*", "*") in table else None)
    if base is not None:
        predicted = estimate(table, point_id, preferential, base)
        n_before = table.get((point_id, g), (0, 0.0))[0]
        db.add(TrainingLog(
            service=service, point_id=point_id, grp=g, predicted=predicted, actual=minutes, prior=prior,
            abs_error=abs(predicted - minutes), prior_error=abs(prior - minutes) if prior is not None else None,
            n_before=n_before,
        ))

    # 2) aprendizaje
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


# ---------------------------------------------------------------- reporte de efectividad
def _avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _rolling(vals: list[float | None], w: int) -> list[float | None]:
    out = []
    for i in range(len(vals)):
        chunk = [v for v in vals[max(0, i - w + 1): i + 1] if v is not None]
        out.append(sum(chunk) / len(chunk) if chunk else None)
    return out


def report(db: Session, priors: dict[str, float]) -> dict:
    logs = db.execute(select(TrainingLog).order_by(TrainingLog.id)).scalars().all()
    n = len(logs)
    errs = [r.abs_error for r in logs]
    base_errs = [r.prior_error for r in logs]
    mae, mae_base = _avg(errs), _avg(base_errs)
    improvement = (1 - mae / mae_base) * 100 if mae is not None and mae_base else None
    within = (sum(e <= 3 for e in errs) / n * 100) if n else None
    bias = _avg([r.predicted - r.actual for r in logs])
    recent, early = errs[-20:], errs[:20]

    window = 10
    roll_m, roll_b = _rolling(errs, window), _rolling(base_errs, window)
    step = max(1, n // 80)
    curve = [{"i": i + 1, "mae": round(roll_m[i], 2), "baseline": round(roll_b[i], 2) if roll_b[i] is not None else None}
             for i in range(window - 1 if n >= window else 0, n, step)]

    by_service = []
    for s in sorted({r.service for r in logs}):
        rs = [r for r in logs if r.service == s]
        m, b = _avg([r.abs_error for r in rs]), _avg([r.prior_error for r in rs])
        by_service.append({
            "service": s, "samples": len(rs), "mae": round(m, 2), "mae_baseline": round(b, 2) if b is not None else None,
            "improvement_pct": round((1 - m / b) * 100, 1) if b else None,
        })

    stats = db.execute(select(Stat).where(Stat.point_id != "*", Stat.grp != "*").order_by(Stat.service, Stat.point_id, Stat.grp)).scalars().all()
    tables: dict[str, Table] = {}
    cells = []
    for r in stats:
        t = tables.setdefault(r.service, load_table(db, r.service))
        prior = priors.get(r.service, t.get(("*", "*"), (0, 10.0))[1])
        cells.append({
            "service": r.service, "point_id": r.point_id, "group": r.grp, "samples": r.n, "mean_min": round(r.mean, 2),
            "prior_min": round(prior, 2), "estimate_min": round(estimate(t, r.point_id, r.grp == "pref", prior), 2),
            "maturity_pct": round(min(1.0, r.n / MATURE_SAMPLES) * 100),
        })

    if n < 10:
        verdict = ("insufficient", "Datos insuficientes: se necesitan al menos 10 atenciones finalizadas para evaluar el modelo.")
    elif improvement is None:
        verdict = ("insufficient", "Aun no hay linea base para comparar.")
    elif improvement >= 15:
        verdict = ("good", f"El modelo supera claramente la estimacion base: reduce el error en {improvement:.0f}%.")
    elif improvement >= 0:
        verdict = ("fair", f"Mejora leve sobre la estimacion base ({improvement:.0f}%). Seguira mejorando con mas atenciones.")
    else:
        verdict = ("poor", "Aun no supera la estimacion base. Se necesitan mas atenciones para que aprenda.")

    return {
        "samples": n, "mae": _r(mae), "mae_baseline": _r(mae_base), "improvement_pct": _r(improvement, 1),
        "within_3min_pct": _r(within, 1), "bias_min": _r(bias), "mae_recent": _r(_avg(recent)), "mae_early": _r(_avg(early)),
        "verdict": {"level": verdict[0], "text": verdict[1]},
        "curve": curve, "curve_window": window, "by_service": by_service, "cells": cells,
        "mature_samples": MATURE_SAMPLES,
    }


def _r(x, d=2):
    return round(x, d) if x is not None else None
