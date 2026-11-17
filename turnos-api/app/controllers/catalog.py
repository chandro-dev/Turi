"""CONTROLADOR - catalogos: servicios y puntos de atencion."""
from collections import Counter as Cnt

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import current_user
from ..models import ACTIVE_STATUSES, CALLED, IN_SERVICE, WAITING, Point, Service, Turn, User
from ..services import availability, queueing
from ..views import presenters

router = APIRouter(prefix="/api", tags=["catalogo"])


@router.get("/services")
def list_services(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [
        {"id": s.id, "code": s.code, "name": s.name, "color": s.color, "prior_minutes": s.prior_minutes}
        for s in db.execute(select(Service).order_by(Service.id)).scalars().all()
    ]


@router.get("/points")
def list_points(db: Session = Depends(get_db), _: User = Depends(current_user)):
    active = db.execute(
        select(Turn).where(Turn.day == queueing.today(), Turn.status.in_(ACTIVE_STATUSES))
    ).scalars().all()
    waiting = Cnt(t.point_id for t in active if t.status == WAITING)
    busy = {t.point_id for t in active if t.status in (CALLED, IN_SERVICE)}
    shifts = availability.load_shifts(db)
    return [
        presenters.point_row(p, waiting.get(p.id, 0), p.id in busy, availability.point_status(p, shifts))
        for p in db.execute(select(Point).order_by(Point.id)).scalars().all()
        if p.enabled
    ]
