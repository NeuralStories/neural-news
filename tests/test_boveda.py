"""NN-117.3 — Bóveda de secretos: cifrado, resolución y API.

Portado del motor editorial (`archive/neuralnews-20261101/apps/api/app/security/vault.py`).

Lo que se comprueba:

  - en la base de datos **no** hay ningún valor en claro;
  - la resolución efectiva es «bóveda primero, entorno después»;
  - la API **nunca** devuelve el valor, sólo si está configurado y de dónde viene;
  - sin clave maestra la aplicación **arranca igual** y lo que dependa de un
    secreto queda bloqueado con un motivo claro.
"""
from __future__ import annotations

import base64
import hashlib

import pytest
from sqlalchemy import select

from neuralnews import vault
from neuralnews.models import ProviderSecret
from neuralnews.services import secrets as secrets_service

CLAVE = base64.urlsafe_b64encode(hashlib.sha256(b"clave-maestra-de-prueba").digest()).decode()


@pytest.fixture()
def boveda_lista():
    vault.configurar(CLAVE)
    vault.forget_all()
    yield
    vault.configurar(None)
    vault.forget_all()


# ---------------------------------------------------------------------------
# Cifrado
# ---------------------------------------------------------------------------


def test_el_secreto_cifrado_no_contiene_el_valor(boveda_lista):
    cifrado = vault.cifrar("mi-clave-secreta")
    assert "mi-clave-secreta" not in cifrado
    assert vault.descifrar(cifrado) == "mi-clave-secreta"


def test_el_mismo_valor_cifra_distinto_cada_vez(boveda_lista):
    assert vault.cifrar("x") != vault.cifrar("x")


def test_sin_clave_maestra_no_se_puede_cifrar():
    vault.configurar(None)
    with pytest.raises(vault.ClaveMaestraAusente):
        vault.cifrar("secreto")


def test_una_clave_distinta_no_puede_descifrar(boveda_lista):
    cifrado = vault.cifrar("secreto")
    otra = base64.urlsafe_b64encode(hashlib.sha256(b"otra-clave").digest()).decode()
    vault.configurar(otra)
    with pytest.raises(vault.DescifradoImposible):
        vault.descifrar(cifrado)


def test_redact_oculta_el_valor():
    assert vault.redact("secreto") == "[REDACTED]"
    assert vault.redact(None) == ""


# ---------------------------------------------------------------------------
# Resolución efectiva: bóveda primero, entorno después
# ---------------------------------------------------------------------------


def test_la_boveda_tiene_prioridad_sobre_el_entorno(demo_client, boveda_lista):
    with demo_client.app.state.db if False else _sesion() as db:
        secrets_service.guardar_clave(db, "llm_api_key", "desde-la-boveda")
        db.commit()
    assert secrets_service.clave_de_proveedor("llm_api_key") == "desde-la-boveda"


def test_sin_boveda_se_usa_el_entorno(demo_client):
    vault.forget_all()
    valor = secrets_service.clave_de_proveedor("llm_api_key")
    # El entorno de pruebas no define claves: el valor efectivo es vacío.
    assert valor == ""


def test_borrar_la_clave_vuelve_al_entorno(demo_client, boveda_lista):
    with _sesion() as db:
        secrets_service.guardar_clave(db, "llm_api_key", "en-la-boveda")
        db.commit()
        assert secrets_service.borrar_clave(db, "llm_api_key") is True
        db.commit()
    assert secrets_service.clave_de_proveedor("llm_api_key") == ""


def test_en_la_base_de_datos_no_hay_valor_en_claro(demo_client, boveda_lista):
    with _sesion() as db:
        secrets_service.guardar_clave(db, "llm_api_key", "VALOR-SUPER-SECRETO")
        db.commit()
    with _sesion() as db:
        filas = db.scalars(select(ProviderSecret)).all()
        assert filas, "el secreto debería estar guardado"
        for fila in filas:
            assert "VALOR-SUPER-SECRETO" not in fila.ciphertext


def test_cargar_desde_db_recupera_los_secretos(demo_client, boveda_lista):
    with _sesion() as db:
        secrets_service.guardar_clave(db, "search_api_key", "clave-de-busqueda")
        db.commit()
    vault.forget_all()
    with _sesion() as db:
        secrets_service.cargar_desde_db(db)
    assert secrets_service.clave_de_proveedor("search_api_key") == "clave-de-busqueda"


# ---------------------------------------------------------------------------
# La API
# ---------------------------------------------------------------------------


def test_la_api_no_devuelve_el_valor(demo_client, boveda_lista, monkeypatch):
    """La API informa de que hay clave y de dónde viene, nunca del valor."""
    monkeypatch.setattr(vault, "clave_maestra_configurada", lambda: True)
    with _sesion() as db:
        secrets_service.guardar_clave(db, "llm_api_key", "VALOR-QUE-NO-DEBE-SALIR")
        db.commit()

    r = demo_client.get("/api/v1/config/secrets")
    assert r.status_code == 200
    cuerpo = r.text
    assert "VALOR-QUE-NO-DEBE-SALIR" not in cuerpo
    llm = next(p for p in r.json()["providers"] if p["key"] == "llm_api_key")
    assert llm["configured"] is True
    assert llm["source"] == "boveda"


def test_guardar_un_secreto_requiere_clave_maestra(client, monkeypatch):
    """Sin clave maestra se dice con claridad, en vez de fallar sin explicación."""
    from neuralnews import security as security_mod

    # Sesión real de editor (no demo): la puerta de demo y la de sesión demo
    # saltarían antes (y bien).
    login = client.post(
        "/api/v1/auth/login", json={"username": "editor", "password": "test-password"}
    )
    assert login.status_code == 200, login.text

    class _Ajustes:
        demo_mode = False
        es_despliegue = False
        paid_services_enabled = False

    monkeypatch.setattr(security_mod, "get_settings", lambda: _Ajustes())
    monkeypatch.setattr(vault, "clave_maestra_configurada", lambda: False)

    r = client.put("/api/v1/config/secrets/llm_api_key", json={"value": "x"})
    assert r.status_code == 503
    assert "MASTER_KEY" in r.json()["detail"]


def test_una_clave_desconocida_se_rechaza(demo_client):
    r = demo_client.put("/api/v1/config/secrets/inventada", json={"value": "x"})
    assert r.status_code == 404


def test_en_demo_no_se_guardan_secretos(demo_client):
    """En modo demo el cambio no surtiría efecto: se rechaza."""
    r = demo_client.put("/api/v1/config/secrets/llm_api_key", json={"value": "x"})
    assert r.status_code == 400
    assert "demo" in r.json()["detail"].lower()


def _sesion():
    from neuralnews.db import get_session_factory

    return get_session_factory()()
