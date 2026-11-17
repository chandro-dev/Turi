"""CONTROLADOR - prueba del modelo de IA (solo supervision)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import require
from ..models import User
from ..services import model_service
from ..views.schemas import ModelPredictIn

router = APIRouter(prefix="/api/model", tags=["modelo"])
SUPERVISOR = require("SUPERVISOR")


@router.get("/report")
def report(db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    return model_service.report(db)


@router.post("/retrain")
def retrain(_: User = Depends(SUPERVISOR)):
    return model_service.retrain()


@router.post("/predict")
def predict(body: ModelPredictIn, db: Session = Depends(get_db), _: User = Depends(SUPERVISOR)):
    return model_service.predict(db, body.service_code, body.preferential, body.point_id)
