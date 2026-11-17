"""Horarios y disponibilidad de puntos (sin base de datos)."""
from datetime import datetime, time
from types import SimpleNamespace

from app.services import availability as av

MON_9 = datetime(2026, 11, 16, 9, 0)    # lunes
MON_14 = datetime(2026, 11, 16, 14, 0)
SAT_9 = datetime(2026, 11, 21, 9, 0)


def point(pid=1, enabled=True, active=True):
    return SimpleNamespace(id=pid, enabled=enabled, active=active)


def shift(user_id=1, point_id=1, days=(0, 1, 2, 3, 4), start=time(7, 0), end=time(13, 0), point_name="C1"):
    return SimpleNamespace(user_id=user_id, point_id=point_id, days=list(days), start_time=start, end_time=end,
                           point=SimpleNamespace(name=point_name))


def test_point_without_shifts_is_always_open():
    assert av.point_status(point(), [], MON_9) == "open"
    assert av.point_status(point(), [], SAT_9) == "open"


def test_closed_overrides_everything():
    assert av.point_status(point(enabled=False), [shift()], MON_9) == "closed"


def test_point_open_only_inside_shift():
    s = [shift()]
    assert av.point_status(point(), s, MON_9) == "open"
    assert av.point_status(point(), s, MON_14) == "off_hours"   # fuera de 07-13
    assert av.point_status(point(), s, SAT_9) == "off_hours"    # sabado no trabaja


def test_shift_end_is_exclusive_and_start_inclusive():
    s = shift()
    assert av.covers(s, datetime(2026, 11, 16, 7, 0))
    assert av.covers(s, datetime(2026, 11, 16, 12, 59))
    assert not av.covers(s, datetime(2026, 11, 16, 13, 0))
    assert not av.covers(s, datetime(2026, 11, 16, 6, 59))


def test_paused_only_when_in_hours():
    assert av.point_status(point(active=False), [], MON_9) == "paused"
    assert av.point_status(point(active=False), [shift()], MON_14) == "off_hours"


def test_another_points_shifts_do_not_affect_this_one():
    assert av.point_status(point(pid=2), [shift(point_id=1)], MON_14) == "open"


def test_next_shift_finds_upcoming_slot():
    u = SimpleNamespace(id=1)
    nxt = av.next_shift(u, [shift()], MON_14)          # lunes 14:00 -> martes 07:00
    assert nxt["weekday"] == "Mar" and nxt["start"] == "07:00" and nxt["point"] == "C1"
    assert av.next_shift(SimpleNamespace(id=99), [shift()], MON_14) is None


def test_overlaps():
    assert av.overlaps(time(7), time(13), time(12), time(15))
    assert not av.overlaps(time(7), time(13), time(13), time(15))
