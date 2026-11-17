"""CONTROLADOR - recepcion: registrar, editar, cancelar y reasignar turnos."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import require
from ..models import Point, User
from ..services import suggest_client, turn_service
from ..views import presenters
from ..views.schemas import NewTurnIn, PatchTurnIn, PreviewIn, ReassignIn

router = APIRouter(prefix="/api/turns", tags=["turnos"])
RECEPTION = require("RECEPCION", "SUPERVISOR")
READERS = require("RECEPCION", "SUPERVISOR", "MEDICO")


@router.post("/suggest")
def preview(body: PreviewIn, db: Session = Depends(get_db), _: User = Depends(RECEPTION)):
    return turn_service.preview(db, body.service_code, body.age, body.pregnant, body.disability)


@router.post("", status_code=201)
def create(body: NewTurnIn, db: Session = Depends(get_db), user: User = Depends(require("RECEPCION"))):
    t, model = turn_service.create_turn(db, body.model_dump(), user.username)
    out = presenters.turn(t, suggest_client.estimate_point(db, t.point).get(t.id))
    out["model"] = model
    return out


@router.get("")
def list_turns(include_closed: bool = False, db: Session = Depends(get_db), _: User = Depends(READERS)):
    turns = turn_service.list_turns(db, include_closed)
    est = suggest_client.estimates_for(db, list(db.execute(select(Point)).scalars().all()))
    return [presenters.turn(t, est.get(t.id)) for t in turns]


@router.patch("/{turn_id}")
def patch(turn_id: int, body: PatchTurnIn, db: Session = Depends(get_db), user: User = Depends(RECEPTION)):
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None or k == "phone"}
    return presenters.turn(turn_service.patch_turn(db, turn_id, changes, user.username))


@router.post("/{turn_id}/cancel")
def cancel(turn_id: int, db: Session = Depends(get_db), user: User = Depends(RECEPTION)):
    return presenters.turn(turn_service.cancel_turn(db, turn_id, user.username))


@router.post("/{turn_id}/reassign")
def reassign(turn_id: int, body: ReassignIn, db: Session = Depends(get_db), user: User = Depends(RECEPTION)):
    return presenters.turn(turn_service.reassign_turn(db, turn_id, body.point_id, user.username))
