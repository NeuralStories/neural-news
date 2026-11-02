"""NN-115.2 — La salud informa del estado real, no sólo «la API está viva»."""
from __future__ import annotations

from neuralnews.health import comprobar_salud, limpiar_cache


def test_la_salud_informa_de_cada_dependencia(demo_client):
    """`/api/v1/health` comprueba base de datos, FFmpeg, yt-dlp y proveedores."""
    r = demo_client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    checks = body["checks"]
    for clave in ("database", "ffmpeg", "yt_dlp", "providers", "presupuesto"):
        assert clave in checks, clave
        assert "ok" in checks[clave]
        assert "detalle" in checks[clave]


def test_la_base_de_datos_se_comprueba_de_verdad(demo_client):
    """La comprobación de la base de datos es real: responde a una consulta."""
    checks = comprobar_salud()
    assert checks["database"]["ok"] is True
    assert checks["database"]["detalle"]


def test_el_entorno_aparece_en_la_salud(demo_client):
    """La salud dice en qué entorno se está corriendo."""
    assert demo_client.get("/api/v1/health").json()["env"]


def test_los_binarios_se_avisan_si_no_estan(demo_client, monkeypatch):
    """Si FFmpeg no está, se dice con claridad en vez de callar."""
    from neuralnews import health

    health.limpiar_cache()
    monkeypatch.setattr(health.shutil, "which", lambda _b: None)
    checks = health.comprobar_salud()
    health.limpiar_cache()
    assert checks["ffmpeg"]["ok"] is False
    assert "PATH" in checks["ffmpeg"]["detalle"]


def test_los_proveedores_informan_de_cuantas_claves_hay(demo_client):
    """El bloque de proveedores dice cuántas claves hay configuradas."""
    checks = comprobar_salud()
    proveedores = checks["providers"]["items"]
    assert proveedores
    assert all("configurado" in p for p in proveedores)
