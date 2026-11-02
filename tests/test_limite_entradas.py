"""NN-111.10 — Límite de intentos de entrada (fuerza bruta)."""
from __future__ import annotations

import pytest

from neuralnews.rate_limit import DemasiadosIntentos, RateLimiter


def test_el_limite_permite_los_intentos_hasta_el_maximo():
    limitador = RateLimiter(max_attempts=3, window_s=60, cooldown_s=60)
    for _ in range(3):
        limitador.registrar_fallo("1.2.3.4")
    with pytest.raises(DemasiadosIntentos):
        limitador.comprobar("1.2.3.4")


def test_el_limite_no_afecta_a_otras_direcciones():
    limitador = RateLimiter(max_attempts=2, window_s=60, cooldown_s=60)
    limitador.registrar_fallo("1.2.3.4")
    limitador.registrar_fallo("1.2.3.4")
    with pytest.raises(DemasiadosIntentos):
        limitador.comprobar("1.2.3.4")
    limitador.comprobar("5.6.7.8")  # no debe lanzar


def test_un_acierto_limpia_el_contador():
    limitador = RateLimiter(max_attempts=3, window_s=60, cooldown_s=60)
    limitador.registrar_fallo("1.2.3.4")
    limitador.registrar_exito("1.2.3.4")
    limitador.registrar_fallo("1.2.3.4")
    limitador.comprobar("1.2.3.4")  # no debe lanzar


def test_los_fallos_antiguos_se_olvidan():
    """Fuera de la ventana, los fallos anteriores no cuentan."""
    import time

    limitador = RateLimiter(max_attempts=2, window_s=0.05, cooldown_s=60)
    limitador.registrar_fallo("1.2.3.4")
    time.sleep(0.08)
    limitador.registrar_fallo("1.2.3.4")
    limitador.comprobar("1.2.3.4")  # no debe lanzar


def test_la_api_responde_429_despues_de_varios_fallos(demo_client, monkeypatch):
    """La entrada real se bloquea tras varios intentos fallidos."""
    from neuralnews.api import auth as auth_mod
    from neuralnews.rate_limit import RateLimiter

    monkeypatch.setattr(auth_mod, "limitador_entradas", RateLimiter(max_attempts=2, window_s=60, cooldown_s=60))
    monkeypatch.setattr(auth_mod, "_admin_password_hash", lambda: "pbkdf2$sal$hash")

    cuerpo = {"username": "editor", "password": "incorrecta"}
    for _ in range(2):
        r = demo_client.post("/api/v1/auth/login", json=cuerpo)
        assert r.status_code == 401

    r = demo_client.post("/api/v1/auth/login", json=cuerpo)
    assert r.status_code == 429
    assert "intentos" in r.json()["detail"].lower()
