"""Retira las cuentas de demostracion (para pasar un despliegue a uso real).

    docker compose exec turnos-api python -m app.seeds.demo_users purge

Exige que exista al menos otro supervisor activo (por ejemplo el creado con BOOTSTRAP_ADMIN_USER) para no
dejar el sistema sin acceso. Elimina tambien los horarios de esas cuentas. No borra turnos ni historial.
"""
import sys

from sqlalchemy import select

from ..core.database import SessionLocal
from ..models import Shift, User
from .catalog import USERS

DEMO_USERNAMES = [u[0] for u in USERS]


def purge(db) -> list[str]:
    others = db.execute(
        select(User).where(User.role == "SUPERVISOR", User.active.is_(True), User.username.notin_(DEMO_USERNAMES))
    ).scalars().all()
    if not others:
        raise SystemExit("Abortado: no hay otro supervisor activo. Define BOOTSTRAP_ADMIN_USER/BOOTSTRAP_ADMIN_PASSWORD primero.")
    users = db.execute(select(User).where(User.username.in_(DEMO_USERNAMES))).scalars().all()
    names = [u.username for u in users]
    for u in users:
        db.execute(Shift.__table__.delete().where(Shift.user_id == u.id))
        db.delete(u)
    db.commit()
    return names


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "purge":
        raise SystemExit("uso: python -m app.seeds.demo_users purge")
    with SessionLocal() as session:
        removed = purge(session)
    print(f"Cuentas de demostracion eliminadas: {', '.join(removed) or 'ninguna'}")
