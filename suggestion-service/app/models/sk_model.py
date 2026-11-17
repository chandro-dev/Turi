"""Modelo scikit-learn (opcional) que complementa al estimador EMA.

Aprende la duracion (en log) a partir de servicio, punto, tipo de paciente y franja horaria con una regresion
Ridge sobre variables categoricas. Despues de entrenar se precalcula una tabla de predicciones
(servicio, punto, grupo, franja) para que consultar sea O(1) y no cueste decenas de ms por turno de la fila.

Modos (variable de entorno ESTIMATOR):
  ema      solo el estimador EMA (sin scikit-learn)
  hybrid   mezcla EMA y scikit-learn; el peso de scikit-learn crece con las muestras (maximo 60 %)  [por defecto]
  sklearn  igual que hybrid (reservado); siempre cae a EMA si no hay modelo entrenado

Si scikit-learn no esta instalado o falla, el servicio sigue funcionando solo con EMA.
"""
from __future__ import annotations

import logging
import math
import os
import threading
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .entities import Attention

log = logging.getLogger("turi.sk")

try:  # pragma: no cover - depende del entorno
    import numpy as np
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder

    AVAILABLE = True
except Exception:  # noqa: BLE001
    AVAILABLE = False

MODE = os.getenv("ESTIMATOR", "hybrid").lower()
MIN_TRAIN = int(os.getenv("SK_MIN_TRAIN", "40"))          # muestras minimas para entrenar
RETRAIN_EVERY = int(os.getenv("SK_RETRAIN_EVERY", "25"))   # reentrenar cada N atenciones nuevas
MAX_ROWS = 1000                                            # ventana de entrenamiento (las mas recientes)
MAX_WEIGHT = 0.6                                           # peso maximo de scikit-learn en la mezcla
FULL_WEIGHT_SAMPLES = 200                                  # muestras para alcanzar el peso maximo
HOUR_BUCKET = 4                                            # franjas de 4 h: 0-3, 4-7, ...
BUCKETS = [str(i) for i in range(24 // HOUR_BUCKET)] + ["na"]

_lock = threading.Lock()
_state: dict = {"grid": {}, "samples": 0, "trained_at": None}


def enabled() -> bool:
    return AVAILABLE and MODE in ("hybrid", "sklearn")


def bucket(hour: int | None) -> str:
    return "na" if hour is None else str(int(hour) // HOUR_BUCKET)


def weight() -> float:
    n = _state["samples"]
    return min(MAX_WEIGHT, MAX_WEIGHT * n / FULL_WEIGHT_SAMPLES) if n else 0.0


def predict(service: str, point_id: str, grp: str, hour: int | None) -> float | None:
    """Minutos predichos por scikit-learn, o None si no hay modelo o no conoce esa combinacion."""
    if not enabled():
        return None
    return _state["grid"].get((service, point_id, grp, bucket(hour)))


def blend(ema: float, sk: float | None) -> float:
    if sk is None:
        return ema
    w = weight()
    return (1 - w) * ema + w * sk


def info() -> dict:
    return {
        "mode": MODE, "sklearn_installed": AVAILABLE, "active": enabled(), "trained": _state["samples"] > 0,
        "trained_samples": _state["samples"], "trained_at": _state["trained_at"], "weight": round(weight(), 3),
        "min_train": MIN_TRAIN, "retrain_every": RETRAIN_EVERY,
    }


def train(db: Session) -> dict:
    """Entrena con las atenciones guardadas. Seguro de llamar en cualquier momento (falla en silencio hacia EMA)."""
    if not enabled():
        return {"trained": False, "samples": 0, "reason": "scikit-learn no disponible o modo ema"}
    rows = db.execute(select(Attention).order_by(Attention.id.desc()).limit(MAX_ROWS)).scalars().all()
    if len(rows) < MIN_TRAIN:
        return {"trained": False, "samples": len(rows), "reason": f"se necesitan al menos {MIN_TRAIN} atenciones"}
    try:
        X = np.array([[r.service, r.point_id, r.grp, bucket(r.hour)] for r in rows], dtype=object)
        y = np.log(np.array([max(r.minutes, 0.5) for r in rows]))
        model = make_pipeline(
            ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), [0, 1, 2, 3])]),
            Ridge(alpha=1.0),
        )
        model.fit(X, y)
        combos = sorted({(r.service, r.point_id, r.grp) for r in rows})
        keys = [(s, p, g, b) for s, p, g in combos for b in BUCKETS]
        preds = np.exp(model.predict(np.array([list(k) for k in keys], dtype=object)))
        grid = {k: float(v) for k, v in zip(keys, preds)}
    except Exception:  # noqa: BLE001
        log.exception("fallo el entrenamiento de scikit-learn; se sigue con EMA")
        return {"trained": False, "samples": len(rows), "reason": "error de entrenamiento"}
    with _lock:
        _state.update(grid=grid, samples=len(rows), trained_at=datetime.now(timezone.utc).isoformat())
    return {"trained": True, "samples": len(rows)}


def reset() -> None:
    with _lock:
        _state.update(grid={}, samples=0, trained_at=None)
