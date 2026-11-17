"""CONTROLADORES (C): reciben la peticion HTTP, delegan en servicios y responden con presentadores."""
from . import auth, catalog, doctor, model, public, supervisor, turns

ROUTERS = [public.router, auth.router, catalog.router, turns.router, doctor.router, supervisor.router, model.router]
