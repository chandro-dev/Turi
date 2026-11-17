"""CONTROLADOR (C): endpoints HTTP. Orquesta el estimador (modelo) y devuelve esquemas (vista)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import estimator, sk_model
from ..models.entities import Stat, TrainingLog
from ..views.schemas import (
    EstimateIn, EstimateOut, LearnIn, Option, PointIn, PredictIn, PredictOut, ReportIn, SuggestIn, SuggestOut,
)

router = APIRouter()
BONUS_STEP_MIN = 5  # el modelo sube la bonificacion de prioridad en pasos de 5 min


def fmt_min(m: float, decimals: int = 0) -> str:
    """Minutos legibles: '45 min'; desde 60 min pasa a horas ('1 h', '1 h 15 min')."""
    v = round(m, decimals)
    if decimals == 0:
        v = int(v)
    if v < 60:
        return f"{v:g} min"
    h, r = divmod(int(round(v)), 60)
    return f"{h} h {r} min" if r else f"{h} h"


def _est(db: Session, cache: dict, service: str, point_id: int, pref: bool, prior: dict[str, float]) -> float:
    if service not in cache:
        cache[service] = estimator.load_table(db, service)
    return estimator.estimate(cache[service], str(point_id), pref, prior.get(service, 10.0),
                              service=service, hour=cache.get("_hour"))


def _remaining(db: Session, p: PointIn, prior: dict[str, float], cache: dict) -> float:
    """Minutos que faltan para liberar el punto (paciente en curso)."""
    if not p.in_service:
        return 0.0
    s = p.in_service
    return max(_est(db, cache, s.service, p.id, s.preferential, prior) - s.elapsed_min, 1.0)


def _wait_with_key(db: Session, p: PointIn, key: float, prior: dict[str, float], cache: dict) -> tuple[float, int]:
    """Espera y personas por delante para un turno cuya clave de orden es `key`."""
    wait, ahead = _remaining(db, p, prior, cache), 0
    for item in p.queue:
        if item.key <= key:
            ahead += 1
            wait += _est(db, cache, item.service, p.id, item.preferential, prior)
    return wait, ahead


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/suggest", response_model=SuggestOut)
def suggest(body: SuggestIn, db: Session = Depends(get_db)):
    """Ordena los puntos por espera estimada.

    Para pacientes prioritarios el modelo decide ademas CUANTA prioridad otorgar: parte de la
    bonificacion minima y la sube de a 5 min hasta cumplir la meta de espera (o llegar al tope).
    """
    cache: dict = {"_hour": body.hour}
    options: list[Option] = []
    for p in body.points:
        if not p.active or body.service not in p.services:
            continue
        normal_wait, normal_ahead = _wait_with_key(db, p, body.base_key, body.prior_minutes, cache)
        bonus = body.bonus_min if body.preferential else 0.0
        wait, ahead = _wait_with_key(db, p, body.base_key - bonus * 60, body.prior_minutes, cache)
        if body.preferential and body.target_wait_min is not None:
            while wait > body.target_wait_min and bonus < body.max_bonus_min:
                bonus = min(bonus + BONUS_STEP_MIN, body.max_bonus_min)
                wait, ahead = _wait_with_key(db, p, body.base_key - bonus * 60, body.prior_minutes, cache)
        mine = _est(db, cache, body.service, p.id, body.preferential, body.prior_minutes)
        meets = (not body.preferential) or body.target_wait_min is None or wait <= body.target_wait_min
        busy = " (atendiendo ahora)" if p.in_service else ""
        who = "sin personas por delante" if ahead == 0 else f"{ahead} por delante"
        # prioritarios: la inmediatez pesa mas que la duracion de su propia atencion
        score = wait + (0.05 if body.preferential else 0.25) * mine
        options.append(Option(
            point_id=p.id, name=p.name, est_wait_min=round(wait, 1), est_service_min=round(mine, 1),
            queue_ahead=ahead, score=round(score, 2), reason=f"{who}{busy}, espera aprox. {fmt_min(wait)}",
            bonus_min=round(bonus, 1), est_wait_normal_min=round(normal_wait, 1),
            saved_min=round(max(normal_wait - wait, 0.0), 1), meets_target=meets,
        ))
    options.sort(key=lambda o: (o.score, o.queue_ahead, o.point_id))
    if options:
        options[0].recommended = True
    return SuggestOut(options=options)


@router.post("/estimate", response_model=EstimateOut)
def estimate(body: EstimateIn, db: Session = Depends(get_db)):
    cache: dict = {"_hour": body.hour}
    p = body.point
    wait = _remaining(db, p, body.prior_minutes, cache)
    waits: dict[int, float] = {}
    mins: dict[int, float] = {}
    for item in sorted(p.queue, key=lambda i: i.key):
        dur = _est(db, cache, item.service, p.id, item.preferential, body.prior_minutes)
        if item.id is not None:
            waits[item.id] = round(wait, 1)
            mins[item.id] = round(dur, 1)
        wait += dur
    return EstimateOut(waits=waits, service_minutes=mins)


@router.post("/learn", status_code=204)
def learn(body: LearnIn, db: Session = Depends(get_db)):
    estimator.learn(db, body.service, str(body.point_id), body.preferential, body.minutes, body.prior_minutes, body.hour)


@router.post("/predict", response_model=PredictOut)
def predict(body: PredictIn, db: Session = Depends(get_db)):
    """Responde una consulta puntual: cuanto tardara una atencion y como se llego a esa cifra."""
    table = estimator.load_table(db, body.service)
    ex = estimator.explain(table, str(body.point_id), body.preferential, body.prior_minutes, body.service, body.hour)
    recent = db.execute(
        select(TrainingLog.abs_error).where(TrainingLog.service == body.service).order_by(TrainingLog.id.desc()).limit(30)
    ).scalars().all()
    mae = sum(recent) / len(recent) if recent else ex["minutes"] * 0.3
    margin = max(1.0, 1.25 * mae)
    return PredictOut(
        service=body.service, point_id=body.point_id, group=estimator.group_of(body.preferential),
        minutes=round(ex["minutes"], 1), margin=round(margin, 1),
        low=round(max(ex["minutes"] - margin, 0.5), 1), high=round(ex["minutes"] + margin, 1),
        samples=ex["samples"], confidence_pct=round(ex["confidence"] * 100), levels=ex["levels"],
    )


@router.post("/model/retrain")
def model_retrain(db: Session = Depends(get_db)):
    """Reentrena scikit-learn ahora con las atenciones guardadas."""
    return {**sk_model.train(db), "estimator": sk_model.info()}


@router.post("/model/report")
def model_report(body: ReportIn, db: Session = Depends(get_db)):
    return estimator.report(db, body.prior_minutes)


@router.get("/model/stats")
def stats(db: Session = Depends(get_db)):
    rows = db.execute(select(Stat).order_by(Stat.service, Stat.point_id, Stat.grp)).scalars().all()
    return [{"service": r.service, "point_id": r.point_id, "group": r.grp, "samples": r.n, "mean_min": round(r.mean, 2)}
            for r in rows]
