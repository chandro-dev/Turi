"""Orden de la fila con prioridad otorgada por el modelo (sin base de datos)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.models import BAJA, NORMAL, PREFERENCIAL
from app.services import queueing

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)


def turn(cls, minutes_after, bonus=None):
    return SimpleNamespace(priority_class=cls, queued_at=T0 + timedelta(minutes=minutes_after), bonus_min=bonus)


def test_default_bonus_moves_preferential_ahead_of_normal():
    normal = turn(NORMAL, 0)
    pref = turn(PREFERENCIAL, 15)                  # llego 15 min despues, bonus por defecto 20
    assert queueing.turn_key(pref) < queueing.turn_key(normal)


def test_model_bonus_overrides_default():
    pref_default = turn(PREFERENCIAL, 30)          # 30 > 20: queda detras del normal
    pref_model = turn(PREFERENCIAL, 30, bonus=45)  # el modelo le otorgo 45 min
    normal = turn(NORMAL, 0)
    assert queueing.turn_key(pref_default) > queueing.turn_key(normal)
    assert queueing.turn_key(pref_model) < queueing.turn_key(normal)


def test_requeued_patient_ignores_bonus_and_yields():
    low = turn(BAJA, 0, bonus=60)                  # el bonus no aplica a reincorporados
    normal = turn(NORMAL, 5)
    assert queueing.turn_key(low) > queueing.turn_key(normal)


def test_normal_ignores_bonus_field():
    assert queueing.turn_key(turn(NORMAL, 0, bonus=50)) == queueing.turn_key(turn(NORMAL, 0))
