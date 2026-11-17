from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Point, Service, User
from ..core.security import hash_password

SERVICES = [
    ("CG", "Consulta general", 12, "#0f766e"),
    ("LAB", "Laboratorio", 6, "#7c3aed"),
    ("FAR", "Farmacia", 4, "#d97706"),
    ("ODO", "Odontologia", 20, "#2563eb"),
]

POINTS = [
    ("Consultorio 1", ["CG"]),
    ("Consultorio 2", ["CG"]),
    ("Laboratorio", ["LAB"]),
    ("Farmacia", ["FAR"]),
    ("Odontologia", ["ODO"]),
]

USERS = [
    ("recepcion", "Laura Gomez (Recepcion)", "RECEPCION", "recepcion123", None),
    ("medico1", "Dr. Andres Rojas", "MEDICO", "medico123", "Consultorio 1"),
    ("medico2", "Dra. Camila Pardo", "MEDICO", "medico123", "Consultorio 2"),
    ("laboratorio", "Lic. Sofia Mejia", "MEDICO", "medico123", "Laboratorio"),
    ("farmacia", "Q.F. Daniel Ruiz", "MEDICO", "medico123", "Farmacia"),
    ("odontologia", "Dr. Felipe Castro", "MEDICO", "medico123", "Odontologia"),
    ("supervisor", "Marta Vega (Supervision)", "SUPERVISOR", "supervisor123", None),
]


def seed_catalog(db: Session) -> None:
    if db.execute(select(Service).limit(1)).first():
        return
    by_code = {}
    for code, name, prior, color in SERVICES:
        s = Service(code=code, name=name, prior_minutes=prior, color=color)
        db.add(s)
        by_code[code] = s
    for name, codes in POINTS:
        db.add(Point(name=name, active=True, services=[by_code[c] for c in codes]))
    db.commit()


def seed_users(db: Session) -> None:
    if db.execute(select(User).limit(1)).first():
        return
    points = {p.name: p for p in db.execute(select(Point)).scalars().all()}
    for username, name, role, pwd, point in USERS:
        db.add(
            User(
                username=username,
                name=name,
                role=role,
                password_hash=hash_password(pwd),
                point_id=points[point].id if point else None,
            )
        )
    db.commit()


def ensure_bootstrap_admin(db: Session) -> str | None:
    """Crea el supervisor inicial definido por entorno si aun no existe. Devuelve su usuario si lo creo."""
    from ..core.config import BOOTSTRAP_ADMIN_NAME, BOOTSTRAP_ADMIN_PASSWORD, BOOTSTRAP_ADMIN_USER

    if not BOOTSTRAP_ADMIN_USER or len(BOOTSTRAP_ADMIN_PASSWORD) < 8:
        return None
    if db.execute(select(User).where(User.username == BOOTSTRAP_ADMIN_USER)).scalar_one_or_none():
        return None
    db.add(User(username=BOOTSTRAP_ADMIN_USER, name=BOOTSTRAP_ADMIN_NAME, role="SUPERVISOR",
                password_hash=hash_password(BOOTSTRAP_ADMIN_PASSWORD), active=True))
    db.commit()
    return BOOTSTRAP_ADMIN_USER
