import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db


def init_db(base, retries: int = 30) -> None:
    for i in range(retries):
        try:
            base.metadata.create_all(engine)
            return
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1)
