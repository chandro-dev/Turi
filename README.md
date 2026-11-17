# Turi - Gestion y priorizacion de turnos en salud (MVP)

Produccion de demostracion: <https://turi.alejocarretero.site>

## Arranque local

```bash
cp .env.example .env      # opcional, hay valores por defecto para desarrollo
docker compose up --build
```

Abrir <http://localhost:8080>.

## Documentacion

- [Arquitectura (componentes, responsabilidades, MVC)](docs/ARQUITECTURA.md)
- [Modelo de IA y verificacion de scikit-learn](docs/MODELO_IA.md)

## Componentes

| Servicio | Tecnologia | Funcion |
|---|---|---|
| `turi-web` | nginx + JS (modulos ES, MVC) | Interfaz y proxy de `/api` |
| `turnos-api` | FastAPI + SQLAlchemy (MVC) | Autenticacion por rol, turnos, prioridad, fila, auditoria |
| `suggestion-service` | FastAPI + SQLAlchemy (MVC) | IA: sugiere punto de atencion y estima esperas |
| `db` | PostgreSQL 16 | Bases `turi` y `turi_suggest` |

## Usuarios demo (`SEED_DEMO=true`)

| Usuario | Clave | Rol |
|---|---|---|
| recepcion | recepcion123 | Registra, asigna, reasigna, edita, cancela |
| medico1 / medico2 | medico123 | Consultorio 1 / 2 |
| laboratorio / farmacia / odontologia | medico123 | Otros puntos |
| supervisor | supervisor123 | Indicadores, fila general, consultorios y personal, prueba del modelo |

Para uso real: `SEED_DEMO=false`, cambia `JWT_SECRET` y `POSTGRES_PASSWORD`, y crea usuarios propios.

## Datos de prueba

Se cargan solos al iniciar con `SEED_DEMO=true` y sin turnos. Para agregar otro lote:

```bash
docker compose exec turnos-api python -m app.seeds.demo_data
```

## Pruebas

```bash
cd turnos-api && pip install -r requirements.txt pytest && pytest
cd suggestion-service && pip install -r requirements.txt pytest httpx && pytest
python scripts/e2e.py http://localhost:8080      # extremo a extremo (requiere el stack arriba)
```

## Despliegue en servidor con Caddy

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

No publica puertos; `turi-web` se une a la red `ecd-vps_default` del Caddy existente.
