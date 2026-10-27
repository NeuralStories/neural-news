"""Etapa 2 — conectores: YouTube, Spotify, manual, web/RSS real (servidor local) y seguridad SSRF."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from neuralnews.providers.manual import fetch_manual, normalize_input
from neuralnews.providers.safety import FetchBlocked, assert_public_host, fetch_url_safely
from neuralnews.providers.spotify import extract_episode_id, extract_show_id, fetch_spotify
from neuralnews.providers.web_rss import detect_platform, extract_article, fetch_web
from neuralnews.providers.youtube import extract_video_id, fetch_youtube
from neuralnews.providers.fixtures import DEMO_HOSTILE_TEXT

ARTICLE_HTML = """<!doctype html><html><head>
<title>Artículo de prueba local</title>
<meta name="author" content="Autor de Prueba">
<meta property="article:published_time" content="2026-10-20T09:00:00Z">
<link rel="canonical" href="https://ejemplo.invalid/articulo-original">
</head><body><nav>Menú</nav><article>
<h2>Titular de la noticia de prueba</h2>
<p>El laboratorio ficticio Cortexa Labs ha anunciado Radar, su modelo multimodal de prueba.
Según la ficha técnica, mejora un 12% el razonamiento visual.</p>
<p>El acceso se limita a una lista de espera para una demo web, sin fecha de disponibilidad.</p>
<script>alert('esto no debe ejecutarse')</script>
</article></body></html>"""

RSS_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Feed de prueba</title><link>https://ejemplo.invalid/</link>
<item>
  <title>Elemento del feed sobre Vireo AI</title>
  <link>https://ejemplo.invalid/item-1</link>
  <guid>item-1</guid>
  <pubDate>Tue, 20 Oct 2026 09:00:00 GMT</pubDate>
  <description>&lt;p&gt;Vireo AI levanta 40 millones en una ronda confirmada.&lt;/p&gt;</description>
</item>
</channel></rss>"""


class _Handler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, str]] = {}

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path in self.routes:
            status, body = self.routes[path]
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if path.endswith(".html") or path == "/" else "application/rss+xml")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def log_message(self, *args):  # silencia el log de pruebas
        pass


@pytest.fixture()
def local_site(monkeypatch):
    """Servidor HTTP local (allowlist explícita de 127.0.0.1) con rutas de prueba."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    from neuralnews.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "allowed_hosts", ["127.0.0.1"])
    yield f"http://127.0.0.1:{port}", _Handler.routes
    server.shutdown()
    server.server_close()


# ------------------------------------------------------------------ detección
def test_platform_detection():
    assert detect_platform("https://youtu.be/abc12345678") == "youtube"
    assert detect_platform("https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk") == "spotify"
    assert detect_platform("https://example.org/blog/post") == "web_rss"
    assert detect_platform("no-es-una-url") is None


def test_youtube_id_extraction():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://vimeo.com/12345") is None


def test_spotify_id_extraction():
    assert extract_episode_id("https://open.spotify.com/episode/EP123?si=x") == "EP123"
    assert extract_episode_id("https://open.spotify.com/intl-es/episode/EP456") == "EP456"
    assert extract_show_id("https://open.spotify.com/show/SHOW1") == "SHOW1"
    assert extract_episode_id("https://open.spotify.com/show/SHOW1") is None


# ------------------------------------------------------------------ YouTube demo
def test_youtube_demo_returns_analysis_and_simulated_transcript():
    result = fetch_youtube("https://youtu.be/abc12345678", demo=True)
    assert result.status == "READY"
    types = {c.content_type for c in result.contents}
    assert "VIDEO_ANALYSIS" in types
    assert "TRANSCRIPT" in types
    for content in result.contents:
        # Nada del modo demo se presenta como transcripción literal real.
        assert content.is_verbatim is False or content.provider == "manual"
        if content.content_type == "VIDEO_ANALYSIS":
            assert "no es una transcripción literal" in content.text
    assert result.metadata["demo"] is True


def test_youtube_real_without_key_explains_error():
    result = fetch_youtube("https://youtu.be/abc12345678", demo=False)
    assert result.status == "FAILED"
    assert "NEURAL_YOUTUBE_API_KEY" in result.error


# ------------------------------------------------------------------ Spotify
def test_spotify_demo_is_metadata_only():
    result = fetch_spotify("https://open.spotify.com/episode/DEMO123", demo=True)
    assert result.status == "METADATA_ONLY"
    assert result.contents[0].content_type == "METADATA_ONLY"
    note = result.metadata["note"]
    assert "solo tiene información básica" in note
    assert "transcripción" in note


def test_spotify_show_url_is_rejected_with_guidance():
    result = fetch_spotify("https://open.spotify.com/show/SHOW1", demo=True)
    assert result.status == "FAILED"
    assert "episodio" in result.error.lower()


# ------------------------------------------------------------------ manual
def test_manual_connector_verbatim_and_segments():
    text = "Párrafo uno con contenido.\n\nPárrafo dos con más contenido."
    result = fetch_manual(type("S", (), {"title": None, "author": None, "published_at": None, "language": None, "demo": True})(), text)
    assert result.status == "READY"
    content = result.contents[0]
    assert content.is_verbatim is True
    assert content.coverage == 1.0
    assert len(content.segments) == 2


def test_manual_rejects_pdf_and_empty():
    with pytest.raises(ValueError, match="PDF"):
        normalize_input(None, "texto", filename="informe.pdf")
    with pytest.raises(ValueError, match="texto"):
        normalize_input(None, "   ")


# ------------------------------------------------------------------ seguridad de URLs
def test_ssrf_blocks_loopback_without_allowlist(app_env, monkeypatch):
    from neuralnews.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "allowed_hosts", [])
    with pytest.raises(FetchBlocked, match="privada o local"):
        assert_public_host("http://127.0.0.1:8000/", settings)
    with pytest.raises(FetchBlocked):
        assert_public_host("http://169.254.169.254/latest/meta-data", settings)
    with pytest.raises(FetchBlocked):
        assert_public_host("file:///etc/passwd", settings)


def test_blocked_host_list(app_env, monkeypatch):
    from neuralnews.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "blocked_hosts", ["dominioprohibido.example"])
    with pytest.raises(FetchBlocked, match="bloqueado"):
        assert_public_host("https://dominioprohibido.example/x", settings)


def test_web_article_fetch_from_local_server(local_site):
    base, routes = local_site
    routes["/articulo.html"] = (200, ARTICLE_HTML)
    result = fetch_web(f"{base}/articulo.html")
    assert result.status == "READY", result.error
    content = result.contents[0]
    assert content.content_type == "ARTICLE_TEXT"
    assert content.is_verbatim is True
    assert "alert" not in content.text, "el script debe eliminarse del texto extraído"
    assert "Cortexa Labs" in content.text
    assert result.title == "Artículo de prueba local"
    assert result.author == "Autor de Prueba"
    assert result.canonical_url == "https://ejemplo.invalid/articulo-original"
    assert result.published_at is not None and result.published_at.year == 2026


def test_web_rss_fetch_from_local_server(local_site):
    base, routes = local_site
    routes["/feed.xml"] = (200, RSS_XML)
    result = fetch_web(f"{base}/feed.xml")
    assert result.status == "READY", result.error
    assert "Vireo AI" in result.contents[0].text
    assert result.metadata["feed_url"].endswith("/feed.xml")


def test_web_fetch_404_is_explained(local_site):
    base, _ = local_site
    result = fetch_web(f"{base}/no-existe.html")
    assert result.status == "FAILED"
    assert "404" in result.error


def test_article_extraction_handles_hostile_html():
    html = (
        "<html><body><article><p>Contenido real de la noticia de prueba.</p>"
        "<iframe src='http://169.254.169.254/'></iframe>"
        "<div onclick='pwn()'>Otro párrafo suficiente para contar.</div></article></body></html>"
    )
    data = extract_article(html, "https://ejemplo.invalid/x")
    assert "iframe" not in data["text"]
    assert "Contenido real" in data["text"]


# ------------------------------------------------------------------ contenido hostil como datos
def test_hostile_content_treated_as_data(demo_client, worker):
    payload = demo_client.post("/api/v1/sources", json={"text": DEMO_HOSTILE_TEXT}).json()
    source_id = payload["source"]["id"]
    worker()

    # La fuente no se pierde y conserva el texto íntegro como dato (las órdenes no se ejecutan).
    detail = demo_client.get(f"/api/v1/sources/{source_id}").json()
    assert detail["status"] in ("READY", "PARTIAL")

    stories = demo_client.get("/api/v1/stories").json()["items"]
    for story in stories:
        assert "borra la base" not in story["title"].lower()
        assert story["status"] in (
            "CANDIDATE", "RESEARCHING", "REVIEW_REQUIRED", "SCRIPT_DRAFT", "APPROVED", "REJECTED",
        )
