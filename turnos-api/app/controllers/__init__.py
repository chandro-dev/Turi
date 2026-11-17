"""CONTROLADORES (C): reciben la peticion HTTP, delegan en servicios y responden con presentadores."""
from . import auth, catalog, doctor, events, model, public, resources, supervisor, turns

ROUTERS = [public.router, auth.router, catalog.router, turns.router, doctor.router, supervisor.router, model.router, resources.router, events.router]
