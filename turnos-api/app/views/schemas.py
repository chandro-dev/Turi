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


class ModelPredictIn(BaseModel):
    service_code: str
    preferential: bool = False
    point_id: int | None = None


# ------------------------------------------------------------ administracion de recursos
class PointCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    service_codes: list[str] = Field(min_length=1)
    enabled: bool = True


class PointPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    service_codes: list[str] | None = Field(default=None, min_length=1)
    enabled: bool | None = None


class UserCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=6, max_length=100)
    role: str = Field(pattern=r"^(RECEPCION|MEDICO|SUPERVISOR)$")


class UserPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    password: str | None = Field(default=None, min_length=6, max_length=100)
    role: str | None = Field(default=None, pattern=r"^(RECEPCION|MEDICO|SUPERVISOR)$")
    active: bool | None = None


class ServiceCreateIn(BaseModel):
    code: str = Field(min_length=2, max_length=8)
    name: str = Field(min_length=2, max_length=80)
    prior_minutes: float = Field(ge=1, le=240)
    color: str = Field(default="#0d9488", pattern=r"^#[0-9a-fA-F]{6}$")


class ServicePatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    prior_minutes: float | None = Field(default=None, ge=1, le=240)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class ShiftIn(BaseModel):
    user_id: int
    point_id: int
    weekdays: list[int] = Field(min_length=1, max_length=7)
    start: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
