"""Errores aptos para mostrarse al cliente o guardarse en la base de datos.

Regla (hallazgo B7): el texto crudo de una excepción puede contener rutas del
sistema, secretos o la salida de herramientas externas. Al navegador y a la
tabla de trabajos solo llega un resumen; el detalle completo va al log.
"""
from __future__ import annotations

import re

# Rutas absolutas de Windows y POSIX. El `(?<![:\w])` evita que se confunda un
# fragmento de ruta con una fecha ("12/03/2026") o con el camino de una URL.
_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s'\"]+|(?<![:\w])/(?:[\w.\-]+/)+[\w.\-]*")
# Credenciales con forma clave=valor.
_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|passwd|bearer)\b\s*[:=]\s*\S+"
)
# Direcciones de correo.
_EMAIL_RE = re.compile(r"[\w.\-]+@[\w.\-]+\.\w+")


def safe_error(exc: BaseException, *, max_length: int = 240) -> str:
    """Resume una excepción en una línea, sin rutas, secretos ni trazas.

    Conserva el nombre de la clase y el mensaje: quien lee el trabajo sigue
    sabiendo qué falló, pero sin las rutas del servidor ni las claves.
    """
    message = str(exc).strip()
    if message:
        message = message.splitlines()[0]
    message = _PATH_RE.sub("<ruta>", message)
    message = _SECRET_RE.sub(lambda m: f"{m.group(1)}=<oculto>", message)
    message = _EMAIL_RE.sub("<correo>", message)
    message = message.strip()
    if len(message) > max_length:
        message = message[: max_length - 1].rstrip() + "…"
    name = type(exc).__name__
    return f"{name}: {message}" if message else name


# ---------------------------------------------------------------------------
# Motivo normalizado del fallo (NN-110.e)
# ---------------------------------------------------------------------------
#
# El motivo se registra CUANDO ocurre el fallo, no se deduce después del texto:
# adivinarlo por el mensaje es frágil y mezcla «presupuesto» con «conector».

ERROR_KIND_LABELS: dict[str, str] = {
    "budget": "Presupuesto agotado",
    "connector": "Fallo del conector",
    "material": "Falta material",
    "interrupted": "Trabajo interrumpido",
    "timeout": "Tiempo agotado",
    "unknown": "Motivo desconocido",
}


def error_kind_label(kind: str | None) -> str:
    """Etiqueta legible del motivo normalizado."""
    if not kind:
        return ""
    return ERROR_KIND_LABELS.get(kind, kind)


class MaterialFaltante(RuntimeError):
    """El trabajo no puede ejecutarse porque falta material (tomas sin MP4, etc.).

    No tiene sentido reintentar: reintentar sin material da el mismo resultado.
    """

    kind = "material"


class ConectorFallido(RuntimeError):
    """Un proveedor externo falló (red, credenciales, formato de la respuesta).

    Suele ser transitorio: se reintenta y se registra el motivo «conector».
    """

    kind = "connector"
