"""CONTROLADOR - administracion (supervisor): servicios, puntos de atencion, usuarios y horarios."""
from datetime import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import require
from ..models import Service, User
from ..services import resource_service
from ..services.availability import WEEKDAY_NAMES
from ..views import presenters
from ..views.schemas import (
    PointCreateIn, PointPatchIn, ServiceCreateIn, ServicePatchIn, ShiftIn, UserCreateIn, UserPatchIn,
)

router = APIRouter(prefix="/api/admin", tags=["administracion"])
SUPERVISOR = require("SUPERVISOR")


def _t(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    return {
        "points": [presenters.admin_point(d) for d in resource_service.list_points(db)],
        "users": [presenters.admin_user(d) for d in resource_service.list_users(db)],
        "services": [presenters.admin_service(s) for s in db.execute(select(Service).order_by(Service.id)).scalars().all()],
        "weekdays": WEEKDAY_NAMES,
    }


# ---- servicios
@router.post("/services", status_code=201)
def create_service(body: ServiceCreateIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    return presenters.admin_service(resource_service.create_service(db, body.code, body.name, body.prior_minutes, body.color))


@router.patch("/services/{service_id}")
def patch_service(service_id: int, body: ServicePatchIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    return presenters.admin_service(resource_service.update_service(db, service_id, body.model_dump(exclude_unset=True, exclude_none=True)))


@router.delete("/services/{service_id}", status_code=204)
def delete_service(service_id: int, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    resource_service.delete_service(db, service_id)


# ---- puntos
@router.post("/points", status_code=201)
def create_point(body: PointCreateIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    p = resource_service.create_point(db, body.name, body.service_codes, body.enabled)
    return {"id": p.id, "name": p.name}


@router.patch("/points/{point_id}")
def patch_point(point_id: int, body: PointPatchIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    p = resource_service.update_point(db, point_id, body.model_dump(exclude_unset=True, exclude_none=True))
    return {"id": p.id, "name": p.name, "enabled": p.enabled}


@router.delete("/points/{point_id}", status_code=204)
def delete_point(point_id: int, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    resource_service.delete_point(db, point_id)


# ---- usuarios (todos los roles)
@router.post("/users", status_code=201)
def create_user(body: UserCreateIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    u = resource_service.create_user(db, body.name, body.username, body.password, body.role)
    return {"id": u.id, "name": u.name, "username": u.username, "role": u.role}


@router.patch("/users/{user_id}")
def patch_user(user_id: int, body: UserPatchIn, db: Session = Depends(get_db), actor: User = Depends(SUPERVISOR)):
    u = resource_service.update_user(db, actor, user_id, body.model_dump(exclude_unset=True, exclude_none=True))
    return {"id": u.id, "name": u.name, "role": u.role, "active": u.active}


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(SUPERVISOR)):
    resource_service.delete_user(db, actor, user_id)


# ---- horarios
@router.post("/shifts", status_code=201)
def create_shift(body: ShiftIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    return presenters.shift(resource_service.create_shift(db, body.user_id, body.point_id, body.weekdays, _t(body.start), _t(body.end)))


@router.delete("/shifts/{shift_id}", status_code=204)
def delete_shift(shift_id: int, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    resource_service.delete_shift(db, shift_id)
