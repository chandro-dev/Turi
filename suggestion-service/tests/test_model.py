import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PRIOR = {"CG": 10.0}


def point(pid, queue=0, active=True):
    return {
        "id": pid,
        "name": f"P{pid}",
        "services": ["CG"],
        "active": active,
        "queue": [{"id": 100 * pid + i, "service": "CG", "key": float(i)} for i in range(queue)],
    }


def test_suggest_prefers_shorter_queue_and_skips_inactive():
    with TestClient(app) as c:
        r = c.post("/suggest", json={
            "service": "CG", "new_key": 99.0, "prior_minutes": PRIOR,
            "points": [point(1, queue=4), point(2, queue=1), point(3, queue=0, active=False)],
        })
        opts = r.json()["options"]
        assert [o["point_id"] for o in opts] == [2, 1]
        assert opts[0]["recommended"] is True


def test_learning_changes_estimate():
    with TestClient(app) as c:
        base = c.post("/estimate", json={"prior_minutes": PRIOR, "point": point(7, queue=2)}).json()
        for _ in range(20):
            c.post("/learn", json={"service": "CG", "point_id": 7, "minutes": 20})
        after = c.post("/estimate", json={"prior_minutes": PRIOR, "point": point(7, queue=2)}).json()
        assert after["service_minutes"]["701"] > base["service_minutes"]["701"] + 5
