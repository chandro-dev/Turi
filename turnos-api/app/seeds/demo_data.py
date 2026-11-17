"""Datos de prueba: historial del dia (para entrenar la IA) y pacientes en fila.

Se ejecuta al iniciar si SEED_DEMO=true y no hay turnos.
Manual:  docker compose exec turnos-api python -m app.seeds.demo_data
"""
import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..services import priority, queueing, suggest_client
from ..models import (
    CANCELLED,
    DONE,
    NO_SHOW,
    PREFERENCIAL,
    WAITING,
    Point,
    Service,
    Turn,
)

NAMES = [
    "Maria Lopez", "Juan Perez", "Ana Torres", "Carlos Diaz", "Lucia Fernandez", "Pedro Gomez",
    "Sofia Ramirez", "Jorge Castillo", "Valentina Ruiz", "Miguel Herrera", "Isabel Moreno",
    "Andres Vargas", "Rosa Mendoza", "Camilo Ortiz", "Elena Rojas", "Tomas Navarro", "Paula Medina",
    "Ricardo Suarez", "Gloria Pineda", "Hernando Mejia", "Diana Cardenas", "Luis Barrios",
    "Natalia Osorio", "Fabian Duran", "Marta Quintero", "Oscar Villa", "Carolina Peña", "Julian Cano",
]

# minutos reales medios por punto: Consultorio 2 es mas lento que el 1, para que la IA lo aprenda
REAL_MEAN = {"Consultorio 1": 9, "Consultorio 2": 16, "Laboratorio": 5, "Farmacia": 3, "Odontologia": 24}


def _patient(rng: random.Random, used: set[str]) -> dict:
    age = rng.choice([rng.randint(2, 17), rng.randint(18, 59), rng.randint(18, 59), rng.randint(60, 90)])
    doc = str(rng.randint(10_000_000, 1_099_999_999))
    while doc in used:
        doc = str(rng.randint(10_000_000, 1_099_999_999))
    used.add(doc)
    return {
        "doc_number": doc,
        "patient_name": rng.choice(NAMES),
        "age": age,
        "pregnant": 10 <= age <= 55 and rng.random() < 0.07,
        "disability": rng.random() < 0.06,
    }


def _build(db: Session, rng, used, service: Service, point: Point, created_at, status: str) -> Turn:
    p = _patient(rng, used)
    cls, reasons = priority.classify(p["age"], p["pregnant"], p["disability"])
    code, day = queueing.next_code(db, service)
    t = Turn(
        code=code, day=day, service_id=service.id, point_id=point.id, priority_class=cls,
        priority_reasons=",".join(reasons), status=status, created_at=created_at, queued_at=created_at,
        created_by="seed", phone=None, **p,
    )
    db.add(t)
    db.flush()
    queueing.add_event(db, t, "CREATED", "seed", "seed")
    return t


def seed_history(db: Session, force: bool = False, seed: int = 42) -> str:
    if not force and db.execute(select(Turn).limit(1)).first():
        return "ya hay turnos, se omite"
    rng = random.Random(seed)
    used: set[str] = set()
    services = db.execute(select(Service).order_by(Service.id)).scalars().all()
    points = db.execute(select(Point).order_by(Point.id)).scalars().all()
    serving = {s.code: [p for p in points if s.code in [x.code for x in p.services]] for s in services}
    now = queueing.now()
    learned = []

    # 1) Historial atendido (entrena la IA)
    for i in range(48):
        s = rng.choices(services, weights=[5, 3, 3, 2])[0]
        p = rng.choice(serving[s.code])
        created = now - timedelta(minutes=rng.randint(40, 300))
        t = _build(db, rng, used, s, p, created, DONE)
        dur = max(1.0, rng.gauss(REAL_MEAN.get(p.name, 8), REAL_MEAN.get(p.name, 8) * 0.25))
        t.called_at = created + timedelta(minutes=rng.uniform(2, 25))
        t.started_at = t.called_at + timedelta(seconds=rng.randint(20, 90))
        t.finished_at = t.started_at + timedelta(minutes=dur)
        learned.append((s.code, p.id, t.priority_class == PREFERENCIAL, dur))

    # 2) Cancelados y no presentados
    for status in (CANCELLED, CANCELLED, NO_SHOW, NO_SHOW):
        s = rng.choice(services)
        p = rng.choice(serving[s.code])
        t = _build(db, rng, used, s, p, now - timedelta(minutes=rng.randint(20, 120)), status)
        if status == NO_SHOW:
            t.called_at = t.created_at + timedelta(minutes=10)
            t.no_show_count = 1
        else:
            t.finished_at = t.created_at + timedelta(minutes=5)

    # 3) Fila actual: cada paciente se asigna al punto con menos gente
    load = {p.id: 0 for p in points}
    for i in range(14):
        s = rng.choices(services, weights=[5, 3, 3, 2])[0]
        p = min(serving[s.code], key=lambda x: load[x.id])
        load[p.id] += 1
        _build(db, rng, used, s, p, now - timedelta(minutes=rng.randint(1, 35)), WAITING)

    db.commit()
    priors = suggest_client.priors(db)
    for code, pid, pref, dur in learned:
        suggest_client.learn(code, pid, pref, dur, priors.get(code))
    return f"{len(learned)} atendidos, 4 cancelados/no presentados, 14 en espera"


if __name__ == "__main__":
    from ..core.database import SessionLocal

    with SessionLocal() as db:
        print(seed_history(db, force=True))
