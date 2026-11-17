"""CONTROLADOR - autenticacion."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import current_user, make_token, verify_password
from ..models import User
from ..services import availability
from ..views import presenters
from ..views.schemas import LoginIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.execute(select(User).where(User.username == body.username.strip().lower())).scalar_one_or_none()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Usuario o contrasena incorrectos")
    if not u.active:
        raise HTTPException(403, "Tu usuario esta desactivado. Contacta a supervision")
    return {"token": make_token(u), "user": presenters.user(u, availability.user_point(db, u))}


@router.get("/me")
def me(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return presenters.user(u, availability.user_point(db, u))
