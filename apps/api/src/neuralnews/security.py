"""Autenticación básica: un editor, sesión con token en cookie HttpOnly.

La contraseña se guarda con PBKDF2-SHA256. En modo demo el acceso rápido crea
sesiones marcadas como demo; ese modo sólo debe activarse en local.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select

from .config import get_settings, new_token
from .db import get_db
from .models import AuditLog, Session as DbSession, utcnow

COOKIE_NAME = "nn_session"


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"pbkdf2${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return hmac.compare_digest(candidate, digest)


def admin_password_hash() -> str | None:
    settings = get_settings()
    if not settings.admin_password:
        return None
    return hash_password(settings.admin_password)


def create_session(db, actor_id: str, is_demo: bool = False) -> tuple[str, DbSession]:
    token = new_token()
    settings = get_settings()
    session = DbSession(
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        actor_id=actor_id,
        is_demo=is_demo,
        expires_at=utcnow() + timedelta(minutes=settings.session_ttl_minutes),
    )
    db.add(session)
    db.add(AuditLog(event="login", actor_id=actor_id, detail={"demo": is_demo}))
    return token, session


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=False,  # en despliegue con HTTPS, activar via variable de entorno
        max_age=get_settings().session_ttl_minutes * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def get_current_actor(request: Request, db=Depends(get_db)) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Sesión no iniciada")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = db.scalar(select(DbSession).where(DbSession.token_hash == token_hash))
    if session is None or session.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="La sesión ha caducado; vuelve a entrar")
    return {"actor_id": session.actor_id, "is_demo": session.is_demo}


def require_demo_disabled(settings=get_settings()) -> None:
    if settings.demo_mode:
        raise HTTPException(status_code=400, detail="El modo demo está activado; desactívalo para usar servicios reales")
