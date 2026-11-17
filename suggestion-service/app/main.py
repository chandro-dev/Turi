from contextlib import asynccontextmanager

from fastapi import FastAPI

from .controllers import router
from .core.database import SessionLocal, init_db
from .models import sk_model


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if sk_model.enabled():
        with SessionLocal() as db:
            sk_model.train(db)  # recupera el modelo a partir de las atenciones guardadas
    yield


app = FastAPI(title="Turi - Servicio de sugerencia de turnos", version="1.1.0", lifespan=lifespan)
app.include_router(router)
