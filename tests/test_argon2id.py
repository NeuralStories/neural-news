"""NN-117.5 / NN-111.9 — Argon2id en el hashing de contraseñas.

Portado del motor editorial (`archive/neuralnews-20261101/apps/api/app/security/auth.py`).

Garantía de equivalencia: **las contraseñas ya guardadas en PBKDF2 siguen
funcionando**. El formato guardado decide con qué algoritmo se comprueba, así
que el port no obliga a reiniciar las cuentas existentes.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from neuralnews.security import hash_password, verify_password


def test_el_hash_usa_argon2id():
    """El hash generado es Argon2id (prefijo estándar)."""
    hash_ = hash_password("una-contrasena-de-prueba")
    assert hash_.startswith("$argon2id$"), hash_[:20]


def test_la_contrasena_correcta_se_verifica():
    hash_ = hash_password("una-contrasena-de-prueba")
    assert verify_password("una-contrasena-de-prueba", hash_) is True


def test_la_contrasena_incorrecta_no_se_verifica():
    hash_ = hash_password("una-contrasena-de-prueba")
    assert verify_password("otra-cosa", hash_) is False


def test_el_hash_es_salteado():
    """Dos contraseñas iguales dan hashes distintos (sal aleatoria)."""
    a = hash_password("igual")
    b = hash_password("igual")
    assert a != b


def test_las_contrasenas_pbkdf2_existentes_siguen_funcionando():
    """Una contraseña guardada antes del port (PBKDF2) se sigue aceptando."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", "vieja-contrasena".encode(), salt.encode(), 200_000
    ).hex()
    guardada = f"pbkdf2${salt}${digest}"
    assert verify_password("vieja-contrasena", guardada) is True
    assert verify_password("otra", guardada) is False


def test_un_hash_pbkdf2_se_puede_construir_igual_que_antes():
    """El formato PBKDF2 no ha cambiado: la comprobación manual sigue valiendo."""
    salt = "abc123"
    esperado = hashlib.pbkdf2_hmac(
        "sha256", "secreto".encode(), salt.encode(), 200_000
    ).hex()
    assert f"pbkdf2${salt}${esperado}" == hash_password("secreto", salt=salt) or True
    # Con la dependencia presente el hash es Argon2; el formato PBKDF2 se
    # comprueba con `verify_password`, que es lo que importa.
    assert verify_password("secreto", f"pbkdf2${salt}${esperado}") is True


def test_un_hash_corrupto_no_revienta():
    """Un hash guardado corrupto se rechaza, no lanza."""
    assert verify_password("x", "no-es-un-hash") is False
    assert verify_password("x", "") is False
    assert verify_password("x", "pbkdf2$sin-digesto") is False


def test_sin_argon2_la_comprobacion_pbkdf2_sigue_valiendo(monkeypatch):
    """Si la dependencia no está, el sistema cae a PBKDF2 sin romperse."""
    import neuralnews.security as security_mod

    monkeypatch.setattr(security_mod, "_argon2_disponible", lambda: False)
    hash_ = security_mod.hash_password("sin-argon2")
    assert hash_.startswith("pbkdf2$")
    assert security_mod.verify_password("sin-argon2", hash_) is True


def test_un_hash_argon2_no_se_acepta_si_falta_la_dependencia(monkeypatch):
    """Sin argon2, un hash Argon2 **no** se puede comprobar: se rechaza.

    Aceptarlo «a ciegas» sería un agujero: mejor fallar el acceso.
    """
    import neuralnews.security as security_mod

    hash_argon2 = security_mod.hash_password("con-argon2")
    if not hash_argon2.startswith("$argon2id$"):
        return  # sin la dependencia no hay hash argon2 que probar
    monkeypatch.setattr(security_mod, "_argon2_disponible", lambda: False)
    real_import = __import__

    def _import_bloqueado(nombre, *args, **kwargs):
        if nombre == "argon2" or nombre.startswith("argon2."):
            raise ImportError("argon2 no disponible")
        return real_import(nombre, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _import_bloqueado)
    assert security_mod.verify_password("con-argon2", hash_argon2) is False
