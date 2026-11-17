"""Prueba de humo end-to-end contra un despliegue en ejecucion.

    python scripts/e2e.py [http://localhost:8080]

Requiere SEED_DEMO=true (usuarios demo). Crea datos de prueba reales: usar en entornos de demostracion.
"""
import json
import sys
import time
import urllib.error
import urllib.request as u

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/") + "/api"
FAILS = []


def call(method, path, body=None, tok=None):
    req = u.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                    headers={"Content-Type": "application/json", "User-Agent": "turi-e2e/1.0", **({"Authorization": "Bearer " + tok} if tok else {})})
    try:
        with u.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(name, cond, extra=""):
    print(("OK   " if cond else "FAIL ") + name + (f"  {extra}" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def login(user, pwd):
    return call("POST", "/auth/login", {"username": user, "password": pwd})[1]["token"]


rec, doc, sup = login("recepcion", "recepcion123"), login("medico2", "medico123"), login("supervisor", "supervisor123")
stamp = str(int(time.time()))[-7:]

# --- Bug: rango de edad para gestante
for age in (1, 5, 9):
    s, r = call("POST", "/turns/suggest", {"service_code": "CG", "age": age, "pregnant": True}, rec)
    check(f"preview rechaza gestante con {age} anos", s == 422 and "gestante" in json.dumps(r).lower(), str(r))
s, r = call("POST", "/turns", {"doc_number": "A" + stamp, "patient_name": "Nina Prueba", "age": 8, "pregnant": True, "service_code": "CG"}, rec)
check("crear turno rechaza gestante de 8 anos", s == 422, str(r))
s, r = call("POST", "/turns/suggest", {"service_code": "CG", "age": 70, "pregnant": True}, rec)
check("rechaza gestante de 70 anos", s == 422)
s, r = call("POST", "/turns/suggest", {"service_code": "CG", "age": 28, "pregnant": True}, rec)
check("acepta gestante de 28 anos", s == 200 and r["priority_class"] == "PREFERENCIAL")
s, r = call("POST", "/turns/suggest", {"service_code": "CG", "age": 6, "pregnant": False}, rec)
check("acepta nino de 6 anos sin gestacion", s == 200 and r["priority_class"] == "NORMAL")

# --- editar: la combinacion final se valida
s, t = call("POST", "/turns", {"doc_number": "B" + stamp, "patient_name": "Adulto Prueba", "age": 30, "service_code": "LAB"}, rec)
check("crear turno valido", s == 201, str(t))
s, r = call("PATCH", f"/turns/{t['id']}", {"age": 7, "pregnant": True}, rec)
check("editar a gestante de 7 anos rechazado", s == 422, str(r))
s, r = call("PATCH", f"/turns/{t['id']}", {"age": 7}, rec)
check("editar edad a 7 sin gestante ok", s == 200 and r["age"] == 7, str(r))

# --- Bug: fila general del supervisor muestra atendidos y tiempo de atencion
s, t2 = call("POST", "/turns", {"doc_number": "C" + stamp, "patient_name": "Atendido Prueba", "age": 40, "service_code": "CG", "point_id": 2}, rec)
# limpiar un posible turno en curso de ejecuciones anteriores
s, panel = call("GET", "/doctor/panel", tok=doc)
if panel.get("current"):
    c = panel["current"]
    if c["status"] == "CALLED":
        call("POST", f"/doctor/turns/{c['id']}/start", tok=doc)
    call("POST", f"/doctor/turns/{c['id']}/finish", tok=doc)
s, cur = call("POST", "/doctor/call-next", tok=doc)
check("crear turno para atender", "code" in t2, str(t2))
check("llamar siguiente", "id" in cur, str(cur))
if "id" not in cur or "code" not in t2:
    sys.exit(1)
while cur.get("code") != t2["code"]:  # atender primero a quienes esten delante en el punto 2
    call("POST", f"/doctor/turns/{cur['id']}/start", tok=doc)
    call("POST", f"/doctor/turns/{cur['id']}/finish", tok=doc)
    s, cur = call("POST", "/doctor/call-next", tok=doc)
call("POST", f"/doctor/turns/{cur['id']}/start", tok=doc)
time.sleep(2)
s, fin = call("POST", f"/doctor/turns/{cur['id']}/finish", tok=doc)
check("finalizar devuelve duration_min", s == 200 and fin["duration_min"] is not None, str(fin))
s, all_turns = call("GET", "/turns?include_closed=true", tok=sup)
mine = next((x for x in all_turns if x["id"] == t2["id"]), None)
check("supervisor ve turno atendido con tiempos", bool(mine) and mine["status"] == "DONE" and mine["duration_min"] is not None and mine["wait_min"] is not None, str(mine))
s, active_only = call("GET", "/turns", tok=sup)
check("sin include_closed no aparecen atendidos", all(x["status"] != "DONE" for x in active_only))

# --- Pantalla de espera: proximos turnos
s, d = call("GET", "/public/display")
check("display incluye proximos por punto", s == 200 and all("upcoming" in p for p in d["points"]))
check("display solo expone codigos (sin nombres)", "patient_name" not in json.dumps(d))
with_q = [p for p in d["points"] if p["waiting"] > 0]
check("hay puntos con proximos turnos", bool(with_q) and all(len(p["upcoming"]) >= 1 for p in with_q))

print("\n" + ("TODO OK" if not FAILS else f"{len(FAILS)} FALLAS: {FAILS}"))
sys.exit(1 if FAILS else 0)
