"""Autenticación básica: un editor, sesión con token en cookie HttpOnly.

La contraseña se guarda con **Argon2id** (portado del motor editorial, NN-117.5).
Se mantiene la verificación de **PBKDF2-SHA256** para que las contraseñas ya
guardadas sigan funcionando: el formato guardado decide con qué algoritmo se
comprueba.

En modo demo el acceso rápido crea sesiones marcadas como demo; ese modo sólo
debe activarse en local.
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

# Prefijos de los formatos de contraseña guardados.
PBKDF2_PREFIJO = "pbkdf2$"
ARGON2_PREFIJO = "$argon2"


def _argon2_disponible() -> bool:
    try:
        import argon2  # noqa: F401
    except ImportError:
        return False
    return True


def hash_password(password: str, salt: str | None = None) -> str:
    """Genera el hash de una contraseña.

    Usa Argon2id cuando la dependencia está disponible; si no, cae a
    PBKDF2-SHA256 (200 000 iteraciones) para no dejar al operador sin poder
    entrar. El formato guardado lo dice: `pbkdf2$salt$digest` o el texto
    estándar de Argon2 (`$argon2id$…`).
    """
    if _argon2_disponible():
        from argon2 import PasswordHasher

        return PasswordHasher().hash(password)
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{PBKDF2_PREFIJO}{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """Comprueba la contraseña contra el hash guardado, sea del formato que sea."""
    if not stored:
        return False
    if stored.startswith(PBKDF2_PREFIJO):
        try:
            _, salt, digest = stored.split("$")
        except ValueError:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 200_000
        ).hex()
        return hmac.compare_digest(candidate, digest)
    if stored.startswith(ARGON2_PREFIJO):
        try:
            from argon2 import PasswordHasher
            from argon2.exceptions import VerificationError, VerifyMismatchError
        except ImportError:
            # Sin la dependencia no se puede comprobar: se rechaza (no se acepta).
            return False
        try:
            return bool(PasswordHasher().verify(stored, password))
        except (VerifyMismatchError, VerificationError):
            return False
    return False


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
    """Cookie de sesión: HttpOnly, y **segura** fuera del entorno local.

    Antes `secure=False` estaba fijo: por HTTPS la cookie de sesión viajaba en
    claro. Ahora depende del entorno (ADR-017) y se puede fijar a mano con
    `NEURAL_SESSION_COOKIE_SECURE` / `_SAMESITE` / `_DOMAIN`.
    """
    settings = get_settings()
    kwargs = {
        "httponly": True,
        "samesite": settings.session_cookie_samesite,
        "secure": settings.cookie_segura,
        "max_age": settings.session_ttl_minutes * 60,
        "path": "/",
    }
    if settings.session_cookie_domain:
        kwargs["domain"] = settings.session_cookie_domain
    response.set_cookie(COOKIE_NAME, token, **kwargs)


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    kwargs = {"path": "/"}
    if settings.session_cookie_domain:
        kwargs["domain"] = settings.session_cookie_domain
    response.delete_cookie(COOKIE_NAME, **kwargs)


def get_current_actor(request: Request, db=Depends(get_db)) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Sesión no iniciada")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = db.scalar(select(DbSession).where(DbSession.token_hash == token_hash))
    if session is None or session.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="La sesión ha caducado; vuelve a entrar")
    return {"actor_id": session.actor_id, "is_demo": session.is_demo}


def require_demo_disabled(settings=None) -> None:
    """Impide una operación que solo tiene sentido con servicios reales.

    En el entorno local el modo demo es legítimo; en un despliegue, el modo
    demo está prohibido (lo comprueba `Settings.comprobar()` al arrancar).

    Los ajustes se resuelven **en la llamada**, no al importar el módulo: si se
    fijaran al importar, el valor quedaría congelado y no se podría cambiar en
    caliente ni sustituir en las pruebas.
    """
    settings = settings or get_settings()
    if settings.demo_mode:
        raise HTTPException(status_code=400, detail="El modo demo está activado; desactívalo para usar servicios reales")


def require_paid_services(settings=None) -> None:
    """Ruta que llama a un proveedor de pago.

    En un despliegue, si los servicios de pago están desactivados, se dice en
    voz alta en vez de encolar un trabajo que no va a poder completarse (o que
    devolvería datos de demostración sin avisar).
    """
    settings = settings or get_settings()
    if settings.es_despliegue and not settings.paid_services_enabled:
        raise HTTPException(
            status_code=400,
            detail="Los servicios de pago están desactivados en este despliegue "
            "(NEURAL_PAID_SERVICES_ENABLED=false): esta función necesita un proveedor real",
        )
