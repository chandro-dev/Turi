"""CONTROLADOR - atencion (personal medico): llamar, iniciar, no presentado, finalizar."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import require
from ..models import User
from ..services import turn_service
from ..views import presenters
from ..views.schemas import ActiveIn

router = APIRouter(prefix="/api/doctor", tags=["atencion"])
DOCTOR = require("MEDICO")


@router.get("/panel")
def panel(db: Session = Depends(get_db), user: User = Depends(DOCTOR)):
    return presenters.doctor_panel(turn_service.doctor_panel(db, user))


@router.post("/active")
def active(body: ActiveIn, db: Session = Depends(get_db), user: User = Depends(DOCTOR)):
    return {"active": turn_service.set_point_active(db, user, body.active)}


@router.post("/call-next")
def call_next(db: Session = Depends(get_db), user: User = Depends(DOCTOR)):
    return presenters.turn(turn_service.call_next(db, user))


@router.post("/turns/{turn_id}/recall")
def recall(turn_id: int, db: Session = Depends(get_db), user: User = Depends(DOCTOR)):
    return presenters.turn(turn_service.recall(db, user, turn_id))


@router.post("/turns/{turn_id}/start")
def start(turn_id: int, db: Session = Depends(get_db), user: User = Depends(DOCTOR)):
    return presenters.turn(turn_service.start(db, user, turn_id))


@router.post("/turns/{turn_id}/no-show")
def no_show(turn_id: int, db: Session = Depends(get_db), user: User = Depends(DOCTOR)):
    return presenters.turn(turn_service.no_show(db, user, turn_id))


@router.post("/turns/{turn_id}/finish")
def finish(turn_id: int, db: Session = Depends(get_db), user: User = Depends(DOCTOR)):
    return presenters.turn(turn_service.finish(db, user, turn_id))
