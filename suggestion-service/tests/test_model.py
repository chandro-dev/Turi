import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

import pytest  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    from app.models import entities  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

PRIOR = {"CG": 10.0}


def point(pid, queue=0, active=True):
    return {
        "id": pid,
        "name": f"P{pid}",
        "services": ["CG"],
        "active": active,
        "queue": [{"id": 100 * pid + i, "service": "CG", "key": float(i)} for i in range(queue)],
    }


def suggest(c, points, **extra):
    body = {"service": "CG", "base_key": 99.0, "prior_minutes": PRIOR, "points": points}
    body.update(extra)
    return c.post("/suggest", json=body).json()["options"]


def test_suggest_prefers_shorter_queue_and_skips_inactive():
    with TestClient(app) as c:
        opts = suggest(c, [point(1, queue=4), point(2, queue=1), point(3, queue=0, active=False)])
        assert [o["point_id"] for o in opts] == [2, 1]
        assert opts[0]["recommended"] is True


def test_learning_changes_estimate():
    with TestClient(app) as c:
        base = c.post("/estimate", json={"prior_minutes": PRIOR, "point": point(7, queue=2)}).json()
        for _ in range(20):
            c.post("/learn", json={"service": "CG", "point_id": 7, "minutes": 20})
        after = c.post("/estimate", json={"prior_minutes": PRIOR, "point": point(7, queue=2)}).json()
        assert after["service_minutes"]["701"] > base["service_minutes"]["701"] + 5


def test_priority_bonus_grows_until_target_is_met():
    """Fila de 6 personas (10 min c/u): sin bonificacion espera 60; con meta de 10 min el modelo sube el bonus."""
    # keys 0..5 y base_key=100: sin bonus todos estan delante; cada minuto de bonus = 60 de clave
    pts = [{"id": 1, "name": "P1", "services": ["CG"], "active": True,
            "queue": [{"id": i, "service": "CG", "key": 100 - 60 * (i + 1) * 5 + 1} for i in range(6)]}]
    with TestClient(app) as c:
        plain = suggest(c, pts, base_key=100.0, preferential=False)[0]
        vip = suggest(c, pts, base_key=100.0, preferential=True, bonus_min=5, max_bonus_min=60, target_wait_min=10)[0]
        assert vip["est_wait_min"] < plain["est_wait_min"]
        assert vip["bonus_min"] > 5            # el modelo aumento la prioridad
        assert vip["saved_min"] > 0
        capped = suggest(c, pts, base_key=100.0, preferential=True, bonus_min=5, max_bonus_min=5, target_wait_min=1)[0]
        assert capped["bonus_min"] == 5 and capped["meets_target"] is False


def test_normal_patient_gets_no_bonus():
    with TestClient(app) as c:
        o = suggest(c, [point(1, queue=2)], preferential=False, bonus_min=20, max_bonus_min=60, target_wait_min=1)[0]
        assert o["bonus_min"] == 0 and o["saved_min"] == 0


def test_report_tracks_effectiveness_and_predict_answers():
    with TestClient(app) as c:
        for i in range(25):  # la realidad (20 min) difiere del valor inicial (10): el modelo debe mejorar
            c.post("/learn", json={"service": "CG", "point_id": 9, "minutes": 20 + (i % 3 - 1), "prior_minutes": 10})
        r = c.post("/model/report", json={"prior_minutes": PRIOR}).json()
        assert r["samples"] == 25
        assert r["mae"] < r["mae_baseline"] and r["improvement_pct"] > 30
        assert r["mae_recent"] < r["mae_early"]
        assert r["verdict"]["level"] == "good"
        assert r["curve"] and r["cells"][0]["samples"] > 0

        a = c.post("/predict", json={"service": "CG", "point_id": 9, "preferential": False, "prior_minutes": 10}).json()
        assert 17 < a["minutes"] < 22 and a["low"] < a["minutes"] < a["high"]
        assert a["samples"] == 25 and a["levels"][0]["label"].startswith("Valor inicial")


def test_report_without_data_is_insufficient():
    with TestClient(app) as c:
        r = c.post("/model/report", json={"prior_minutes": PRIOR}).json()
        assert r["samples"] == 0 and r["verdict"]["level"] == "insufficient"
