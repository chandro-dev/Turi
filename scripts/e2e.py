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

# --- Atencion prioritaria guiada por el modelo
for i in range(4):
    call("POST", "/turns", {"doc_number": f"N{i}{stamp}", "patient_name": f"Normal {i}", "age": 30, "service_code": "FAR"}, rec)
s, prev_n = call("POST", "/turns/suggest", {"service_code": "FAR", "age": 30}, rec)
s, prev_p = call("POST", "/turns/suggest", {"service_code": "FAR", "age": 72}, rec)
on, op = prev_n["options"][0], prev_p["options"][0]
check("preview informa politica de prioridad", "policy" in prev_p and prev_p["policy"]["target_wait_min"] > 0)
check("prioritario recibe adelanto del modelo", op["bonus_min"] >= prev_p["policy"]["base_bonus_min"] and on["bonus_min"] == 0, str((op, on)))
check("prioritario espera menos que un normal", op["est_wait_min"] <= on["est_wait_min"] and op["saved_min"] >= 0, str((op["est_wait_min"], on["est_wait_min"])))
s, tp = call("POST", "/turns", {"doc_number": "P" + stamp, "patient_name": "Prioritario Prueba", "age": 72, "service_code": "FAR"}, rec)
check("turno prioritario guarda el adelanto", s == 201 and tp.get("bonus_min"), str(tp))
s, lst = call("GET", "/turns", tok=rec)
far = [x for x in lst if x["service"]["code"] == "FAR" and x["status"] == "WAITING" and x["code"] != tp["code"] and x["patient_name"].startswith("Normal") and x["doc_number"].endswith(stamp)]  # solo los de esta ejecucion
mine = next(x for x in lst if x["code"] == tp["code"])
check("prioritario queda delante de los normales recien llegados", bool(far) and all(mine["position"] < x["position"] for x in far), str((mine["position"], [x["position"] for x in far])))

# --- Prueba del modelo (supervisor)
s, rep = call("GET", "/model/report", tok=sup)
check("reporte del modelo", s == 200 and rep["samples"] > 0 and "verdict" in rep and rep["cells"], str(rep)[:200])
check("reporte trae curva y efectividad", "curve" in rep and rep["mae"] is not None and rep["mae_baseline"] is not None, str(rep)[:300])
check("reporte prohibido a recepcion", call("GET", "/model/report", tok=rec)[0] == 403)
s, ans = call("POST", "/model/predict", {"service_code": "CG", "preferential": True}, sup)
check("el modelo responde a una consulta", s == 200 and ans["answer"] and ans["points"] and ans["points"][0]["levels"], str(ans)[:200])
check("consulta de modelo prohibida a recepcion", call("POST", "/model/predict", {"service_code": "CG"}, rec)[0] == 403)

# --- Recursos: puntos, personal y horarios (supervisor)
check("admin/overview prohibido a recepcion", call("GET", "/admin/overview", tok=rec)[0] == 403)
s, ov = call("GET", "/admin/overview", tok=sup)
check("overview lista puntos, personal y servicios", s == 200 and ov["points"] and ov["services"] and "users" in ov, str(ov)[:200])

s, pa = call("POST", "/admin/points", {"name": f"E2E Lab {stamp}", "service_codes": ["LAB"]}, sup)
check("crear punto", s == 201, str(pa))
s, pb = call("POST", "/admin/points", {"name": f"E2E Fuera {stamp}", "service_codes": ["LAB"]}, sup)
s, dup = call("POST", "/admin/points", {"name": f"E2E Lab {stamp}", "service_codes": ["LAB"]}, sup)
check("nombre de punto duplicado rechazado", s == 409, str(dup))
s, bad = call("POST", "/admin/points", {"name": "Sin servicios", "service_codes": []}, sup)
check("punto sin servicios rechazado", s == 422, str(bad))

s, st1 = call("POST", "/admin/users", {"name": "Tec Uno", "username": f"e2e1{stamp}", "password": "clave123", "role": "MEDICO"}, sup)
s, st2 = call("POST", "/admin/users", {"name": "Tec Dos", "username": f"e2e2{stamp}", "password": "clave123", "role": "MEDICO"}, sup)
check("crear personal", "id" in st1 and "id" in st2, str((st1, st2)))
check("usuario repetido rechazado", call("POST", "/admin/users", {"name": "Otro", "username": f"e2e1{stamp}", "password": "clave123", "role": "MEDICO"}, sup)[0] == 409)
check("clave corta rechazada", call("POST", "/admin/users", {"name": "Otro", "username": f"e2e9{stamp}", "password": "123", "role": "MEDICO"}, sup)[0] == 422)

ALL = [0, 1, 2, 3, 4, 5, 6]
s, sh1 = call("POST", "/admin/shifts", {"user_id": st1["id"], "point_id": pa["id"], "weekdays": ALL, "start": "00:00", "end": "23:59"}, sup)
check("asignar horario que cubre ahora", s == 201, str(sh1))
check("horario con inicio igual a fin rechazado", call("POST", "/admin/shifts", {"user_id": st2["id"], "point_id": pb["id"], "weekdays": ALL, "start": "10:00", "end": "10:00"}, sup)[0] == 422)
check("cruce de horario del mismo funcionario rechazado", call("POST", "/admin/shifts", {"user_id": st1["id"], "point_id": pb["id"], "weekdays": [1], "start": "08:00", "end": "09:00"}, sup)[0] == 409)
check("cruce de horario en el mismo punto rechazado", call("POST", "/admin/shifts", {"user_id": st2["id"], "point_id": pa["id"], "weekdays": [1], "start": "08:00", "end": "09:00"}, sup)[0] == 409)
s, sh2 = call("POST", "/admin/shifts", {"user_id": st2["id"], "point_id": pb["id"], "weekdays": ALL, "start": "00:00", "end": "00:01"}, sup)
check("asignar horario fuera de la hora actual", s == 201, str(sh2))

s, pts = call("GET", "/points", tok=rec)
state = {p["name"]: p["status"] for p in pts}
check("punto con horario vigente esta disponible", state.get(f"E2E Lab {stamp}") == "open", str(state))
check("punto fuera de horario no esta disponible", state.get(f"E2E Fuera {stamp}") == "off_hours", str(state))
s, pv = call("POST", "/turns/suggest", {"service_code": "LAB", "age": 30}, rec)
names = [o["name"] for o in pv["options"]]
check("sugerencia incluye punto en horario y excluye fuera de horario", f"E2E Lab {stamp}" in names and f"E2E Fuera {stamp}" not in names, str(names))
s, r = call("POST", "/turns", {"doc_number": "Z" + stamp, "patient_name": "Prueba Horario", "age": 30, "service_code": "LAB", "point_id": pb["id"]}, rec)
check("no se asigna a un punto fuera de horario", s == 409, str(r))

tec1 = login(f"e2e1{stamp}", "clave123")
s, panel = call("GET", "/doctor/panel", tok=tec1)
check("funcionario en turno ve su punto", s == 200 and panel["off_shift"] is False and panel["point"]["name"] == f"E2E Lab {stamp}", str(panel)[:200])
tec2 = login(f"e2e2{stamp}", "clave123")
s, panel2 = call("GET", "/doctor/panel", tok=tec2)
check("funcionario fuera de turno ve su proximo turno", s == 200 and panel2["off_shift"] is True and panel2["next_shift"], str(panel2))
check("funcionario fuera de turno no puede llamar", call("POST", "/doctor/call-next", tok=tec2)[0] == 403)

s, st_list = call("GET", "/admin/overview", tok=sup)
mine = next(x for x in st_list["users"] if x["id"] == st1["id"])
check("overview muestra el punto actual del funcionario", mine["current_point"] == f"E2E Lab {stamp}" and mine["shifts"], str(mine))

check("cerrar punto", call("PATCH", f"/admin/points/{pa['id']}", {"enabled": False}, sup)[0] == 200)
s, pts = call("GET", "/points", tok=rec)
check("punto cerrado no aparece en recepcion", f"E2E Lab {stamp}" not in [p["name"] for p in pts])
check("reabrir punto", call("PATCH", f"/admin/points/{pa['id']}", {"enabled": True}, sup)[0] == 200)

# limpieza
check("quitar horario", call("DELETE", f"/admin/shifts/{sh2['id']}", tok=sup)[0] == 204)
check("eliminar personal", call("DELETE", f"/admin/users/{st1['id']}", tok=sup)[0] == 204 and call("DELETE", f"/admin/users/{st2['id']}", tok=sup)[0] == 204)
check("eliminar puntos de prueba", call("DELETE", f"/admin/points/{pa['id']}", tok=sup)[0] == 204 and call("DELETE", f"/admin/points/{pb['id']}", tok=sup)[0] == 204)

# --- Servicios, usuarios, horarios nocturnos, tiempo real y motor de IA
s, cfg = call("GET", "/config")
check("config publica", s == 200 and isinstance(cfg.get("demo"), bool), str(cfg))

code = "T" + stamp[-5:]
s, svc = call("POST", "/admin/services", {"code": code, "name": f"Servicio {stamp}", "prior_minutes": 15, "color": "#ff8800"}, sup)
check("crear servicio", s == 201 and svc["code"] == code, str(svc))
check("codigo de servicio repetido rechazado", call("POST", "/admin/services", {"code": code, "name": "Otro", "prior_minutes": 10, "color": "#ff8800"}, sup)[0] == 409)
check("codigo de servicio invalido rechazado", call("POST", "/admin/services", {"code": "x!", "name": "Malo", "prior_minutes": 10, "color": "#ff8800"}, sup)[0] == 422)
check("servicio exige rol supervisor", call("POST", "/admin/services", {"code": "ZZ9", "name": "No", "prior_minutes": 10, "color": "#ff8800"}, rec)[0] == 403)
check("editar servicio", call("PATCH", f"/admin/services/{svc['id']}", {"prior_minutes": 25}, sup)[1]["prior_minutes"] == 25)
s, pnew = call("POST", "/admin/points", {"name": f"Sala {stamp}", "service_codes": [code]}, sup)
check("crear punto con el servicio nuevo", s == 201, str(pnew))
check("servicio en uso no se elimina", call("DELETE", f"/admin/services/{svc['id']}", tok=sup)[0] == 409)
s, pv = call("POST", "/turns/suggest", {"service_code": code, "age": 30}, rec)
check("el servicio nuevo ya recibe sugerencias", s == 200 and pv["options"] and pv["options"][0]["name"] == f"Sala {stamp}", str(pv)[:200])

# usuarios de todos los roles
s, u_rec = call("POST", "/admin/users", {"name": "Recep Prueba", "username": f"e2r{stamp}", "password": "clave123", "role": "RECEPCION"}, sup)
check("crear usuario de recepcion", s == 201 and u_rec["role"] == "RECEPCION", str(u_rec))
check("el nuevo usuario inicia sesion", call("POST", "/auth/login", {"username": f"e2r{stamp}", "password": "clave123"})[0] == 200)
check("desactivar usuario", call("PATCH", f"/admin/users/{u_rec['id']}", {"active": False}, sup)[0] == 200)
check("usuario desactivado no puede entrar", call("POST", "/auth/login", {"username": f"e2r{stamp}", "password": "clave123"})[0] == 403)
check("reactivar usuario", call("PATCH", f"/admin/users/{u_rec['id']}", {"active": True}, sup)[0] == 200)
me = call("GET", "/auth/me", tok=sup)[1]
check("no puedes desactivarte", call("PATCH", f"/admin/users/{me['id']}", {"active": False}, sup)[0] == 409)
check("no puedes eliminarte", call("DELETE", f"/admin/users/{me['id']}", tok=sup)[0] == 409)
check("no puedes cambiar tu propio rol", call("PATCH", f"/admin/users/{me['id']}", {"role": "RECEPCION"}, sup)[0] == 409)
check("cambiar rol a medico", call("PATCH", f"/admin/users/{u_rec['id']}", {"role": "MEDICO"}, sup)[1]["role"] == "MEDICO")

# turno de trabajo que cruza la medianoche
s, night = call("POST", "/admin/shifts", {"user_id": u_rec["id"], "point_id": pnew["id"], "weekdays": ALL, "start": "22:00", "end": "06:00"}, sup)
check("horario nocturno (cruza medianoche) aceptado", s == 201 and night["overnight"] is True, str(night))
check("cruce con horario nocturno detectado", call("POST", "/admin/shifts", {"user_id": u_rec["id"], "point_id": pnew["id"], "weekdays": [2], "start": "03:00", "end": "04:00"}, sup)[0] == 409)
check("inicio igual a fin rechazado", call("POST", "/admin/shifts", {"user_id": u_rec["id"], "point_id": pnew["id"], "weekdays": [2], "start": "10:00", "end": "10:00"}, sup)[0] == 422)
check("fuera del horario nocturno si se puede asignar", call("POST", "/admin/shifts", {"user_id": u_rec["id"], "point_id": pnew["id"], "weekdays": [2], "start": "08:00", "end": "09:00"}, sup)[0] == 201)

# tiempo real (SSE): un cambio en la base llega al cliente conectado
import http.client
import urllib.parse as up

host = up.urlparse(BASE)
conn = (http.client.HTTPSConnection if host.scheme == "https" else http.client.HTTPConnection)(host.netloc, timeout=8)
conn.request("GET", "/api/events", headers={"User-Agent": "turi-e2e/1.0", "Accept": "text/event-stream"})
resp = conn.getresponse()
check("flujo SSE disponible", resp.status == 200 and "text/event-stream" in (resp.getheader("Content-Type") or ""), str(resp.status))
first = resp.fp.readline().decode()
resp.fp.readline(), resp.fp.readline()
call("PATCH", f"/admin/services/{svc['id']}", {"prior_minutes": 26}, sup)   # provoca un commit
got = ""
try:
    for _ in range(6):
        line = resp.fp.readline().decode()
        if line.startswith("data: change"):
            got = line
            break
except Exception as e:  # noqa: BLE001
    got = f"error: {e}"
check("el cambio se difunde en tiempo real", got.startswith("data: change"), got)
conn.close()

# motor de IA
s, rt = call("POST", "/model/retrain", tok=sup)
check("reentrenar modelo", s == 200 and "estimator" in rt, str(rt)[:200])
s, rep = call("GET", "/model/report", tok=sup)
check("reporte incluye motor y comparacion", "estimator" in rep and "comparison" in rep and "attentions_stored" in rep, str(rep)[:200])
check("reentrenar prohibido a recepcion", call("POST", "/model/retrain", tok=rec)[0] == 403)

# limpieza
call("DELETE", f"/admin/users/{u_rec['id']}", tok=sup)
check("eliminar punto y servicio de prueba", call("DELETE", f"/admin/points/{pnew['id']}", tok=sup)[0] == 204 and call("DELETE", f"/admin/services/{svc['id']}", tok=sup)[0] == 204)

print("\n" + ("TODO OK" if not FAILS else f"{len(FAILS)} FALLAS: {FAILS}"))
sys.exit(1 if FAILS else 0)
