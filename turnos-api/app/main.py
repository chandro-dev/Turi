import random
from collections import Counter as Cnt
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import logic
from .config import SEED_DEMO, TZ
from .db import SessionLocal, get_db, init_db
from .models import (
    ACTIVE_STATUSES,
    BAJA,
    CALLED,
    CANCELLED,
    DONE,
    IN_SERVICE,
    NO_SHOW,
    NORMAL,
    PREFERENCIAL,
    WAITING,
    Base,
    Point,
    Service,
    Turn,
    TurnEvent,
    User,
)
from .security import current_user, make_token, require, verify_password
from .demo_data import seed_history
from .seed import seed_catalog, seed_users


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db(Base)
    with SessionLocal() as db:
        seed_catalog(db)
        if SEED_DEMO:
            seed_users(db)
            try:
                logic.log.info("seed: %s", seed_history(db))
            except Exception:  # noqa: BLE001
                logic.log.exception("seed de historial fallo")
                db.rollback()
    yield


app = FastAPI(title="Turi - API de turnos", version="1.0.0", lifespan=lifespan, root_path="")
R = require("RECEPCION", "SUPERVISOR")
M = require("MEDICO")
S = require("SUPERVISOR")
ANY = Depends(current_user)


# ------------------------------------------------------------------ schemas
class LoginIn(BaseModel):
    username: str
    password: str


class PatientIn(BaseModel):
    doc_number: str = Field(min_length=3, max_length=30)
    patient_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    age: int = Field(ge=0, le=120)
    pregnant: bool = False
    disability: bool = False


class NewTurnIn(PatientIn):
    service_code: str
    point_id: int | None = None


class PreviewIn(BaseModel):
    service_code: str
    age: int = Field(ge=0, le=120)
    pregnant: bool = False
    disability: bool = False


class PatchTurnIn(BaseModel):
    doc_number: str | None = Field(default=None, min_length=3, max_length=30)
    patient_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    pregnant: bool | None = None
    disability: bool | None = None


class ReassignIn(BaseModel):
    point_id: int


class ActiveIn(BaseModel):
    active: bool


class SimulateIn(BaseModel):
    count: int = Field(default=8, ge=1, le=40)


# ------------------------------------------------------------------ helpers
def iso(d: datetime | None) -> str | None:
    return d.astimezone(TZ).isoformat() if d else None


def mask_name(name: str) -> str:
    parts = name.split()
    return parts[0] + (f" {parts[1][0]}." if len(parts) > 1 else "")


def turn_out(t: Turn, est: dict | None = None, public: bool = False) -> dict:
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
        "no_show_count": t.no_show_count,
        "reassign_count": t.reassign_count,
    }
    if public:
        out["patient_name"] = mask_name(t.patient_name)
    else:
        out.update(
            patient_name=t.patient_name,
            doc_number=t.doc_number,
            phone=t.phone,
            age=t.age,
            pregnant=t.pregnant,
            disability=t.disability,
        )
    return out


def estimates_for(db: Session, points: list[Point]) -> dict[int, dict]:
    est: dict[int, dict] = {}
    for p in points:
        est.update(logic.estimate_point(db, p))
    return est


def get_service(db: Session, code: str) -> Service:
    s = db.execute(select(Service).where(Service.code == code)).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Servicio no existe")
    return s


def get_turn(db: Session, turn_id: int) -> Turn:
    t = db.get(Turn, turn_id)
    if not t:
        raise HTTPException(404, "Turno no existe")
    return t


def create_turn(db: Session, data: NewTurnIn, username: str) -> tuple[Turn, str]:
    service = get_service(db, data.service_code)
    dup = db.execute(
        select(Turn).where(
            Turn.doc_number == data.doc_number.strip(), Turn.day == logic.today(), Turn.status.in_(ACTIVE_STATUSES)
        )
    ).scalars().first()
    if dup:
        raise HTTPException(409, f"El paciente ya tiene un turno activo: {dup.code} ({dup.point.name})")
    cls, reasons = logic.classify(data.age, data.pregnant, data.disability)
    options, model = logic.suggest_points(db, service, cls)
    if data.point_id is None:
        if not options:
            raise HTTPException(409, "No hay puntos de atencion disponibles para este servicio")
        point_id = options[0]["point_id"]
    else:
        point_id = data.point_id
    point = db.get(Point, point_id)
    if not point or service.code not in [s.code for s in point.services]:
        raise HTTPException(400, "El punto no atiende este servicio")
    chosen = next((o for o in options if o["point_id"] == point_id), None)
    code, day = logic.next_code(db, service)
    t = Turn(
        code=code,
        day=day,
        service_id=service.id,
        point_id=point.id,
        doc_number=data.doc_number.strip(),
        patient_name=data.patient_name.strip(),
        phone=(data.phone or "").strip() or None,
        age=data.age,
        pregnant=data.pregnant,
        disability=data.disability,
        priority_class=cls,
        priority_reasons=",".join(reasons),
        status=WAITING,
        initial_wait_est=chosen["est_wait_min"] if chosen else None,
        created_by=username,
    )
    db.add(t)
    db.flush()
    suggested = options[0]["name"] if options else "-"
    logic.add_event(db, t, "CREATED", f"Asignado a {point.name} (sugerido: {suggested}; modelo: {model})", username)
    db.commit()
    db.refresh(t)
    return t, model


# ------------------------------------------------------------------ public
@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.execute(select(User).where(User.username == body.username.strip().lower())).scalar_one_or_none()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Usuario o contrasena incorrectos")
    return {"token": make_token(u), "user": user_out(u)}


def user_out(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "name": u.name,
        "role": u.role,
        "point": {"id": u.point.id, "name": u.point.name} if u.point else None,
    }


@app.get("/api/auth/me")
def me(u: User = ANY):
    return user_out(u)


@app.get("/api/public/display")
def public_display(db: Session = Depends(get_db)):
    day = logic.today()
    called = db.execute(
        select(Turn)
        .where(Turn.day == day, Turn.status.in_([CALLED, IN_SERVICE]))
        .order_by(Turn.called_at.desc())
    ).scalars().all()
    points = db.execute(select(Point).order_by(Point.id)).scalars().all()
    waiting = Cnt(
        t.point_id for t in db.execute(select(Turn).where(Turn.day == day, Turn.status == WAITING)).scalars().all()
    )
    return {
        "calls": [
            {
                "code": t.code,
                "point": t.point.name,
                "status": t.status,
                "called_at": iso(t.called_at),
                "preferential": t.priority_class == PREFERENCIAL,
                "color": t.service.color,
            }
            for t in called
        ],
        "points": [{"name": p.name, "active": p.active, "waiting": waiting.get(p.id, 0)} for p in points],
    }


@app.get("/api/public/lookup")
def public_lookup(q: str = Query(min_length=3, max_length=30), db: Session = Depends(get_db)):
    q = q.strip()
    day = logic.today()
    t = db.execute(
        select(Turn)
        .where(Turn.day == day, or_(Turn.code == q.upper(), Turn.doc_number == q))
        .order_by(Turn.id.desc())
    ).scalars().first()
    if not t:
        raise HTTPException(404, "No encontramos un turno de hoy con ese dato")
    est = logic.estimate_point(db, t.point) if t.status == WAITING else {}
    return turn_out(t, est.get(t.id), public=True)


# ------------------------------------------------------------------ catalog
@app.get("/api/services")
def list_services(db: Session = Depends(get_db), _: User = ANY):
    return [
        {"id": s.id, "code": s.code, "name": s.name, "color": s.color, "prior_minutes": s.prior_minutes}
        for s in db.execute(select(Service).order_by(Service.id)).scalars().all()
    ]


@app.get("/api/points")
def list_points(db: Session = Depends(get_db), _: User = ANY):
    day = logic.today()
    active = db.execute(select(Turn).where(Turn.day == day, Turn.status.in_(ACTIVE_STATUSES))).scalars().all()
    waiting = Cnt(t.point_id for t in active if t.status == WAITING)
    busy = {t.point_id for t in active if t.status in (CALLED, IN_SERVICE)}
    return [
        {
            "id": p.id,
            "name": p.name,
            "active": p.active,
            "services": [s.code for s in p.services],
            "waiting": waiting.get(p.id, 0),
            "busy": p.id in busy,
        }
        for p in db.execute(select(Point).order_by(Point.id)).scalars().all()
    ]


# ------------------------------------------------------------------ reception
@app.post("/api/turns/suggest")
def preview(body: PreviewIn, db: Session = Depends(get_db), _: User = Depends(R)):
    service = get_service(db, body.service_code)
    cls, reasons = logic.classify(body.age, body.pregnant, body.disability)
    options, model = logic.suggest_points(db, service, cls)
    return {"priority_class": cls, "priority_reasons": reasons, "options": options, "model": model}


@app.post("/api/turns", status_code=201)
def new_turn(body: NewTurnIn, db: Session = Depends(get_db), user: User = Depends(R)):
    t, model = create_turn(db, body, user.username)
    est = logic.estimate_point(db, t.point).get(t.id)
    out = turn_out(t, est)
    out["model"] = model
    return out


@app.get("/api/turns")
def list_turns(
    include_closed: bool = False, db: Session = Depends(get_db), user: User = Depends(require("RECEPCION", "SUPERVISOR", "MEDICO"))
):
    statuses = None if include_closed else ACTIVE_STATUSES
    q = select(Turn).where(Turn.day == logic.today())
    if statuses:
        q = q.where(Turn.status.in_(statuses))
    turns = db.execute(q.order_by(Turn.created_at)).scalars().all()
    est = estimates_for(db, db.execute(select(Point)).scalars().all())
    return [turn_out(t, est.get(t.id)) for t in turns]


@app.patch("/api/turns/{turn_id}")
def patch_turn(turn_id: int, body: PatchTurnIn, db: Session = Depends(get_db), user: User = Depends(R)):
    t = get_turn(db, turn_id)
    if t.status not in (WAITING, NO_SHOW):
        raise HTTPException(409, "Solo se pueden editar turnos en espera o no presentados")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "phone":
            v = (v or "").strip() or None
        elif isinstance(v, str):
            v = v.strip()
        setattr(t, k, v)
    if t.priority_class != BAJA:
        cls, reasons = logic.classify(t.age, t.pregnant, t.disability)
        t.priority_class, t.priority_reasons = cls, ",".join(reasons)
    else:
        _, reasons = logic.classify(t.age, t.pregnant, t.disability)
        t.priority_reasons = ",".join(reasons)
    logic.add_event(db, t, "EDITED", ", ".join(data.keys()), user.username)
    db.commit()
    return turn_out(t)


@app.post("/api/turns/{turn_id}/cancel")
def cancel_turn(turn_id: int, db: Session = Depends(get_db), user: User = Depends(R)):
    t = get_turn(db, turn_id)
    if t.status not in (WAITING, NO_SHOW, CALLED):
        raise HTTPException(409, "El turno no se puede cancelar en su estado actual")
    t.status = CANCELLED
    t.finished_at = logic.now()
    logic.add_event(db, t, "CANCELLED", "", user.username)
    db.commit()
    return turn_out(t)


@app.post("/api/turns/{turn_id}/reassign")
def reassign_turn(turn_id: int, body: ReassignIn, db: Session = Depends(get_db), user: User = Depends(R)):
    t = get_turn(db, turn_id)
    if t.status not in (WAITING, NO_SHOW):
        raise HTTPException(409, "Solo se reasignan turnos en espera o no presentados")
    p = db.get(Point, body.point_id)
    if not p or t.service.code not in [s.code for s in p.services]:
        raise HTTPException(400, "El punto no atiende este servicio")
    detail = f"{t.point.name} -> {p.name}"
    if t.status == NO_SHOW:
        # reincorporacion: conserva la identidad, pasa a prioridad baja
        t.status = WAITING
        t.priority_class = BAJA
        t.queued_at = logic.now()
        logic.add_event(db, t, "REQUEUED", f"Reincorporado en prioridad baja: {detail}", user.username)
    else:
        logic.add_event(db, t, "REASSIGNED", detail, user.username)
    if p.id != t.point_id:
        t.reassign_count += 1
    t.point_id = p.id
    db.commit()
    db.refresh(t)
    return turn_out(t)


# ------------------------------------------------------------------ doctor
def doctor_point(user: User) -> Point:
    if not user.point:
        raise HTTPException(400, "Tu usuario no tiene punto de atencion asignado")
    return user.point


def own_turn(db: Session, user: User, turn_id: int, *statuses: str) -> Turn:
    t = get_turn(db, turn_id)
    if t.point_id != doctor_point(user).id:
        raise HTTPException(403, "El turno pertenece a otro punto de atencion")
    if t.status not in statuses:
        raise HTTPException(409, f"Accion no valida: el turno esta en estado {t.status}")
    return t


@app.get("/api/doctor/panel")
def doctor_panel(db: Session = Depends(get_db), user: User = Depends(M)):
    p = doctor_point(user)
    db.refresh(p)
    cur = logic.current_turn(db, p.id)
    est = logic.estimate_point(db, p)
    queue = logic.waiting_turns(db, p.id)
    no_shows = db.execute(
        select(Turn).where(Turn.point_id == p.id, Turn.day == logic.today(), Turn.status == NO_SHOW)
    ).scalars().all()
    done = db.execute(
        select(Turn).where(Turn.point_id == p.id, Turn.day == logic.today(), Turn.status == DONE)
    ).scalars().all()
    return {
        "point": {"id": p.id, "name": p.name, "active": p.active, "services": [s.name for s in p.services]},
        "current": turn_out(cur) if cur else None,
        "queue": [turn_out(t, est.get(t.id)) for t in queue],
        "no_shows": [turn_out(t) for t in no_shows],
        "done_today": len(done),
    }


@app.post("/api/doctor/active")
def doctor_active(body: ActiveIn, db: Session = Depends(get_db), user: User = Depends(M)):
    p = db.get(Point, doctor_point(user).id)
    p.active = body.active
    db.commit()
    return {"active": p.active}


@app.post("/api/doctor/call-next")
def call_next(db: Session = Depends(get_db), user: User = Depends(M)):
    p = doctor_point(user)
    if logic.current_turn(db, p.id):
        raise HTTPException(409, "Ya hay un paciente llamado o en atencion. Finaliza ese turno primero")
    queue = logic.waiting_turns(db, p.id)
    if not queue:
        raise HTTPException(404, "No hay pacientes en espera")
    t = queue[0]
    t.status = CALLED
    t.called_at = logic.now()
    logic.add_event(db, t, "CALLED", p.name, user.username)
    db.commit()
    return turn_out(t)


@app.post("/api/doctor/turns/{turn_id}/recall")
def recall(turn_id: int, db: Session = Depends(get_db), user: User = Depends(M)):
    t = own_turn(db, user, turn_id, CALLED)
    t.called_at = logic.now()
    logic.add_event(db, t, "RECALLED", "", user.username)
    db.commit()
    return turn_out(t)


@app.post("/api/doctor/turns/{turn_id}/start")
def start(turn_id: int, db: Session = Depends(get_db), user: User = Depends(M)):
    t = own_turn(db, user, turn_id, CALLED)
    t.status = IN_SERVICE
    t.started_at = logic.now()
    logic.add_event(db, t, "STARTED", "", user.username)
    db.commit()
    return turn_out(t)


@app.post("/api/doctor/turns/{turn_id}/no-show")
def no_show(turn_id: int, db: Session = Depends(get_db), user: User = Depends(M)):
    t = own_turn(db, user, turn_id, CALLED)
    t.status = NO_SHOW
    t.no_show_count += 1
    logic.add_event(db, t, "NO_SHOW", f"Intento {t.no_show_count}", user.username)
    db.commit()
    return turn_out(t)


@app.post("/api/doctor/turns/{turn_id}/finish")
def finish(turn_id: int, db: Session = Depends(get_db), user: User = Depends(M)):
    t = own_turn(db, user, turn_id, IN_SERVICE)
    t.status = DONE
    t.finished_at = logic.now()
    minutes = (t.finished_at - t.started_at).total_seconds() / 60
    logic.add_event(db, t, "FINISHED", f"{minutes:.1f} min", user.username)
    db.commit()
    logic.learn(t.service.code, t.point_id, t.priority_class == PREFERENCIAL, minutes)
    return turn_out(t)


# ------------------------------------------------------------------ supervisor
@app.get("/api/stats")
def stats(db: Session = Depends(get_db), _: User = Depends(S)):
    day = logic.today()
    turns = db.execute(select(Turn).where(Turn.day == day)).scalars().all()
    points = db.execute(select(Point).order_by(Point.id)).scalars().all()

    def mins(a, b):
        return (b - a).total_seconds() / 60

    waits = [mins(t.created_at, t.called_at) for t in turns if t.called_at]
    durs = [mins(t.started_at, t.finished_at) for t in turns if t.status == DONE and t.started_at and t.finished_at]
    by_status = Cnt(t.status for t in turns)
    hourly = Cnt(t.created_at.astimezone(TZ).hour for t in turns)

    per_point = []
    for p in points:
        pt = [t for t in turns if t.point_id == p.id]
        pd = [mins(t.started_at, t.finished_at) for t in pt if t.status == DONE and t.started_at and t.finished_at]
        per_point.append(
            {
                "id": p.id,
                "name": p.name,
                "active": p.active,
                "waiting": sum(t.status == WAITING for t in pt),
                "in_attention": sum(t.status in (CALLED, IN_SERVICE) for t in pt),
                "done": sum(t.status == DONE for t in pt),
                "no_show": sum(t.status == NO_SHOW for t in pt),
                "avg_service_min": round(sum(pd) / len(pd), 1) if pd else None,
            }
        )
    per_service = [
        {
            "code": s.code,
            "name": s.name,
            "color": s.color,
            "total": sum(t.service_id == s.id for t in turns),
            "done": sum(t.service_id == s.id and t.status == DONE for t in turns),
        }
        for s in db.execute(select(Service).order_by(Service.id)).scalars().all()
    ]
    prio = [t for t in turns if t.priority_class == PREFERENCIAL or t.priority_reasons]
    prio_waits = [mins(t.created_at, t.called_at) for t in prio if t.called_at]
    normal_waits = [mins(t.created_at, t.called_at) for t in turns if t.called_at and t not in prio]
    avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None  # noqa: E731
    return {
        "total": len(turns),
        "by_status": dict(by_status),
        "avg_wait_min": avg(waits),
        "avg_service_min": avg(durs),
        "priority": {
            "total": len(prio),
            "avg_wait_min": avg(prio_waits),
            "avg_wait_normal_min": avg(normal_waits),
            "reasons": dict(Cnt(r for t in prio for r in t.priority_reasons.split(",") if r)),
        },
        "reassigned": sum(t.reassign_count > 0 for t in turns),
        "no_shows_total": sum(t.no_show_count > 0 for t in turns),
        "per_point": per_point,
        "per_service": per_service,
        "hourly": [{"hour": h, "count": hourly.get(h, 0)} for h in range(6, 21)],
    }


NAMES = ["Maria Lopez", "Juan Perez", "Ana Torres", "Carlos Diaz", "Lucia Fernandez", "Pedro Gomez", "Sofia Ramirez",
         "Jorge Castillo", "Valentina Ruiz", "Miguel Herrera", "Isabel Moreno", "Andres Vargas", "Rosa Mendoza",
         "Camilo Ortiz", "Elena Rojas", "Tomas Navarro", "Paula Medina", "Ricardo Suarez"]


@app.post("/api/demo/simulate")
def simulate(body: SimulateIn, db: Session = Depends(get_db), user: User = Depends(S)):
    services = db.execute(select(Service)).scalars().all()
    created = 0
    for _ in range(body.count):
        age = random.choice([random.randint(3, 17), random.randint(18, 59), random.randint(18, 59), random.randint(60, 88)])
        data = NewTurnIn(
            doc_number=str(random.randint(10_000_000, 1_099_999_999)),
            patient_name=random.choice(NAMES),
            age=age,
            pregnant=random.random() < 0.08,
            disability=random.random() < 0.07,
            service_code=random.choices(services, weights=[5, 3, 3, 2])[0].code,
        )
        try:
            create_turn(db, data, user.username)
            created += 1
        except HTTPException:
            db.rollback()
    return {"created": created}
