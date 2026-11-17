"""Reglas de prioridad y validacion de datos del paciente (logica de dominio pura, sin I/O)."""
from __future__ import annotations

from ..models import NORMAL, PREFERENCIAL

SENIOR_AGE = 60            # desde esta edad: adulto mayor
PREGNANCY_MIN_AGE = 10     # rango de edad en que se admite "gestante"
PREGNANCY_MAX_AGE = 55
MAX_AGE = 120


class PatientRuleError(ValueError):
    """Dato del paciente incoherente con las reglas del negocio."""


def validate_patient(age: int, pregnant: bool) -> None:
    if not 0 <= age <= MAX_AGE:
        raise PatientRuleError(f"La edad debe estar entre 0 y {MAX_AGE} anos")
    if pregnant and not PREGNANCY_MIN_AGE <= age <= PREGNANCY_MAX_AGE:
        raise PatientRuleError(
            f"No se puede marcar gestante con {age} anos: el rango permitido es {PREGNANCY_MIN_AGE} a {PREGNANCY_MAX_AGE} anos"
        )


def classify(age: int, pregnant: bool, disability: bool) -> tuple[str, list[str]]:
    """Devuelve (clase de prioridad, motivos). Valida antes de clasificar."""
    validate_patient(age, pregnant)
    reasons = []
    if age >= SENIOR_AGE:
        reasons.append("Adulto mayor")
    if pregnant:
        reasons.append("Gestante")
    if disability:
        reasons.append("Discapacidad")
    return (PREFERENCIAL if reasons else NORMAL), reasons
