"""Bóveda de secretos: cifrado autenticado con clave maestra externa a la base.

Portado del motor editorial (`archive/neuralnews-20261101/apps/api/app/security/vault.py`),
con la diferencia de que el valor descifrado se queda **en memoria** para que los
adaptadores puedan usarlo sin abrir una sesión en cada llamada.

La clave maestra llega por entorno (`NEURAL_MASTER_KEY`, formato Fernet
urlsafe-b64 de 32 bytes) y **nunca** se guarda en la base de datos ni se
devuelve por la API. Sin clave maestra, los secretos guardados quedan
`BLOCKED` y la aplicación **arranca igual** (el trabajo editorial sin secretos
sigue siendo posible).

En memoria se guardan los valores en claro: es el precio de que los adaptadores
los usen sin sesión. Por eso el proceso no debe exponerse (y la clave maestra
sólo se carga desde el entorno, nunca desde la base).
"""
from __future__ import annotations

import base64
import hashlib
import logging

logger = logging.getLogger(__name__)

CLAVE_MAESTRA = "NEURAL_MASTER_KEY"

_clave_maestra: str | None = None
_valores: dict[str, str] = {}


class ClaveMaestraAusente(Exception):
    """No hay clave maestra configurada: no se pueden cifrar ni descifrar."""


class DescifradoImposible(Exception):
    """El secreto guardado no se puede descifrar con la clave actual."""


def _derivar_clave(secret: str) -> bytes:
    """Acepta una clave Fernet ya codificada o deriva una determinista.

    La derivación (sha256 → base64) es para desarrollo; en un despliegue real
    la clave debe llegar ya codificada.
    """
    try:
        crudo = base64.urlsafe_b64decode(secret.encode("utf-8"))
        if len(crudo) == 32:
            return secret.encode("utf-8")
    except Exception:  # noqa: BLE001 — se cae a la derivación
        pass
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())


def configurar(clave: str | None) -> None:
    """Fija la clave maestra del proceso. Sin clave, la bóveda no está disponible."""
    global _clave_maestra
    _clave_maestra = clave or None


def clave_maestra_configurada() -> bool:
    return bool(_clave_maestra)


def disponible() -> bool:
    """¿Se puede cifrar/descifrar ahora mismo?"""
    if not _clave_maestra:
        return False
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return False
    return True


def _fernet():
    if not _clave_maestra:
        raise ClaveMaestraAusente(
            "No hay clave maestra configurada (NEURAL_MASTER_KEY): "
            "no se pueden guardar secretos."
        )
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover - dependencia declarada
        raise ClaveMaestraAusente(
            "Falta la dependencia 'cryptography': no se pueden guardar secretos."
        ) from exc
    return Fernet(_derivar_clave(_clave_maestra))


def cifrar(texto: str) -> str:
    """Cifra un secreto con la clave maestra."""
    return _fernet().encrypt(texto.encode("utf-8")).decode("utf-8")


def descifrar(cifrado: str) -> str:
    """Descifra un secreto. Si la clave cambió, se dice con claridad."""
    try:
        return _fernet().decrypt(cifrado.encode("utf-8")).decode("utf-8")
    except Exception as exc:  # noqa: BLE001 — InvalidToken y derivados
        logger.error("No se pudo descifrar un secreto: la clave maestra no corresponde")
        raise DescifradoImposible(
            "El secreto almacenado no se puede descifrar con la clave actual: reconfigúralo."
        ) from exc


def guardar_en_memoria(proveedor: str, valor: str) -> None:
    _valores[proveedor] = valor


def olvidar(proveedor: str) -> None:
    _valores.pop(proveedor, None)


def valor(proveedor: str) -> str | None:
    """Valor en claro cacheado en memoria para ese proveedor."""
    return _valores.get(proveedor)


def forget_all() -> None:
    _valores.clear()


def sellar() -> str:
    """Valor seguro para logs."""
    return "[REDACTED]"


def redact(valor: str | None) -> str:
    """Sustituye cualquier valor sensible por un marcador seguro (logs/GET)."""
    return "[REDACTED]" if valor else ""
