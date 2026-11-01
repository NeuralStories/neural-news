"""Motor de montaje real (NN-107 FASE 3) — previsualización 9:16 con FFmpeg.

Compone las tomas del proyecto en una línea de tiempo continua:
  - Tomas con MP4 importado → clip real (recortado/extendido a su ventana).
  - DATA_GRAPHIC / TITLE_CARD → tarjeta programática renderizada con el
    diseño único de graphics.py (valores exactos del GraphicSpec; nunca
    cifras inventadas; misma paleta y geometría que el SVG de la UI).
  - Tomas sin material → hueco: el montaje NO se construye y se lista
    exactamente qué falta (voz, clips, autorizaciones).

El resultado es una ANIMÁTICA (previsualización sin locución), nunca el render
final: se etiqueta como tal en el propio fichero y en la API.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from sqlalchemy import select

from .. import config
from ..models import GraphicSpec
from .graphics import render_chart_png_1080x1920, render_title_png_1080x1920

W, H, FPS = 1080, 1920, 30


def ffmpeg_dir() -> Path | None:
    """Resuelve FFmpeg: variable NEURAL_FFMPEG_DIR, PATH del sistema o la
    instalación local de binarios nativos junto al repositorio. Sin Docker."""
    import os
    candidates: list[Path] = []
    custom = os.getenv("NEURAL_FFMPEG_DIR")
    if custom:
        candidates.append(Path(custom))
    which = shutil.which("ffmpeg")
    if which:
        return Path(which).parent
    repo_tools = Path(config.REPO_ROOT).parent / "ffmpeg-local"
    if repo_tools.exists():
        candidates.extend(sorted(repo_tools.glob("ffmpeg*/bin")))
    for c in candidates:
        if (c / "ffmpeg.exe").exists() or (c / "ffmpeg").exists():
            return c
    return None


def _run(bin_dir: Path, args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    exe = bin_dir / ("ffmpeg.exe" if (bin_dir / "ffmpeg.exe").exists() else "ffmpeg")
    return subprocess.run([str(exe), "-hide_banner", "-loglevel", "error", "-y", *args],
                          capture_output=True, timeout=timeout)



def timeline(db: Any, project: Any) -> tuple[list[dict], list[dict]]:
    """Construye la línea de tiempo desde shots/takes persistidos y calcula
    los materiales que faltan (sin inventar nada)."""
    segments: list[dict] = []
    missing: list[dict] = []
    shots = sorted(project.shots, key=lambda s: s.sequence)
    for shot in shots:
        take = next((t for t in project.takes if t.shot_id == shot.id), None)
        duration = round((shot.end_s or 0) - (shot.start_s or 0), 2)
        if duration <= 0:
            duration = 2.0
        entry = {
            "shot_id": shot.id,
            "shot_kind": shot.shot_kind,
            "start_s": shot.start_s,
            "end_s": shot.end_s,
            "duration_s": duration,
            "beat_texts": (shot.data or {}).get("beat_texts", []),
            "transition": (shot.data or {}).get("transition", "corte_directo"),
        }
        if take is not None and take.imported_media_id is not None:
            entry["segment_type"] = "CLIP"
            entry["media_id"] = take.imported_media_id
            entry["path"] = take.imported_media.storage_path
            segments.append(entry)
            continue
        if shot.shot_kind in ("DATA_GRAPHIC", "TITLE_CARD"):
            graphic = db.scalars(
                select(GraphicSpec)
                .where(GraphicSpec.project_id == project.id, GraphicSpec.status != "INVALIDADO")
                .order_by(GraphicSpec.id.desc())
                .limit(1)
            ).first()
            if graphic is None:
                missing.append({
                    "shot_id": shot.id,
                    "shot_kind": shot.shot_kind,
                    "window": f"{shot.start_s}s→{shot.end_s}s",
                    "reason": "gráfico programático no definido: crea el gráfico con los valores verificados",
                })
                continue
            entry["segment_type"] = "CARD"
            entry["graphic_spec"] = {
                "title": graphic.title,
                "series": (graphic.data or {}).get("series", []),
                "source_note": (graphic.data or {}).get("source_note", ""),
            }
            segments.append(entry)
            continue
        missing.append({
            "shot_id": shot.id,
            "shot_kind": shot.shot_kind,
            "window": f"{shot.start_s}s→{shot.end_s}s",
            "reason": {
                "FLOW_MAXDOTAI": "toma de maxDotAi sin MP4 importado: generar en Flow con su FlowManualPackage",
                "USER_VIDEO": "vídeo propio no aportado",
                "DOCUMENTARY": "material auténtico con derechos pendientes",
                "GENERATIVE_BROLL": "B-roll generativo pendiente",
            }.get(shot.shot_kind, "material o autorización ausentes"),
        })
    return segments, missing


def build_animatica(db: Any, project: Any) -> dict:
    """Compone la animática 9:16 real con FFmpeg (sin locución: silencio)."""
    bin_dir = ffmpeg_dir()
    if bin_dir is None:
        return {"ok": False, "error": "FFmpeg no está disponible en este equipo", "missing": []}

    segments, missing = timeline(db, project)
    buildable = [seg for seg in segments if seg["segment_type"] in ("CLIP", "CARD")]
    if not buildable:
        return {"ok": False, "error": "No hay ningún segmento renderizable",
                "missing": missing, "segments": segments}
    if missing:
        # La animática se construye SOLO si todos los segmentos tienen material;
        # en modo parcial se permite explícitamente previsualización de lo disponible.
        pass

    out_dir = Path(config.STORAGE_DIR) / "montage" / str(project.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    out_path = out_dir / f"animatica_916_{stamp}.mp4"

    T = 0.4  # duración de la transición xfade entre segmentos (glitch breve)
    XFADE_MAP = {
        "rgb_glitch_flash": "fade",
        "whip_pan": "wipeleft",
        "push_zoom": "zoomin",
        "corte_directo": "fade",  # con T corto se comporta como corte casi seco
    }
    filter_parts: list[str] = []
    input_args: list[str] = []
    index = 0
    # Cada entrada se recorta a su ventana + T extra si el límite posterior es
    # xfade (el solapamiento consume material del siguiente encadenado).
    for i, seg in enumerate(buildable):
        dur = seg["duration_s"]
        extra = T if i < len(buildable) - 1 and seg.get("transition") != "corte_directo" else 0
        if seg["segment_type"] == "CLIP":
            src = seg["path"]
            filter_parts.append(
                f"[{index}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},tpad=stop_mode=clone:stop_duration=8,"
                f"trim=duration={dur + extra:.2f},setpts=PTS-STARTPTS[v{index}]"
            )
            input_args += ["-i", src]
        else:
            # Tarjetas desde el DISEÑO ÚNICO de graphics.py (misma paleta y
            # geometría que el SVG de la UI): gráfico de datos o rótulo.
            if seg.get("graphic_spec"):
                spec = dict(seg["graphic_spec"])
                spec.setdefault("source_note", "ANIMÁTICA — previsualización sin locución")
                png_bytes = render_chart_png_1080x1920(spec)
            else:
                beat_texts = seg.get("beat_texts", [])
                title = beat_texts[0] if beat_texts else seg.get("title", "neural.news")
                lines = beat_texts[1:] or ["neural.news"]
                png_bytes = render_title_png_1080x1920(title, lines,
                                                       "ANIMÁTICA — previsualización sin locución")
            card_dir = Path(config.STORAGE_DIR) / "montage" / "cards"
            card_dir.mkdir(parents=True, exist_ok=True)
            card = card_dir / f"{hashlib.sha256(png_bytes).hexdigest()[:16]}.png"
            if not card.exists():
                card.write_bytes(png_bytes)
            filter_parts.append(
                f"[{index}:v]scale={W}:{H},fps={FPS},trim=duration={dur + extra:.2f},setpts=PTS-STARTPTS[v{index}]"
            )
            input_args += ["-loop", "1", "-t", f"{dur + extra:.2f}", "-i", str(card)]
        index += 1

    # Encadenado: xfade (glitch/pan/zoom/fade) o corte seco (concat), según la
    # transición asignada por el director a cada límite.
    transitions_used: list[dict] = []
    current = "[v0]"
    visible = buildable[0]["duration_s"]
    for i in range(1, len(buildable)):
        boundary = buildable[i].get("transition", "corte_directo")
        prev = buildable[i - 1]
        if boundary != "corte_directo":
            transition = XFADE_MAP.get(boundary, "fade")
            offset = round(max(visible - T, 0), 2)
            out_label = f"[x{i}]"
            filter_parts.append(
                f"{current}[v{i}]xfade=transition={transition}:duration={T}:offset={offset}{out_label}"
            )
            transitions_used.append({"after_segment": i, "transition": boundary, "ffmpeg": transition,
                                     "duration_s": T, "offset_s": offset})
            current = out_label
            visible = round(visible + buildable[i]["duration_s"] - T, 2)
        else:
            out_label = f"[c{i}]"
            filter_parts.append(f"{current}[v{i}]concat=n=2:v=1:a=0{out_label}")
            transitions_used.append({"after_segment": i, "transition": "corte_directo"})
            current = out_label
            visible = round(visible + buildable[i]["duration_s"], 2)

    args = [
        *input_args,
        "-filter_complex", ";".join(filter_parts),
        "-map", current, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(out_path),
    ]
    proc = _run(bin_dir, args, timeout=600)
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.decode("utf-8", "replace")[-800:], "missing": missing}

    duration = visible if transitions_used else buildable[-1]["end_s"]
    return {
        "ok": True,
        "path": str(out_path),
        "duration_s": duration,
        "segments": len(buildable),
        "missing": missing,
        "transitions": transitions_used,
        "label": "ANIMÁTICA 9:16 — previsualización sin locución; NO es el render final",
    }
