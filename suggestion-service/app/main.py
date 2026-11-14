from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import model
from .db import SessionLocal, Stat, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Turi - Servicio de sugerencia de turnos", version="1.0.0", lifespan=lifespan)


def get_db():
    with SessionLocal() as db:
        yield db


class QItem(BaseModel):
    id: int | None = None
    service: str
    preferential: bool = False
    key: float = 0.0  # menor = se atiende antes


class InService(BaseModel):
    service: str
    preferential: bool = False
    elapsed_min: float = 0.0


class PointIn(BaseModel):
    id: int
    name: str = ""
    services: list[str] = []
    active: bool = True
    queue: list[QItem] = []
    in_service: InService | None = None


class SuggestIn(BaseModel):
    service: str
    preferential: bool = False
    new_key: float
    prior_minutes: dict[str, float]
    points: list[PointIn]


class Option(BaseModel):
    point_id: int
    name: str
    est_wait_min: float
    est_service_min: float
    queue_ahead: int
    score: float
    reason: str
    recommended: bool = False


class SuggestOut(BaseModel):
    options: list[Option]
    model: str = "ema-shrinkage-v1"


class EstimateIn(BaseModel):
    prior_minutes: dict[str, float]
    point: PointIn


class EstimateOut(BaseModel):
    waits: dict[int, float]
    service_minutes: dict[int, float]


class LearnIn(BaseModel):
    service: str
    point_id: int
    preferential: bool = False
    minutes: float = Field(gt=0)


def _est(db: Session, cache: dict, service: str, point_id: int, pref: bool, prior: dict[str, float]) -> float:
    if service not in cache:
        cache[service] = model.load_table(db, service)
    return model.estimate(cache[service], str(point_id), pref, prior.get(service, 10.0))


def _remaining(db: Session, p: PointIn, prior: dict[str, float], cache: dict) -> float:
    if not p.in_service:
        return 0.0
    s = p.in_service
    est = _est(db, cache, s.service, p.id, s.preferential, prior)
    return max(est - s.elapsed_min, 1.0)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/suggest", response_model=SuggestOut)
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
        options.append(
            Option(
                point_id=p.id,
                name=p.name,
                est_wait_min=round(wait, 1),
                est_service_min=round(mine, 1),
                queue_ahead=ahead,
                score=round(wait + 0.25 * mine, 2),
                reason=f"{who}{busy}, espera aprox. {round(wait)} min",
            )
        )
    options.sort(key=lambda o: (o.score, o.queue_ahead, o.point_id))
    if options:
        options[0].recommended = True
    return SuggestOut(options=options)


@app.post("/estimate", response_model=EstimateOut)
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


@app.post("/learn", status_code=204)
def learn(body: LearnIn, db: Session = Depends(get_db)):
    model.learn(db, body.service, str(body.point_id), body.preferential, body.minutes)


@app.get("/model/stats")
def stats(db: Session = Depends(get_db)):
    rows = db.execute(select(Stat).order_by(Stat.service, Stat.point_id, Stat.grp)).scalars().all()
    return [
        {"service": r.service, "point_id": r.point_id, "group": r.grp, "samples": r.n, "mean_min": round(r.mean, 2)}
        for r in rows
    ]
