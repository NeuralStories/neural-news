"""Biblioteca de medios: subida idempotente por SHA-256 con almacén direccionado
por contenido. En PostgreSQL/SQLite solo metadatos; el archivo vive en
`storage/media/{sha256[:2]}/{sha256}{ext}` (nunca base64 en filas, nunca en git).

`ffprobe` es opcional: si no está instalado, los metadatos quedan UNKNOWN y la
subida sigue siendo válida (hash + tamaño). Nunca se aprueba un asset en la
subida: `license_state` arranca PENDING y la aprobación es humana (F-02).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..models import MediaAsset, utcnow

ALLOWED_MIME = {
    "video/mp4": ".mp4",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_UPLOAD_BYTES = 200 * 1024 * 1024


class MediaUploadError(ValueError):
    """Error de validación de subida (tipo, tamaño o contenido)."""


def media_root() -> Path:
    return Path(config.STORAGE_DIR) / "media"


def _ffprobe(path: Path) -> dict:
    """Metadatos reproducibles con ffprobe si existe; si no, UNKNOWN honesto."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"probe_status": "UNAVAILABLE"}
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams",
             str(path)],
            capture_output=True, timeout=30, check=True,
        )
        info = json.loads(proc.stdout.decode("utf-8", "replace"))
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return {"probe_status": "FAILED"}

    fmt = info.get("format") or {}
    duration = None
    try:
        duration = round(float(fmt.get("duration")), 3)
    except (TypeError, ValueError):
        pass
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    width = height = None
    fps = None
    orientation = None
    if video:
        width = video.get("width")
        height = video.get("height")
        if width and height:
            orientation = "portrait" if height >= width else "landscape"
        rate = video.get("avg_frame_rate") or video.get("r_frame_rate")
        if rate and isinstance(rate, str) and "/" in rate:
            num, den = rate.split("/", 1)
            try:
                if float(den):
                    fps = round(float(num) / float(den), 3)
            except (TypeError, ValueError, ZeroDivisionError):
                fps = None
    return {
        "probe_status": "OK",
        "width": width,
        "height": height,
        "duration_s": duration,
        "fps": fps,
        "orientation": orientation,
        "has_audio": audio is not None,
    }


def upload_media(db: Session, data: bytes, mime_type: str, filename: str | None) -> MediaAsset:
    """Subida idempotente: el mismo contenido devuelve el asset existente."""
    if mime_type not in ALLOWED_MIME:
        raise MediaUploadError(f"Tipo no permitido: {mime_type}. Permitidos: {sorted(ALLOWED_MIME)}")
    if not data:
        raise MediaUploadError("El archivo está vacío")
    if len(data) > MAX_UPLOAD_BYTES:
        raise MediaUploadError("El archivo supera el límite de 200 MB")

    digest = hashlib.sha256(data).hexdigest()
    existing = db.scalars(select(MediaAsset).where(MediaAsset.sha256 == digest)).first()
    if existing is not None:
        return existing

    ext = ALLOWED_MIME[mime_type]
    folder = media_root() / digest[:2]
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{digest}{ext}"
    dest.write_bytes(data)

    probe = _ffprobe(dest) if mime_type == "video/mp4" else {"probe_status": "UNAVAILABLE"}
    asset = MediaAsset(
        sha256=digest,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(data),
        storage_path=str(dest),
        width=probe.get("width"),
        height=probe.get("height"),
        duration_s=probe.get("duration_s"),
        fps=probe.get("fps"),
        orientation=probe.get("orientation"),
        has_audio=probe.get("has_audio"),
        probe_status=probe.get("probe_status", "UNKNOWN"),
        provenance="imported_flow_manual",
        license_state="PENDING",
        created_at=utcnow(),
    )
    db.add(asset)
    db.flush()
    return asset


def asset_to_out(asset: MediaAsset) -> dict:
    return {
        "id": asset.id,
        "sha256": asset.sha256,
        "filename": asset.filename,
        "mime_type": asset.mime_type,
        "size_bytes": asset.size_bytes,
        "width": asset.width,
        "height": asset.height,
        "duration_s": asset.duration_s,
        "fps": asset.fps,
        "orientation": asset.orientation,
        "has_audio": asset.has_audio,
        "probe_status": asset.probe_status,
        "provenance": asset.provenance,
        "license_state": asset.license_state,
        "download_url": f"/api/v1/media/{asset.id}/file",
        "created_at": asset.created_at.isoformat(),
    }
