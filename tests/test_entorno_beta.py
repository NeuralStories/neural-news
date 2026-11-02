"""NN-111 — Beta-go-live: entorno, sesión y puertas de pago.

Lo que se comprueba:

  - la aplicación **no arranca** con una configuración incoherente para su
    entorno (modo demo activo en un despliegue, contraseña de ejemplo, sin
    contraseña);
  - la cookie de sesión va **segura** fuera del entorno local;
  - el acceso rápido de demostración **no existe** fuera del entorno local;
  - las rutas que necesitan un proveedor de pago **lo dicen** cuando en un
    despliegue los servicios de pago están desactivados, en lugar de encolar un
    trabajo que no podrá completarse.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from neuralnews.config import Settings, get_settings


def _settings(**kwargs) -> Settings:
    base = {
        "env": "beta",
        "demo_mode": False,
        "admin_password": "una-contrasena-larga-y-distinta",
    }
    base.update(kwargs)
    return Settings(**base)


# ---------------------------------------------------------------------------
# NN-111.1 — la configuración incoherente impide arrancar
# ---------------------------------------------------------------------------


def test_el_modo_demo_impide_arrancar_en_un_despliegue():
    s = _settings(demo_mode=True)
    with pytest.raises(RuntimeError) as exc:
        s.comprobar()
    assert "demo" in str(exc.value).lower()


def test_sin_contrasena_no_arranca_en_un_despliegue():
    s = _settings(admin_password="")
    with pytest.raises(RuntimeError) as exc:
        s.comprobar()
    assert "contraseña" in str(exc.value).lower()


def test_la_contrasena_de_ejemplo_no_arranca_en_un_despliegue():
    s = _settings(admin_password="neural-demo")
    with pytest.raises(RuntimeError) as exc:
        s.comprobar()
    assert "ejemplo" in str(exc.value).lower()


def test_un_entorno_invalido_no_arranca():
    s = _settings(env="produccion")
    with pytest.raises(RuntimeError) as exc:
        s.comprobar()
    assert "NEURAL_ENV" in str(exc.value)


def test_en_local_todo_vale():
    """El entorno local conserva el comportamiento actual: no rompe el flujo."""
    s = Settings(env="local", demo_mode=True, admin_password="")
    s.comprobar()  # no debe lanzar


def test_un_despliegue_correcto_pasa_la_comprobacion():
    _settings().comprobar()  # no debe lanzar


def test_los_entornos_validos_son_local_beta_y_prod():
    from neuralnews.config import VALID_ENVS

    assert VALID_ENVS == ("local", "beta", "prod")


# ---------------------------------------------------------------------------
# NN-111.2 — la cookie de sesión
# ---------------------------------------------------------------------------


def test_la_cookie_es_segura_fuera_del_entorno_local(monkeypatch):
    from neuralnews import security as security_mod
    from starlette.responses import Response

    monkeypatch.setattr(
        security_mod, "get_settings", lambda: _settings(env="beta")
    )
    respuesta = Response()
    security_mod.set_session_cookie(respuesta, "token-de-prueba")
    cabecera = respuesta.headers["set-cookie"]
    assert "Secure" in cabecera, "la cookie de sesión debe ir segura fuera de local"
    assert "HttpOnly" in cabecera


def test_la_cookie_no_es_segura_en_local(monkeypatch):
    from neuralnews import security as security_mod
    from starlette.responses import Response

    monkeypatch.setattr(
        security_mod, "get_settings", lambda: _settings(env="local", demo_mode=True)
    )
    respuesta = Response()
    security_mod.set_session_cookie(respuesta, "token-de-prueba")
    assert "Secure" not in respuesta.headers["set-cookie"]


def test_el_dominio_de_la_cookie_se_puede_fijar(monkeypatch):
    from neuralnews import security as security_mod
    from starlette.responses import Response

    monkeypatch.setattr(
        security_mod,
        "get_settings",
        lambda: _settings(env="beta", session_cookie_domain="neural.news"),
    )
    respuesta = Response()
    security_mod.set_session_cookie(respuesta, "token-de-prueba")
    assert "Domain=neural.news" in respuesta.headers["set-cookie"]


# ---------------------------------------------------------------------------
# NN-111.3 — las puertas
# ---------------------------------------------------------------------------


def test_el_acceso_demo_no_existe_fuera_de_local(demo_client, monkeypatch):
    """Con NEURAL_ENV=beta, `/auth/demo` responde 403 aunque el modo demo esté on."""
    from neuralnews.api import auth as auth_mod

    monkeypatch.setattr(
        auth_mod, "get_settings", lambda: _settings(env="beta", demo_mode=True)
    )
    r = demo_client.post("/api/v1/auth/demo")
    assert r.status_code == 403
    assert "local" in r.json()["detail"].lower()


def test_las_rutas_de_pago_lo_dicen_cuando_estan_desactivadas(demo_client, worker, monkeypatch):
    """En un despliegue sin servicios de pago, la ruta lo dice en voz alta."""
    from neuralnews import security as security_mod

    monkeypatch.setattr(
        security_mod,
        "get_settings",
        lambda: _settings(env="beta", paid_services_enabled=False),
    )
    demo_client.post(
        "/api/v1/sources",
        json={
            "text": "Cortexa Labs ha anunciado Radar y Vireo AI ha levantado 40 millones."
        },
    )
    worker()  # el worker extrae el candidato de la fuente
    historias = demo_client.get("/api/v1/stories").json()["items"]
    assert historias, "debe haber al menos una noticia candidata"
    story_id = historias[0]["id"]

    r = demo_client.post(f"/api/v1/stories/{story_id}/research")
    assert r.status_code == 400
    assert "pago" in r.json()["detail"].lower()


def test_configurar_el_presupuesto_con_el_modo_demo_no_silencia_nada(demo_client):
    """Con el modo demo activo, cambiar el presupuesto se rechaza en vez de
    devolver un «ok» que no surte efecto."""
    r = demo_client.put(
        "/api/v1/config/budget",
        json={"paid_services_enabled": True, "daily_limit_eur": 5},
    )
    assert r.status_code == 400
    assert "demo" in r.json()["detail"].lower()


def test_require_demo_disabled_falla_con_el_modo_demo():
    from neuralnews.security import require_demo_disabled

    with pytest.raises(HTTPException):
        require_demo_disabled(_settings(env="local", demo_mode=True))


def test_require_demo_disabled_pasa_sin_modo_demo():
    from neuralnews.security import require_demo_disabled

    require_demo_disabled(_settings(env="beta", demo_mode=False))  # no debe lanzar


def test_require_paid_services_falla_en_despliegue_sin_pago():
    from neuralnews.security import require_paid_services

    with pytest.raises(HTTPException):
        require_paid_services(_settings(env="beta", paid_services_enabled=False))


def test_require_paid_services_no_falla_en_local():
    """En local la ruta se puede usar: el modo demo responde con datos simulados."""
    from neuralnews.security import require_paid_services

    require_paid_services(_settings(env="local", demo_mode=True))  # no debe lanzar
