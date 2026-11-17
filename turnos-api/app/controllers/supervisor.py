"""CONTROLADOR - supervision: indicadores y simulador de llegadas."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import require
from ..models import User
from ..services import report_service
from ..views.schemas import SimulateIn

router = APIRouter(prefix="/api", tags=["supervision"])
SUPERVISOR = require("SUPERVISOR")


@router.get("/stats")
def stats(db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    return report_service.stats(db)


@router.post("/demo/simulate")
def simulate(body: SimulateIn, db: Session = Depends(get_db), user: User = Depends(SUPERVISOR)):
    return {"created": report_service.simulate(db, body.count, user.username)}
