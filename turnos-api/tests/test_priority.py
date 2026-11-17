"""Reglas de prioridad y validacion de edad (sin base de datos)."""
import pytest
from pydantic import ValidationError

from app.models import NORMAL, PREFERENCIAL
from app.services import priority
from app.views.schemas import NewTurnIn, PatchTurnIn, PreviewIn


def base(**kw):
    d = dict(doc_number="123456", patient_name="Ana Perez", age=30, service_code="CG")
    d.update(kw)
    return d


@pytest.mark.parametrize("age", [0, 1, 5, 9])
def test_pregnant_rejected_below_min_age(age):
    with pytest.raises(ValidationError) as e:
        NewTurnIn(**base(age=age, pregnant=True))
    assert "gestante" in str(e.value)


@pytest.mark.parametrize("age", [56, 70, 120])
def test_pregnant_rejected_above_max_age(age):
    with pytest.raises(ValidationError):
        PreviewIn(service_code="CG", age=age, pregnant=True)


@pytest.mark.parametrize("age", [10, 25, 55])
def test_pregnant_accepted_in_range(age):
    assert NewTurnIn(**base(age=age, pregnant=True)).pregnant is True


def test_age_bounds():
    for bad in (-1, 121):
        with pytest.raises(ValidationError):
            NewTurnIn(**base(age=bad))


def test_children_without_pregnancy_are_valid_and_normal():
    assert NewTurnIn(**base(age=3)).age == 3
    assert priority.classify(3, False, False) == (NORMAL, [])


def test_classification():
    assert priority.classify(60, False, False) == (PREFERENCIAL, ["Adulto mayor"])
    assert priority.classify(30, True, True) == (PREFERENCIAL, ["Gestante", "Discapacidad"])
    assert priority.classify(59, False, False)[0] == NORMAL


def test_service_layer_rejects_invalid_combination():
    with pytest.raises(priority.PatientRuleError):
        priority.classify(8, True, False)


def test_patch_allows_partial_without_age():
    assert PatchTurnIn(pregnant=True).pregnant is True  # la combinacion final se valida en el servicio
