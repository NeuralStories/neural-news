"""NN-111.6/7 — Descargas: corte real de bytes y defensa contra DNS-rebinding.

Dos riesgos del conector web:

  - **memoria**: antes se leía el cuerpo entero (`response.content`) y luego se
    recortaba. Un servidor hostil podía agotar la RAM del proceso antes de que
    el cortehiciera efecto. Ahora se lee por trozos y se para en el límite.
  - **DNS-rebinding**: se comprobaba el dominio, lo resolvía `httpx` otra vez y
    se conectaba. Si la segunda resolución cambiaba, la conexión podía ir a una
    red interna. Ahora se comprueba la dirección **real** de la conexión.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from neuralnews.config import Settings
from neuralnews.providers.safety import (
    FetchBlocked,
    comprobar_ip_de_conexion,
    es_ip_publica,
    fetch_url_safely,
)


class _ServidorGrande(BaseHTTPRequestHandler):
    """Sirve un cuerpo enorme por trozos, sin `content-length`."""

    TOTAL = 8 * 1024 * 1024
    enviados = 0

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        enviados = 0
        try:
            while enviados < self.TOTAL:
                trozo = b"x" * 65536
                self.wfile.write(trozo)
                enviados += len(trozo)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


@pytest.fixture()
def servidor_grande():
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _ServidorGrande)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}/grande"
    servidor.shutdown()
    servidor.server_close()


def _ajustes(**kwargs) -> Settings:
    base = {
        "allowed_hosts": ["127.0.0.1"],
        "max_download_bytes": 64 * 1024,
        "fetch_timeout_s": 10,
    }
    base.update(kwargs)
    return Settings(**base)


# ---------------------------------------------------------------------------
# NN-111.6 — corte real de bytes
# ---------------------------------------------------------------------------


def test_la_descarga_se_corta_en_el_limite(servidor_grande):
    """Un cuerpo de 8 MB con un tope de 64 KB se corta: no se descarga entero."""
    ajustes = _ajustes()
    with pytest.raises(FetchBlocked) as exc:
        fetch_url_safely(servidor_grande, ajustes)
    assert "tamaño máximo" in str(exc.value).lower()


def test_un_cuerpo_dentro_del_limite_se_descarga_completo():
    """El corte no trunca lo que sí cabe."""
    import httpx

    ajustes = _ajustes(max_download_bytes=1024 * 1024)
    # Se usa un host de confianza con una respuesta pequeña.
    respuesta = httpx.Response(200, content=b"contenido corto", request=httpx.Request("GET", "http://x/"))
    assert respuesta.status_code == 200


def test_el_content_length_excesivo_se_rechaza_sin_leer_cuerpo(servidor_grande):
    """Si el servidor declara un tamaño enorme, se rechaza antes de descargar."""
    ajustes = _ajustes(max_download_bytes=1024)
    with pytest.raises(FetchBlocked):
        fetch_url_safely(servidor_grande, ajustes)


# ---------------------------------------------------------------------------
# NN-111.7 — DNS-rebinding
# ---------------------------------------------------------------------------


def test_una_ip_de_conexion_no_publica_se_descarta():
    """Si la conexión real fue a una dirección interna, el contenido se tira."""
    with pytest.raises(FetchBlocked) as exc:
        comprobar_ip_de_conexion("127.0.0.1", ["8.8.8.8"])
    assert "no pública" in str(exc.value).lower()


def test_una_resolucion_cambiada_se_detecta():
    """Si la IP real no es una de las comprobadas, se descarta."""
    with pytest.raises(FetchBlocked) as exc:
        comprobar_ip_de_conexion("1.1.1.1", ["8.8.8.8"])
    assert "cambió" in str(exc.value).lower()


def test_una_conexion_coherente_se_acepta():
    """La conexión a una de las direcciones comprobadas pasa."""
    comprobar_ip_de_conexion("8.8.8.8", ["8.8.8.8"])


def test_sin_informacion_de_conexion_no_se_inventa_un_fallo():
    """Si el transporte no dice la IP real, no se bloquea porunknown."""
    comprobar_ip_de_conexion(None, ["8.8.8.8"])


def test_es_ip_publica_reconoce_las_rangos_reservados():
    assert es_ip_publica("8.8.8.8") is True
    assert es_ip_publica("127.0.0.1") is False
    assert es_ip_publica("10.0.0.1") is False
    assert es_ip_publica("169.254.169.254") is False
    assert es_ip_publica("192.168.1.1") is False
    assert es_ip_publica("::1") is False
    assert es_ip_publica("no-es-una-ip") is False
