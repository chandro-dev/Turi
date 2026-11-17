"""Estudio de factibilidad: scikit-learn vs. el estimador actual (EMA con contraccion).

Ejecutar (desde suggestion-service/):
    pip install -r requirements.txt scikit-learn
    python experiments/sklearn_feasibility.py

Metodo: evaluacion "prequential" (predecir primero, aprender despues) sobre un flujo sintetico de
atenciones con ruido, efecto de edad/hora/prioridad y un CAMBIO de comportamiento a mitad del flujo
(el Consultorio 2 se vuelve mas rapido). Mide error (MAE, minutos), tiempos y memoria.
Los datos son sinteticos: sirven para comparar enfoques, no para afirmar precision real.
"""
from __future__ import annotations

import math
import os
import random
import resource
import sys
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

N = 1500
SHIFT_AT = 750
PRIOR = {"CG": 12.0, "LAB": 6.0, "FAR": 4.0, "ODO": 20.0}
BASE = {("CG", 1): 9, ("CG", 2): 16, ("LAB", 3): 5, ("FAR", 4): 3, ("ODO", 5): 24}
POINTS = {"CG": [1, 2], "LAB": [3], "FAR": [4], "ODO": [5]}
WINDOWS = [(0, 50), (50, 150), (150, 400), (400, 750), (750, 900), (900, 1500)]


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def true_mean(service, point, pref, hour, age, shifted):
    m = BASE[(service, point)]
    if pref:
        m *= 1.25
    if 9 <= hour <= 11:
        m *= 1.15
    m *= 1 + 0.004 * (age - 40)
    if shifted and (service, point) == ("CG", 2):
        m *= 0.55  # cambio de comportamiento: el punto 2 se acelera
    return m


def make_stream(seed=7):
    rng = random.Random(seed)
    events = []
    for i in range(N):
        service = rng.choices(list(PRIOR), weights=[5, 3, 3, 2])[0]
        point = rng.choice(POINTS[service])
        age = rng.randint(2, 88)
        pref = age >= 60 or rng.random() < 0.1
        hour = rng.randint(7, 17)
        mu = true_mean(service, point, pref, hour, age, i >= SHIFT_AT)
        y = max(0.5, rng.lognormvariate(math.log(mu), 0.3))
        events.append((service, point, pref, hour, age, y))
    return events


def window_report(name, errs):
    out = []
    for a, b in WINDOWS:
        chunk = errs[a:b]
        out.append(sum(chunk) / len(chunk) if chunk else float("nan"))
    return name, out


def run_prior(events):
    return [abs(PRIOR[s] - y) for s, p, pref, h, a, y in events]


def run_ema(events):
    from app.core.database import Base, SessionLocal, engine
    from app.models import entities  # noqa: F401
    from app.models import estimator

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    errs = []
    t_pred = 0.0
    with SessionLocal() as db:
        for s, p, pref, h, a, y in events:
            t0 = time.perf_counter()
            table = estimator.load_table(db, s)
            pred = estimator.estimate(table, str(p), pref, PRIOR[s])
            t_pred += time.perf_counter() - t0
            errs.append(abs(pred - y))
            estimator.learn(db, s, str(p), pref, y)
    return errs, t_pred / len(events) * 1000


def run_sklearn(events, kind, retrain_every=25, window=None):
    import numpy as np
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    def feats(e):
        s, p, pref, h, a, _ = e
        return [s, str(p), int(pref), h, a]

    def build():
        pre = ColumnTransformer([
            ("cat", OneHotEncoder(handle_unknown="ignore"), [0, 1]),
            ("num", StandardScaler(), [2, 3, 4]),
        ])
        # Ridge/GBR sobre log(duracion): las duraciones son asimetricas y positivas
        reg = Ridge(alpha=1.0) if kind == "ridge" else GradientBoostingRegressor(
            n_estimators=120, max_depth=3, learning_rate=0.08, random_state=0)
        return make_pipeline(pre, reg)

    errs, X, y = [], [], []
    model = None
    fit_times, pred_times = [], []
    for i, e in enumerate(events):
        f = feats(e)
        if model is None:
            pred = PRIOR[e[0]]
        else:
            t0 = time.perf_counter()
            pred = float(np.exp(model.predict(np.array([f], dtype=object))[0]))
            pred_times.append(time.perf_counter() - t0)
        errs.append(abs(pred - e[5]))
        X.append(f)
        y.append(math.log(e[5]))
        if len(X) >= 30 and len(X) % retrain_every == 0:
            Xs, ys = (X[-window:], y[-window:]) if window else (X, y)
            m = build()
            t0 = time.perf_counter()
            m.fit(np.array(Xs, dtype=object), np.array(ys))
            fit_times.append(time.perf_counter() - t0)
            model = m
    return errs, sum(pred_times) / len(pred_times) * 1000, max(fit_times) * 1000


def main():
    events = make_stream()
    rows = [window_report("Solo prior (sin aprender)", run_prior(events))]
    ema_errs, ema_ms = run_ema(events)
    rows.append(window_report("EMA + contraccion (actual)", ema_errs))

    base_mem = rss_mb()
    import sklearn
    t0 = time.perf_counter()
    import sklearn.ensemble, sklearn.linear_model  # noqa: F401,E401
    import_s = time.perf_counter() - t0
    after_import_mem = rss_mb()

    r_errs, r_pred, r_fit = run_sklearn(events, "ridge")
    g_errs, g_pred, g_fit = run_sklearn(events, "gbr")
    gw_errs, _, _ = run_sklearn(events, "gbr", window=300)
    rows += [window_report("sklearn Ridge (todo el historial)", r_errs),
             window_report("sklearn GradientBoosting (todo)", g_errs),
             window_report("sklearn GradientBoosting (ult. 300)", gw_errs)]

    print(f"\nscikit-learn {sklearn.__version__} | python {sys.version.split()[0]} | {os.uname().machine}")
    print("\nMAE (min) por tramo del flujo; el cambio de comportamiento ocurre en el evento", SHIFT_AT)
    head = " | ".join(f"{a}-{b}" for a, b in WINDOWS)
    print(f"{'modelo':38s} | {head}")
    for name, vals in rows:
        print(f"{name:38s} | " + " | ".join(f"{v:6.2f}" for v in vals))
    print("\nCosto operativo")
    print(f"  import sklearn: {import_s:.2f} s, memoria +{after_import_mem - base_mem:.0f} MB (RSS max {after_import_mem:.0f} MB)")
    print(f"  prediccion: EMA {ema_ms:.2f} ms (incluye consulta SQL) | Ridge {r_pred:.2f} ms | GBR {g_pred:.2f} ms")
    print(f"  entrenamiento (peor caso, <=1500 filas): Ridge {r_fit:.0f} ms | GBR {g_fit:.0f} ms")


if __name__ == "__main__":
    main()
