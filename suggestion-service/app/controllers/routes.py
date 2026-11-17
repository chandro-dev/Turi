"""CONTROLADOR (C): endpoints HTTP. Orquesta el estimador (modelo) y devuelve esquemas (vista)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import estimator
from ..models.entities import Stat
from ..views.schemas import EstimateIn, EstimateOut, LearnIn, Option, PointIn, SuggestIn, SuggestOut

router = APIRouter()


def _est(db: Session, cache: dict, service: str, point_id: int, pref: bool, prior: dict[str, float]) -> float:
    if service not in cache:
        cache[service] = estimator.load_table(db, service)
    return estimator.estimate(cache[service], str(point_id), pref, prior.get(service, 10.0))


def _remaining(db: Session, p: PointIn, prior: dict[str, float], cache: dict) -> float:
    """Minutos que faltan para liberar el punto (paciente en curso)."""
    if not p.in_service:
        return 0.0
    s = p.in_service
    return max(_est(db, cache, s.service, p.id, s.preferential, prior) - s.elapsed_min, 1.0)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/suggest", response_model=SuggestOut)
def suggest(body: SuggestIn, db: Session = Depends(get_db)):
    cache: dict = {}
    options: list[Option] = []
    for p in body.points:
        if not p.active or body.service not in p.services:
            continue
        wait = _remaining(db, p, body.prior_minutes, cache)
        ahead = 0
        for item in p.queue:
            if item.key <= body.new_key:
                ahead += 1
                wait += _est(db, cache, item.service, p.id, item.preferential, body.prior_minutes)
        mine = _est(db, cache, body.service, p.id, body.preferential, body.prior_minutes)
        busy = " (atendiendo ahora)" if p.in_service else ""
        who = "sin personas por delante" if ahead == 0 else f"{ahead} por delante"
        options.append(Option(
            point_id=p.id, name=p.name, est_wait_min=round(wait, 1), est_service_min=round(mine, 1),
            queue_ahead=ahead, score=round(wait + 0.25 * mine, 2),
            reason=f"{who}{busy}, espera aprox. {round(wait)} min",
        ))
    options.sort(key=lambda o: (o.score, o.queue_ahead, o.point_id))
    if options:
        options[0].recommended = True
    return SuggestOut(options=options)


@router.post("/estimate", response_model=EstimateOut)
def estimate(body: EstimateIn, db: Session = Depends(get_db)):
    cache: dict = {}
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
    estimator.learn(db, body.service, str(body.point_id), body.preferential, body.minutes)


@router.get("/model/stats")
def stats(db: Session = Depends(get_db)):
    rows = db.execute(select(Stat).order_by(Stat.service, Stat.point_id, Stat.grp)).scalars().all()
    return [{"service": r.service, "point_id": r.point_id, "group": r.grp, "samples": r.n, "mean_min": round(r.mean, 2)}
            for r in rows]
