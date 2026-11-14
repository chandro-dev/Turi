# Turi - Gestion y priorizacion de turnos en salud (MVP)

## Arranque

```bash
cp .env.example .env      # opcional, hay valores por defecto para desarrollo
docker compose up --build
```

Abrir <http://localhost:8080>.

## Arquitectura

| Servicio | Tecnologia | Funcion |
|---|---|---|
| `web` | nginx + JS vanilla | Interfaz (recepcion, atencion, supervision, pantalla, consulta). Proxy `/api` |
| `turnos-api` | FastAPI + SQLAlchemy | Autenticacion por rol (JWT), turnos, prioridad, fila, auditoria |
| `suggestion-service` | FastAPI + SQLAlchemy | Microservicio de IA: sugiere punto de atencion y estima esperas |
| `db` | PostgreSQL 16 | Bases `turi` (negocio) y `turi_suggest` (modelo) |

Si `suggestion-service` cae, `turnos-api` usa una estimacion basica y sigue operando.

## Usuarios demo (`SEED_DEMO=true`)

| Usuario | Clave | Rol |
|---|---|---|
| recepcion | recepcion123 | Registra pacientes, asigna, reasigna, edita, cancela |
| medico1 / medico2 | medico123 | Consultorio 1 / 2: llama, atiende, marca no presentado |
| laboratorio / farmacia / odontologia | medico123 | Otros puntos |
| supervisor | supervisor123 | Indicadores, simulador de llegadas |

Para uso real: `SEED_DEMO=false`, cambia `JWT_SECRET` y `POSTGRES_PASSWORD`, y crea usuarios propios.

## Flujo

1. Recepcion registra al paciente. Edad >= 60, gestante o discapacidad dan prioridad preferencial (adelanta hasta 20 min en la fila).
2. La IA sugiere el punto con menor espera estimada. Recepcion puede elegir otro.
3. Pantalla publica (`#/pantalla`) y consulta del paciente (`#/consulta`, por codigo o documento).
4. Atencion llama, inicia, finaliza o marca "no se presento". Al finalizar, la duracion real alimenta el modelo.
5. Un turno no presentado se reincorpora desde recepcion con prioridad baja (cede 15 min).

## Modelo de IA

Media online de duracion por (servicio, punto, grupo normal/preferencial) con contraccion bayesiana hacia niveles mas generales y el valor inicial del servicio. Espera de un punto = tiempo restante del paciente actual + duraciones estimadas de quienes van antes. Ver `suggestion-service/app/model.py`. Estadisticas: `GET /model/stats` en el servicio (puerto interno 8001).

## Pruebas

```bash
cd suggestion-service && pip install -r requirements.txt pytest httpx && pytest
```

## Limitaciones del MVP

Actualizacion por polling (3-5 s), sin migraciones (tablas creadas al iniciar), sin modo offline ni multi-sede.
