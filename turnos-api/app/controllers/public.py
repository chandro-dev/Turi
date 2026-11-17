"""CONTROLADOR - endpoints publicos (sin sesion): salud, pantalla de espera y consulta del paciente."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services import report_service
from ..views import presenters

router = APIRouter(prefix="/api", tags=["publico"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@router.get("/public/display")
def display(db: Session = Depends(get_db)):
    return presenters.display(report_service.display(db))


@router.get("/public/lookup")
def lookup(q: str = Query(min_length=3, max_length=30), db: Session = Depends(get_db)):
    t, est = report_service.lookup(db, q)
    return presenters.turn(t, est, public=True)
