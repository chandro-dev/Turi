"""VISTA (V) - contratos de entrada de la API (DTO validados con Pydantic)."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from ..services import priority


class LoginIn(BaseModel):
    username: str
    password: str


class _AgeRules(BaseModel):
    age: int = Field(ge=0, le=priority.MAX_AGE)
    pregnant: bool = False

    @model_validator(mode="after")
    def _check_pregnancy_age(self):
        try:
            priority.validate_patient(self.age, self.pregnant)
        except priority.PatientRuleError as e:
            raise ValueError(str(e)) from e
        return self


class PatientIn(_AgeRules):
    doc_number: str = Field(min_length=3, max_length=30)
    patient_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    disability: bool = False


class NewTurnIn(PatientIn):
    service_code: str
    point_id: int | None = None


class PreviewIn(_AgeRules):
    service_code: str
    disability: bool = False


class PatchTurnIn(BaseModel):
    """Edicion parcial. La coherencia edad/gestante se valida en el servicio con el valor final."""

    doc_number: str | None = Field(default=None, min_length=3, max_length=30)
    patient_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None
    age: int | None = Field(default=None, ge=0, le=priority.MAX_AGE)
    pregnant: bool | None = None
    disability: bool | None = None


class ReassignIn(BaseModel):
    point_id: int


class ActiveIn(BaseModel):
    active: bool


class SimulateIn(BaseModel):
    count: int = Field(default=8, ge=1, le=40)
