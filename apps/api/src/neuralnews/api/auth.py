"""Autenticación: entrada normal, salida y acceso rápido en modo demo (sólo local)."""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select

from ..config import get_settings
from ..db import get_db
from ..models import Session as DbSession
from ..schemas import LoginRequest, MeResponse
from ..security import (
    COOKIE_NAME,
    clear_session_cookie,
    create_session,
    get_current_actor,
    hash_password,
    set_session_cookie,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _admin_password_hash() -> str | None:
    return get_settings().admin_password and hash_password(get_settings().admin_password) or None


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, response: Response, db=Depends(get_db)) -> MeResponse:
    settings = get_settings()
    expected_hash = _admin_password_hash()
    if expected_hash is None:
        raise HTTPException(
            status_code=503,
            detail="No hay contraseña configurada. Define NEURAL_ADMIN_PASSWORD en el archivo .env",
        )
    if payload.username != settings.admin_username or not verify_password(payload.password, expected_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    token, _ = create_session(db, actor_id=payload.username, is_demo=False)
    set_session_cookie(response, token)
    return MeResponse(actor_id=payload.username, is_demo=False, demo_mode=settings.demo_mode)


@router.post("/demo", response_model=MeResponse)
def demo_login(response: Response, db=Depends(get_db)) -> MeResponse:
    """Acceso rápido de demostración: sólo cuando el modo demo está activado (uso local)."""
    settings = get_settings()
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="El modo demo está desactivado")
    token, _ = create_session(db, actor_id="demo", is_demo=True)
    set_session_cookie(response, token)
    return MeResponse(actor_id="demo", is_demo=True, demo_mode=True)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    # Solo se cierra la SESIÓN ACTUAL. Antes se borraban todas las del actor,
    # lo que expulsaba también de otras pestañas abiertas (hallazgo B15).
    token = request.cookies.get(COOKIE_NAME)
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        session = db.scalar(
            select(DbSession).where(DbSession.token_hash == token_hash)
        )
        if session is not None:
            db.delete(session)
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(actor=Depends(get_current_actor)) -> MeResponse:
    return MeResponse(
        actor_id=actor["actor_id"], is_demo=actor["is_demo"], demo_mode=get_settings().demo_mode
    )
