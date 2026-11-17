"""Modo hibrido: EMA + scikit-learn (se omite si scikit-learn no esta instalado)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402

pytest.importorskip("sklearn")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import sk_model  # noqa: E402

PRIOR = {"CG": 10.0}


@pytest.fixture(autouse=True)
def clean():
    from app.models import entities  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    sk_model.reset()
    sk_model.MODE = "hybrid"


def feed(c, n, point=3):
    """Mananas rapidas (10 min) y tardes lentas (20 min) en el mismo punto."""
    for i in range(n):
        hour, minutes = (8, 10) if i % 2 == 0 else (15, 20)
        c.post("/learn", json={"service": "CG", "point_id": point, "minutes": minutes, "prior_minutes": 12, "hour": hour})


def predict(c, hour, point=3):
    return c.post("/predict", json={"service": "CG", "point_id": point, "prior_minutes": 12, "hour": hour}).json()


def test_not_trained_below_minimum():
    with TestClient(app) as c:
        feed(c, 10)
        assert sk_model.info()["trained"] is False
        assert c.post("/model/retrain").json()["trained"] is False


def test_trains_and_learns_time_of_day_effect():
    with TestClient(app) as c:
        feed(c, 60)  # 25 y 50 disparan reentrenamiento (>= 40 muestras)
        info = sk_model.info()
        assert info["trained"] and info["trained_samples"] >= 40 and 0 < info["weight"] <= sk_model.MAX_WEIGHT
        morning, afternoon = predict(c, 8), predict(c, 15)
        assert afternoon["minutes"] > morning["minutes"]                       # el modelo distingue la franja horaria
        assert any("scikit-learn" in lv["label"] for lv in afternoon["levels"])  # y lo explica


def test_report_compares_estimators_and_exposes_state():
    with TestClient(app) as c:
        feed(c, 80)
        r = c.post("/model/report", json={"prior_minutes": PRIOR}).json()
        assert r["estimator"]["trained"] is True and r["attentions_stored"] == 80
        cmp = r["comparison"]
        assert cmp["n"] > 0 and cmp["mae_ema"] is not None and cmp["mae_sklearn"] is not None
        # con efecto horario real, scikit-learn acierta mas que el EMA solo
        assert cmp["mae_sklearn"] < cmp["mae_ema"]


def test_manual_retrain_endpoint():
    with TestClient(app) as c:
        feed(c, 45)
        out = c.post("/model/retrain").json()
        assert out["trained"] is True and out["estimator"]["trained_samples"] == 45


def test_ema_mode_ignores_sklearn():
    with TestClient(app) as c:
        feed(c, 60)
        sk_model.MODE = "ema"
        assert sk_model.predict("CG", "3", "normal", 8) is None
        assert not any("scikit-learn" in lv["label"] for lv in predict(c, 8)["levels"])
