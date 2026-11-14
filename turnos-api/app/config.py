import os
from zoneinfo import ZoneInfo

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://turi:turi@localhost:5432/turi")
SUGGEST_URL = os.getenv("SUGGEST_URL", "http://localhost:8001")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_HOURS = int(os.getenv("JWT_HOURS", "12"))
SEED_DEMO = os.getenv("SEED_DEMO", "true").lower() in ("1", "true", "yes")
TZ = ZoneInfo(os.getenv("APP_TZ", "America/Bogota"))
