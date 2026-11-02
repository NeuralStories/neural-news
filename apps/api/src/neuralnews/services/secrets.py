"""Secretos de proveedores: bóveda cifrada + entorno.

El valor **efectivo** de cada clave se resuelve así:

  1. la **bóveda** (cifrada con `NEURAL_MASTER_KEY`), si el editor la guardó;
  2. si no, la **variable de entorno** (`NEURAL_LLM_API_KEY`, …).

Regla: la API nunca devuelve el valor, sólo si está configurado. El valor en
claro que usan los adaptadores vive **en memoria** (`vault.py`), no en la base
de datos.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ProviderSecret
from ..vault import (
    ClaveMaestraAusente,
    DescifradoImposible,
    cifrar,
    descifrar,
    forget_all,
    guardar_en_memoria,
    olvidar,
    valor,
)

logger = logging.getLogger(__name__)

# clave de entorno → (proveedor, nombre legible)
PROVEEDORES: dict[str, tuple[str, str]] = {
    "llm_api_key": ("editorial_llm", "Modelo editorial (OpenAI-compatible)"),
    "search_api_key": ("search", "Búsqueda (Brave)"),
    "youtube_api_key": ("youtube", "YouTube Data API v3"),
    "gemini_api_key": ("gemini_video", "Análisis de vídeo (Gemini)"),
    "spotify_access_token": ("spotify", "Spotify (token de usuario)"),
}


def nombre_proveedor(clave_entorno: str) -> str:
    return PROVEEDORES.get(clave_entorno, (clave_entorno, clave_entorno))[0]


def cargar_desde_db(db: Session) -> dict[str, str]:
    """Descifra los secretos guardados y los deja en memoria."""
    forget_all()
    guardados: dict[str, str] = {}
    for fila in db.scalars(select(ProviderSecret)).all():
        try:
            claro = descifrar(fila.ciphertext)
        except (ClaveMaestraAusente, DescifradoImposible) as exc:
            logger.warning(
                "El secreto %s no se pudo cargar: %s", fila.provider, exc
            )
            continue
        guardar_en_memoria(fila.provider, claro)
        guardados[fila.provider] = fila.provider
    return guardados


def clave_de_proveedor(clave_entorno: str) -> str:
    """Valor efectivo de una clave: primero la bóveda, después el entorno."""
    proveedor = nombre_proveedor(clave_entorno)
    guardado = valor(proveedor)
    if guardado:
        return guardado
    return getattr(get_settings(), clave_entorno, "") or ""


def guardar_clave(db: Session, clave_entorno: str, nuevo: str) -> None:
    """Guarda un secreto cifrado en la bóveda (y lo deja en memoria)."""
    proveedor = nombre_proveedor(clave_entorno)
    cifrado = cifrar(nuevo)
    fila = db.scalar(select(ProviderSecret).where(ProviderSecret.provider == proveedor))
    if fila is None:
        fila = ProviderSecret(provider=proveedor)
        db.add(fila)
    fila.ciphertext = cifrado
    guardar_en_memoria(proveedor, nuevo)
    db.flush()


def borrar_clave(db: Session, clave_entorno: str) -> bool:
    """Borra el secreto de la bóveda. Devuelve si había algo que borrar."""
    proveedor = nombre_proveedor(clave_entorno)
    fila = db.scalar(select(ProviderSecret).where(ProviderSecret.provider == proveedor))
    olvidar(proveedor)
    if fila is None:
        return False
    db.delete(fila)
    db.flush()
    return True


def estado(db: Session) -> list[dict]:
    """Estado por proveedor: de dónde viene la clave, nunca su valor."""
    from ..vault import clave_maestra_configurada

    guardados = {
        f.provider for f in db.scalars(select(ProviderSecret)).all()
    }
    ajustes = get_settings()
    filas: list[dict] = []
    for clave_entorno, (proveedor, nombre) in PROVEEDORES.items():
        desde_vault = proveedor in guardados
        desde_entorno = bool(getattr(ajustes, clave_entorno, ""))
        filas.append(
            {
                "provider": proveedor,
                "key": clave_entorno,
                "name": nombre,
                "configured": desde_vault or desde_entorno,
                "source": "boveda" if desde_vault else ("entorno" if desde_entorno else "ninguna"),
                "vault_available": clave_maestra_configurada(),
            }
        )
    return filas
