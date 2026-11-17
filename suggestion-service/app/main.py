from contextlib import asynccontextmanager

from fastapi import FastAPI

from .controllers import router
from .core.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Turi - Servicio de sugerencia de turnos", version="1.1.0", lifespan=lifespan)
app.include_router(router)
