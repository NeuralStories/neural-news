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


def es_ip_publica(ip_text: str) -> bool:
    """¿La dirección es de acceso público (no privada, local ni reservada)?"""
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_public_host(url: str, settings: Settings) -> list[str]:
    """Comprueba la URL y devuelve las direcciones públicas por las que se
    permite conectar.

    Devolver las direcciones validadas permite después comprobar que la
    conexión realmente se hizo a una de ellas (NN-111.7: DNS-rebinding).
    """
    parts = urlsplit(url)
    if parts.scheme not in settings.allowed_url_schemes:
        raise FetchBlocked("Esquema de URL no permitido (usa http o https)")
    host = parts.hostname
    if not host:
        raise FetchBlocked("URL sin dominio válido")
    if host.lower() in {h.lower() for h in settings.blocked_hosts}:
        raise FetchBlocked("Ese dominio está bloqueado por la configuración")
    if host.lower() in {h.lower() for h in settings.allowed_hosts}:
        # Allowlist explícita (p. ej. servidor de pruebas local): se salta el
        # bloqueo de redes privadas, pero sigue limitada a http/https.
        return []
    ips = resolve_host_ips(host)
    for ip_text in ips:
        if not es_ip_publica(ip_text):
            raise FetchBlocked(
                "La URL apunta a una red privada o local; por seguridad no se descarga"
            )
    return ips


def _ip_de_conexion(response: httpx.Response) -> str | None:
    """Dirección real del servidor al que se conectó (si el transporte la da)."""
    stream = response.extensions.get("network_stream")
    if stream is None:
        return None
    try:
        info = stream.get_extra_info("server_addr")
    except Exception:  # noqa: BLE001 — depende del transporte; si no, se omite
        return None
    if isinstance(info, tuple) and info:
        return str(info[0])
    return str(info) if info else None


def _leer_con_tope(response: httpx.Response, max_bytes: int) -> bytes:
    """Lee el cuerpo **por trozos** y se detiene en el límite.

    Antes se leía `response.content` entero y luego se recortaba: el servidor
    hostil podía agotar la memoria del proceso antes de que el corte hiciera
    efecto (hallazgo P7, NN-111.6).
    """
    partes: list[bytes] = []
    total = 0
    for trozo in response.iter_bytes():
        total += len(trozo)
        if total > max_bytes:
            raise FetchBlocked("El contenido supera el tamaño máximo admitido")
        partes.append(trozo)
    return b"".join(partes)


def comprobar_ip_de_conexion(ip_real: str | None, ips_validadas: list[str]) -> None:
    """La conexión real tiene que haber ido a una de las direcciones comprobadas.

    Cierra la ventana del DNS-rebinding (NN-111.7): entre la comprobación y la
    conexión, la resolución puede cambiar y apuntar a una red interna. Si la
    dirección real no es pública, o no era una de las validadas, el contenido
    se descarta.
    """
    if not ip_real or not ips_validadas:
        return
    if not es_ip_publica(ip_real):
        raise FetchBlocked(
            "La conexión se resolvió a una dirección no pública; se descarta"
        )
    if ip_real not in ips_validadas:
        raise FetchBlocked(
            "La resolución del dominio cambió entre la comprobación y la conexión; "
            "se descarta por seguridad"
        )


def fetch_url_safely(url: str, settings: Settings) -> SafeFetch:
    """Descarga con redirecciones verificadas una a una y tope de bytes."""
    current = url
    for _ in range(settings.fetch_max_redirects + 1):
        ips_validadas = assert_public_host(current, settings)
        with httpx.Client(follow_redirects=False, timeout=settings.fetch_timeout_s) as client:
            with client.stream(
                "GET", current, headers={"User-Agent": "neuralnews-mvp/0.1 (+editorial)"}
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location", "")
                    if not location:
                        raise FetchBlocked("Redirección sin destino")
                    current = urljoin(current, location)
                    continue
                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > settings.max_download_bytes:
                    raise FetchBlocked("El archivo supera el tamaño máximo admitido")
                # DNS-rebinding: la conexión real tiene que haber ido a una de las
                # direcciones que se comprobaron. Si la resolución cambió entre
                # la comprobación y la conexión, el contenido se descarta.
                comprobar_ip_de_conexion(_ip_de_conexion(response), ips_validadas)
                body = _leer_con_tope(response, settings.max_download_bytes)
                return SafeFetch(
                    url=url,
                    status=response.status_code,
                    content_type=response.headers.get("content-type", ""),
                    body=body,
                    final_url=str(response.request.url),
                )
    raise FetchBlocked("Demasiadas redirecciones")
