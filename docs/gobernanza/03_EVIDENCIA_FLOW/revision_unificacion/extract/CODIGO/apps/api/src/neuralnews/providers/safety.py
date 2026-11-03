"""Descarga segura de URLs: protecciones SSRF, límites de tamaño y tiempo.

Comprueba esquema, resuelve DNS y bloquea direcciones privadas/reservadas,
limita redirecciones y bytes leídos, y aplica tiempos de espera cortos.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from ..config import Settings


class FetchBlocked(Exception):
    """La URL no supera las comprobaciones de seguridad o el límite de descarga."""


@dataclass
class SafeFetch:
    url: str
    status: int
    content_type: str
    body: bytes
    final_url: str


def resolve_host_ips(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise FetchBlocked(f"No se ha podido resolver el dominio «{host}»") from exc
    return [info[4][0] for info in infos]


def assert_public_host(url: str, settings: Settings) -> str:
    parts = urlsplit(url)
    if parts.scheme not in settings.allowed_url_schemes:
        raise FetchBlocked("Esquema de URL no permitido (usa http o https)")
    host = parts.hostname
    if not host:
        raise FetchBlocked("URL sin dominio válido")
    if host.lower() in {h.lower() for h in settings.blocked_hosts}:
        raise FetchBlocked("Ese dominio está bloqueado por la configuración")
    if host.lower() in {h.lower() for h in settings.allowed_hosts}:
        return host  # allowlist explícita (p. ej. servidor de pruebas): sigue limitada a http/https
    for ip_text in resolve_host_ips(host):
        ip = ipaddress.ip_address(ip_text)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise FetchBlocked(
                "La URL apunta a una red privada o local; por seguridad no se descarga"
            )
    return host


def fetch_url_safely(url: str, settings: Settings) -> SafeFetch:
    """Descarga con redirecciones verificadas una a una y tope de bytes."""
    current = url
    for _ in range(settings.fetch_max_redirects + 1):
        assert_public_host(current, settings)
        with httpx.Client(follow_redirects=False, timeout=settings.fetch_timeout_s) as client:
            response = client.get(current, headers={"User-Agent": "neuralnews-mvp/0.1 (+editorial)"})
        if response.is_redirect:
            location = response.headers.get("location", "")
            if not location:
                raise FetchBlocked("Redirección sin destino")
            current = urljoin(current, location)
            continue
        declared = response.headers.get("content-length")
        if declared and int(declared) > settings.max_download_bytes:
            raise FetchBlocked("El archivo supera el tamaño máximo admitido")
        body = response.content[: settings.max_download_bytes + 1]
        if len(body) > settings.max_download_bytes:
            raise FetchBlocked("El contenido supera el tamaño máximo admitido")
        return SafeFetch(
            url=url,
            status=response.status_code,
            content_type=response.headers.get("content-type", ""),
            body=body,
            final_url=str(response.request.url),
        )
    raise FetchBlocked("Demasiadas redirecciones")
