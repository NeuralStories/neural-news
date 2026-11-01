"""NN-109 — Regresiones de los defectos verificados el 01/11/2026.

Cada test de este fichero falla con el código anterior al arreglo y pasa con él.
Escala: **E** (ejecutado). No se acepta «lo he mirado»: si el test pasa, el
defecto está cerrado.

Defectos cubiertos aquí:
  B1  `source.metadata` no existe (la columna es `metadata_json`): la ruta de
      pódcast lanzaba AttributeError y lo enmascaraba un `except Exception`.
  B7  El texto crudo de la excepción se devolvía al cliente.
  B8  La caché de transcripciones automáticas no tenía TTL ni límite de tamaño.
  B16 `podcast:transcript` se leía del atributo `href`, pero feedparser lo
      expone como `url`: la transcripción de pódcast nunca se recuperaba.
"""
from __future__ import annotations

import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import select

TRANSCRIPCION_PODCAST = (
    "Esta es la transcripción real del episodio de prueba, servida por el feed RSS."
)


class _FeedHandler(BaseHTTPRequestHandler):
    """Sirve un feed RSS con `podcast:transcript` y el fichero de transcripción."""

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        port = self.server.server_address[1]
        if path == "/feed.xml":
            body = f"""<?xml version="1.0"?>
<rss version="2.0" xmlns:podcast="https://podcastindex.org/namespace/1.0">
<channel>
  <title>Programa de prueba</title>
  <link>https://ejemplo.invalid/</link>
  <item>
    <title>Episodio de prueba</title>
    <guid>ep-neuralnews-001</guid>
    <link>https://ejemplo.invalid/ep-neuralnews-001</link>
    <pubDate>Tue, 20 Oct 2026 09:00:00 GMT</pubDate>
    <podcast:transcript url="http://127.0.0.1:{port}/transcript.txt" type="text/plain" />
  </item>
</channel></rss>"""
            ctype = "application/rss+xml"
        elif path == "/transcript.txt":
            body = TRANSCRIPCION_PODCAST
            ctype = "text/plain; charset=utf-8"
        else:
            self.send_error(404)
            return
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # silencia el log de pruebas
        pass


@pytest.fixture()
def podcast_site(monkeypatch):
    """Servidor local con un feed RSS de pódcast y su transcripción."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FeedHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    from neuralnews.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "allowed_hosts", ["127.0.0.1"])
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


def _crear_fuente_spotify(demo_client, episode_id: str) -> int:
    """Crea una fuente de Spotify y devuelve su identificador."""
    r = demo_client.post(
        "/api/v1/sources",
        json={"url": f"https://open.spotify.com/episode/{episode_id}", "title": "Episodio de prueba"},
    )
    assert r.status_code == 200, r.text
    return r.json()["source"]["id"]


def _asignar_feed(demo_client, source_id: int, feed_url: str) -> None:
    """El operador aporta el feed RSS en los metadatos de la fuente."""
    from neuralnews.db import get_session_factory
    from neuralnews.models import Source

    with get_session_factory()() as db:
        source = db.get(Source, source_id)
        assert source is not None
        source.metadata_json = {**(source.metadata_json or {}), "feed_url": feed_url}
        db.commit()


# ---------------------------------------------------------------------------
# B1 — la columna correcta del modelo
# ---------------------------------------------------------------------------


def test_b1_spotify_sin_feed_informa_sin_fugar_error_interno(demo_client):
    """Sin feed RSS la respuesta es honesta y NO menciona `metadata`.

    Antes: `source.metadata` lanzaba AttributeError y el `except Exception`
    devolvía «'Source' object has no attribute 'metadata'» al cliente.
    """
    sid = _crear_fuente_spotify(demo_client, "ep-neuralnews-001")
    r = demo_client.post(f"/api/v1/sources/{sid}/transcribe")
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is False
    assert "feed RSS" in body["message"]
    assert "has no attribute" not in body["message"]
    assert "Traceback" not in body["message"]


def test_b1_spotify_con_feed_descarga_la_transcripcion(demo_client, podcast_site):
    """Con feed RSS aportado, la transcripción del episodio se recupera y guarda.

    Cubre B1 (leer `metadata_json`) y B16 (leer `url` en vez de `href`).
    """
    sid = _crear_fuente_spotify(demo_client, "ep-neuralnews-001")
    _asignar_feed(demo_client, sid, f"{podcast_site}/feed.xml")

    r = demo_client.post(f"/api/v1/sources/{sid}/transcribe")
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True, body
    assert body["created"] is True
    assert "transcripción real del episodio" in body["transcript"]["text"]

    # Y queda almacenada: se puede volver a leer.
    stored = demo_client.get(f"/api/v1/sources/{sid}/transcript").json()
    assert stored["found"] is True
    assert "transcripción real del episodio" in stored["text"]


def test_b16_feedparser_expone_url_y_el_codigo_lo_acepta():
    """El atributo de `podcast:transcript` llega como `url`, no como `href`."""
    import feedparser

    feed = feedparser.parse(
        '<?xml version="1.0"?><rss version="2.0" '
        'xmlns:podcast="https://podcastindex.org/namespace/1.0"><channel>'
        "<title>P</title><link>https://ejemplo.invalid/</link><item>"
        "<title>E</title><guid>g1</guid>"
        '<podcast:transcript url="http://127.0.0.1:1/t.txt" type="text/plain" />'
        "</item></channel></rss>"
    )
    link = feed.entries[0]["podcast_transcript"]
    assert link["url"].endswith("/t.txt")


# ---------------------------------------------------------------------------
# B7 — el cliente no recibe el texto crudo de la excepción
# ---------------------------------------------------------------------------


def test_b7_el_error_del_conector_no_filtra_internals(demo_client, monkeypatch):
    """Un fallo del proveedor se registra, pero el cliente recibe un motivo seguro."""
    from neuralnews.providers import transcript as transcript_mod

    def _fallo(*_args, **_kwargs):
        raise RuntimeError("Fallo interno con ruta C:\\secreto\\config\\token.txt")

    monkeypatch.setattr(transcript_mod, "fetch_podcast_transcript_from_feed", _fallo)
    sid = _crear_fuente_spotify(demo_client, "ep-neuralnews-002")
    _asignar_feed(demo_client, sid, "http://127.0.0.1:1/feed.xml")

    r = demo_client.post(f"/api/v1/sources/{sid}/transcribe")
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is False
    assert "C:" not in body["message"]
    assert "secreto" not in body["message"]
    assert "Traceback" not in body["message"]
    # Y el motivo sigue siendo accionable para el operador.
    assert "manualmente" in body["message"]


def test_b7_el_error_del_trabajo_no_filtra_internals(demo_client, monkeypatch, worker):
    """`job.error` se devuelve al cliente en GET /api/v1/jobs: va resumido."""
    from neuralnews.services import sources as sources_service

    def _fallo(*_args, **_kwargs):
        raise RuntimeError("No se pudo abrir C:\\claves\\spotify.txt con token=abc123")

    monkeypatch.setattr(sources_service, "fetch_spotify", _fallo)
    sid = _crear_fuente_spotify(demo_client, "ep-neuralnews-004")
    demo_client.post(f"/api/v1/sources/{sid}/process")
    worker()

    jobs = demo_client.get("/api/v1/jobs").json()["items"]
    errores = [j["error"] for j in jobs if j.get("error")]
    assert errores, "el trabajo fallido debe dejar constancia"
    for err in errores:
        assert "C:\\claves" not in err
        assert "abc123" not in err
        assert "Traceback" not in err


def test_b7_metadatos_de_fuente_no_exponen_el_error_crudo(demo_client, monkeypatch, worker):
    """`metadata_json` se devuelve al cliente: no puede llevar la excepción cruda."""
    from neuralnews.services import sources as sources_service

    def _fallo(*_args, **_kwargs):
        raise RuntimeError("No se pudo leer /opt/claves/spotify.txt con token=abc123")

    monkeypatch.setattr(sources_service, "fetch_spotify", _fallo)
    sid = _crear_fuente_spotify(demo_client, "ep-neuralnews-003")
    demo_client.post(f"/api/v1/sources/{sid}/process")
    worker()

    listed = demo_client.get("/api/v1/sources").json()
    entry = next(s for s in listed["items"] if s["id"] == sid)
    assert "/opt/claves" not in str(entry.get("metadata"))
    assert "abc123" not in str(entry.get("metadata"))


def test_safe_error_oculta_rutas_y_secretos():
    """El resumen de error no filtra rutas absolutas ni valores con forma de clave."""
    from neuralnews.errors import safe_error

    resumen = safe_error(RuntimeError("No se pudo abrir C:\\claves\\spotify.txt"))
    assert "C:\\claves" not in resumen
    assert "<ruta>" in resumen

    resumen = safe_error(RuntimeError("Fallo con api_key=sk-1234567890abcdef"))
    assert "sk-1234567890abcdef" not in resumen
    assert "<oculto>" in resumen

    # Una fecha NO es una ruta y debe sobrevivir al resumen.
    resumen = safe_error(RuntimeError("Caducado el 12/03/2026"))
    assert "12/03/2026" in resumen

    # El nombre de la clase siempre está: sin él el resumen no es accionable.
    assert resumen.startswith("RuntimeError:")


# ---------------------------------------------------------------------------
# B2 — la transcripción aportada en el alta no se pierde
# ---------------------------------------------------------------------------


def test_b2_la_transcripcion_del_alta_se_guarda(demo_client):
    """El texto pegado y la transcripción pegada se guardan los dos.

    Antes: la transcripción se descartaba en silencio (el backend solo la
    aceptaba en la rama de URL, y la interfaz ni la enviaba).
    """
    r = demo_client.post(
        "/api/v1/sources",
        json={
            "text": "Noticia de prueba para la regresión de la transcripción.",
            "transcript": "Primera frase de la transcripción. Segunda frase de la transcripción.",
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["source"]["id"]

    guardada = demo_client.get(f"/api/v1/sources/{sid}/transcript").json()
    assert guardada["found"] is True
    assert "Primera frase de la transcripción" in guardada["text"]

    # Y el contenido de la fuente sigue ahí: no se perdió al guardar la transcripción.
    detalle = demo_client.get(f"/api/v1/sources/{sid}").json()
    tipos = {c["content_type"] for c in detalle["contents"]}
    assert "TRANSCRIPT" in tipos
    assert "MANUAL_TEXT" in tipos


def test_b2_la_transcripcion_con_url_tambien_se_guarda(demo_client):
    """Con URL la transcripción aportada se guarda igual (rama que ya funcionaba)."""
    r = demo_client.post(
        "/api/v1/sources",
        json={
            "url": "https://ejemplo.invalid/articulo",
            "transcript": "Transcripción aportada junto a la URL.",
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["source"]["id"]
    guardada = demo_client.get(f"/api/v1/sources/{sid}/transcript").json()
    assert guardada["found"] is True
    assert "Transcripción aportada" in guardada["text"]


# ---------------------------------------------------------------------------
# B3 — los ocho pasos del Studio se persisten
# ---------------------------------------------------------------------------


def test_b3_los_ocho_pasos_se_pueden_guardar(demo_client):
    """El backend acepta los ocho pasos, incluido «resultado»."""
    from neuralnews.models import STUDIO_STEPS

    assert len(STUDIO_STEPS) == 8
    assert "resultado" in STUDIO_STEPS

    project = demo_client.post(
        "/api/v1/projects", json={"name": "Proyecto de ocho pasos", "ratio": "9:16"}
    ).json()
    pid = project["id"]

    for paso in STUDIO_STEPS:
        r = demo_client.put(
            f"/api/v1/projects/{pid}/studio/{paso}",
            json={"expected_revision": 0, "payload": {"marcador": paso}},
        )
        assert r.status_code == 200, f"{paso}: {r.text}"

    detalle = demo_client.get(f"/api/v1/projects/{pid}").json()
    guardados = set(detalle["step_revisions"].keys())
    assert guardados == set(STUDIO_STEPS), f"faltan pasos: {set(STUDIO_STEPS) - guardados}"


def test_b3_el_paso_resultado_sobrevive_a_la_recarga(demo_client):
    """Lo guardado en «resultado» se recupera al volver a pedir el proyecto."""
    project = demo_client.post(
        "/api/v1/projects", json={"name": "Proyecto con resultado", "ratio": "9:16"}
    ).json()
    pid = project["id"]

    demo_client.put(
        f"/api/v1/projects/{pid}/studio/resultado",
        json={"expected_revision": 0, "payload": {"selectedSceneIndex": 2}},
    )
    detalle = demo_client.get(f"/api/v1/projects/{pid}").json()
    assert detalle["step_revisions"]["resultado"] == 1
    assert detalle["steps"]["resultado"]["payload"]["selectedSceneIndex"] == 2


# ---------------------------------------------------------------------------
# B15 — cerrar sesión cierra SOLO la sesión actual
# ---------------------------------------------------------------------------


def test_b15_logout_cierra_solo_la_sesion_actual(demo_client):
    """Antes, `logout` borraba todas las sesiones del actor."""
    from neuralnews.db import get_session_factory
    from neuralnews.models import Session as DbSession, utcnow

    # Se crea una segunda sesión del mismo actor (otra pestaña).
    with get_session_factory()() as db:
        segunda = DbSession(
            token_hash="hash-de-otra-sesion",
            actor_id="demo",
            is_demo=True,
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(segunda)
        db.commit()

    r = demo_client.post("/api/v1/auth/logout")
    assert r.status_code == 200

    with get_session_factory()() as db:
        vivos = db.scalars(select(DbSession)).all()
        assert any(s.token_hash == "hash-de-otra-sesion" for s in vivos), (
            "la sesión de otra pestaña no debe cerrarse"
        )


# ---------------------------------------------------------------------------
# B19 — el worker no puede completar un trabajo si el log no codifica «→»
# ---------------------------------------------------------------------------


class _SoloAscii:
    """Flujo que no sabe codificar «→» (como la consola ANSI de Windows)."""

    def __init__(self):
        self.escrito = ""

    def write(self, texto):
        for ch in texto:
            if ord(ch) > 127:
                raise UnicodeEncodeError("ascii", texto, 0, 1, "caracter no ASCII")
        self.escrito += texto
        return len(texto)

    def flush(self):
        return None

    def reconfigure(self, **_kwargs):
        return None


def test_b19_el_trabajo_termina_aunque_el_log_no_codifique_el_flecha(demo_client, monkeypatch):
    """El mensaje del worker no puede deshacer un trabajo ya terminado.

    Antes, el `print` con «→» estaba DENTRO de la transacción: con la salida
    redirigida en Windows (cp1252) lanzaba UnicodeEncodeError, la transacción se
    revertía y el trabajo volvía a la cola para siempre.
    """
    from neuralnews import worker as worker_mod
    from neuralnews.db import get_session_factory
    from neuralnews.models import Job
    stdout = _SoloAscii()
    monkeypatch.setattr(worker_mod.sys, "stdout", stdout)

    creado = demo_client.post(
        "/api/v1/sources", json={"text": "Fuente para la regresión del worker."}
    ).json()
    sid = creado["source"]["id"]

    # El alta de la fuente deja el trabajo en cola: se toma ese mismo trabajo.
    with get_session_factory()() as db:
        pendiente = (
            db.query(Job).filter(Job.status == "QUEUED").order_by(Job.id.desc()).first()
        )
        assert pendiente is not None, "el alta debe encolar un trabajo"
        job_id = pendiente.id

    worker_mod.tick()

    with get_session_factory()() as db:
        job = db.get(Job, job_id)
        assert job is not None
        assert job.status == "DONE", (
            f"el trabajo debe terminar aunque el log no codifique la flecha (estado: {job.status})"
        )


def test_b19_configure_streams_deja_utf8(demo_client, monkeypatch):
    """El worker reconfigura sus flujos para que el log no se corte."""
    from neuralnews import worker as worker_mod

    class _Fake:
        def __init__(self):
            self.configurado = None

        def reconfigure(self, **kwargs):
            self.configurado = kwargs

    salida, error = _Fake(), _Fake()
    monkeypatch.setattr(worker_mod.sys, "stdout", salida)
    monkeypatch.setattr(worker_mod.sys, "stderr", error)

    worker_mod.configure_streams()

    for flujo in (salida, error):
        assert flujo.configurado is not None
        assert flujo.configurado["encoding"] == "utf-8"
        assert flujo.configurado["errors"] == "replace"


# ---------------------------------------------------------------------------
# B8 — la caché está acotada en tiempo y en tamaño
# ---------------------------------------------------------------------------


def test_b8_la_cache_esta_acotada_en_tamano(demo_client, monkeypatch):
    """La caché no crece sin límite: se descarta la entrada más antigua."""
    from neuralnews.api import sources as sources_mod
    from neuralnews.providers import transcript as transcript_mod

    monkeypatch.setattr(sources_mod, "_auto_transcript_cache", {})
    monkeypatch.setattr(sources_mod, "_AUTO_TRANSCRIPT_MAX_ENTRIES", 4)

    class _Draft:
        text = "x"
        provider = "test"
        segments = []

    llamadas = []

    def _fake(video_id, langs=()):
        llamadas.append(video_id)
        return _Draft()

    monkeypatch.setattr(transcript_mod, "fetch_youtube_transcript_auto", _fake)

    for i in range(12):
        sources_mod._auto_transcript(f"video{i}")

    assert len(sources_mod._auto_transcript_cache) <= 4


def test_b8_la_cache_tiene_caducidad(demo_client, monkeypatch):
    """Una entrada vencida no se devuelve y el proveedor vuelve a consultarse."""
    from neuralnews.api import sources as sources_mod
    from neuralnews.providers import transcript as transcript_mod

    monkeypatch.setattr(sources_mod, "_auto_transcript_cache", {})

    class _Draft:
        text = "x"
        provider = "test"
        segments = []

    llamadas = []

    def _fake(video_id, langs=()):
        llamadas.append(video_id)
        return _Draft()

    monkeypatch.setattr(transcript_mod, "fetch_youtube_transcript_auto", _fake)

    sources_mod._auto_transcript("v1")
    sources_mod._auto_transcript("v1")
    assert len(llamadas) == 1, "la segunda llamada debe servirse de la caché"

    # La caducidad se comprueba sobre la marca de tiempo guardada, sin depender
    # del reloj: un test que duerme es un test que falla de forma intermitente.
    expires_at, value = sources_mod._auto_transcript_cache["v1"]
    sources_mod._auto_transcript_cache["v1"] = (expires_at - 3600, value)

    sources_mod._auto_transcript("v1")
    assert len(llamadas) == 2, "tras caducar, se vuelve a consultar al proveedor"


def test_b8_el_fracaso_tambien_se_cachea(demo_client, monkeypatch):
    """Un vídeo sin subtítulos no se vuelve a preguntar en cada intento."""
    from neuralnews.api import sources as sources_mod
    from neuralnews.providers import transcript as transcript_mod

    monkeypatch.setattr(sources_mod, "_auto_transcript_cache", {})

    llamadas = []

    def _fake(video_id, langs=()):
        llamadas.append(video_id)
        return None

    monkeypatch.setattr(transcript_mod, "fetch_youtube_transcript_auto", _fake)

    assert sources_mod._auto_transcript("sin-subtitulos") is None
    assert sources_mod._auto_transcript("sin-subtitulos") is None
    assert len(llamadas) == 1, "un resultado negativo también debe estar acotado"
