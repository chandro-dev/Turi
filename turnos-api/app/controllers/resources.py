"""CONTROLADOR - administracion de recursos (supervisor): puntos de atencion, personal y horarios."""
from datetime import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import require
from ..models import User
from ..services import resource_service
from ..services.availability import WEEKDAY_NAMES
from ..views import presenters
from ..views.schemas import PointCreateIn, PointPatchIn, ShiftIn, StaffCreateIn, StaffPatchIn

router = APIRouter(prefix="/api/admin", tags=["recursos"])
SUPERVISOR = require("SUPERVISOR")


def _t(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    from sqlalchemy import select

    from ..models import Service

    return {
        "points": [presenters.admin_point(d) for d in resource_service.list_points(db)],
        "staff": [presenters.admin_staff(d) for d in resource_service.list_staff(db)],
        "services": [{"code": s.code, "name": s.name, "color": s.color} for s in db.execute(select(Service).order_by(Service.id)).scalars().all()],
        "weekdays": WEEKDAY_NAMES,
    }


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


@router.post("/staff", status_code=201)
def create_staff(body: StaffCreateIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    u = resource_service.create_staff(db, body.name, body.username, body.password)
    return {"id": u.id, "name": u.name, "username": u.username}


@router.patch("/staff/{user_id}")
def patch_staff(user_id: int, body: StaffPatchIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    u = resource_service.update_staff(db, user_id, body.model_dump(exclude_unset=True, exclude_none=True))
    return {"id": u.id, "name": u.name}


@router.delete("/staff/{user_id}", status_code=204)
def delete_staff(user_id: int, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    resource_service.delete_staff(db, user_id)


@router.post("/shifts", status_code=201)
def create_shift(body: ShiftIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    return presenters.shift(resource_service.create_shift(db, body.user_id, body.point_id, body.weekdays, _t(body.start), _t(body.end)))


@router.delete("/shifts/{shift_id}", status_code=204)
def delete_shift(shift_id: int, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    resource_service.delete_shift(db, shift_id)
