"""Punto de entrada: ensambla modelo, servicios, vistas y controladores."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .controllers import ROUTERS
from .core.config import SEED_DEMO
from .core.database import SessionLocal, run_migrations
from .seeds.catalog import ensure_bootstrap_admin, seed_catalog, seed_users
from .seeds.demo_data import seed_history
from .services import events as _events  # noqa: F401  (registra la difusion en cada commit)
from .services.errors import DomainError

log = logging.getLogger("turi")


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_migrations()
    with SessionLocal() as db:
        seed_catalog(db)
        if ensure_bootstrap_admin(db):
            log.info("administrador inicial creado")
        if SEED_DEMO:
            seed_users(db)
            try:
                log.info("seed: %s", seed_history(db))
            except Exception:  # noqa: BLE001
                log.exception("seed de historial fallo")
                db.rollback()
    yield


app = FastAPI(title="Turi - API de turnos", version="1.1.0", lifespan=lifespan)
for router in ROUTERS:
    app.include_router(router)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.message})
