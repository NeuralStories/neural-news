"""Comprobaciones de salud reales del sistema (NN-115.2).

Antes `/api/v1/health` decía «ok» sin comprobar nada: la API contestaba
igual con la base de datos caída, sin FFmpeg (el montaje no funcionaría) o sin
yt-dlp (la transcripción no funcionaría). Ahora cada dependencia se comprueba y
se informa con su estado y su motivo.

Las comprobaciones de binarios se **cachean**: lanzar `ffmpeg -version` en cada
petición de salud sería un desperdicio, y el resultado no cambia entre
arranques.
"""
from __future__ import annotations

import functools
import shutil
import subprocess


@functools.lru_cache(maxsize=1)
def _version_de(binario: str) -> tuple[bool, str]:
    """(disponible, versión) de un binario del PATH."""
    ruta = shutil.which(binario)
    if not ruta:
        return False, "no está en el PATH"
    try:
        proc = subprocess.run(
            [ruta, "-version"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"no se ha podido ejecutar: {exc}"
    primera = (proc.stdout or proc.stderr or "").splitlines()
    return True, primera[0] if primera else "versión desconocida"


@functools.lru_cache(maxsize=1)
def _binario_yt_dlp() -> tuple[bool, str]:
    """(disponible, ruta o motivo) del binario de yt-dlp."""
    try:
        from .providers.transcript import yt_dlp_binary
    except Exception as exc:  # noqa: BLE001 — la comprobación no debe romper la salud
        return False, f"no se ha podido comprobar: {exc}"
    try:
        ruta = yt_dlp_binary()
    except Exception as exc:  # noqa: BLE001
        return False, f"no se ha podido comprobar: {exc}"
    if not ruta:
        return False, "no está disponible (opcional: sólo transcripción automática)"
    return True, str(ruta)


def comprobar_salud() -> dict:
    """Estado de cada dependencia del producto."""
    from .config import get_settings
    from .services import secrets as secrets_service

    ajustes = get_settings()

    base = {"ok": True, "detalle": ""}
    try:
        from sqlalchemy import text

        from .db import session_scope

        with session_scope() as db:
            db.execute(text("SELECT 1"))
        base_de_datos = {"ok": True, "detalle": "responde"}
    except Exception as exc:  # noqa: BLE001 — la salud informa, no revienta
        base_de_datos = {"ok": False, "detalle": f"no responde: {exc}"}

    ffmpeg_ok, ffmpeg_detalle = _version_de("ffmpeg")
    ytdlp_ok, ytdlp_detalle = _binario_yt_dlp()

    proveedores = [
        {
            "key": clave,
            "configurado": bool(secrets_service.clave_de_proveedor(clave)),
        }
        for clave in secrets_service.PROVEEDORES
    ]

    return {
        "database": base_de_datos,
        "ffmpeg": {
            "ok": ffmpeg_ok,
            "detalle": ffmpeg_detalle,
            "necesario_para": "montaje con FFmpeg",
        },
        "yt_dlp": {
            "ok": ytdlp_ok,
            "detalle": ytdlp_detalle,
            "necesario_para": "transcripción automática de YouTube",
        },
        "providers": {
            "ok": True,
            "detalle": f"{sum(p['configurado'] for p in proveedores)} de {len(proveedores)} con clave",
            "items": proveedores,
        },
        "presupuesto": {
            "ok": True,
            "detalle": (
                "modo demo: los servicios de pago están bloqueados"
                if ajustes.demo_mode
                else "servicios de pago con límite diario"
            ),
        },
    }


def limpiar_cache() -> None:
    """Olvida el resultado cacheado de los binarios (lo usa la CI)."""
    _version_de.cache_clear()
    _binario_yt_dlp.cache_clear()
