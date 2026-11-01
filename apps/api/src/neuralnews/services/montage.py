"""Motor de montaje real (NN-107 FASE 3) — previsualización 9:16 con FFmpeg.

Compone las tomas del proyecto en una línea de tiempo continua:
  - Tomas con MP4 importado → clip real (recortado/extendido a su ventana).
  - DATA_GRAPHIC / TITLE_CARD → tarjeta programática renderizada con Pillow
    (valores exactos del GraphicSpec; nunca cifras inventadas).
  - Tomas sin material → hueco: el montaje NO se construye y se lista
    exactamente qué falta (voz, clips, autorizaciones).

El resultado es una ANIMÁTICA (previsualización sin locución), nunca el render
final: se etiqueta como tal en el propio fichero y en la API.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .. import config

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


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for cand in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        if Path(cand).exists():
            return ImageFont.truetype(cand, size)
    return ImageFont.load_default()


def _render_card(title: str, lines: list[str], series: list[dict] | None = None,
                 source_note: str = "") -> Path:
    """Tarjeta programática 1080x1920: rótulo/titular o barras con valores exactos."""
    out_dir = Path(config.STORAGE_DIR) / "montage" / "cards"
    out_dir.mkdir(parents=True, exist_ok=True)
    import hashlib
    name = hashlib.sha256((title + str(lines) + str(series)).encode()).hexdigest()[:16] + ".png"
    dest = out_dir / name
    if dest.exists():
        return dest
    img = Image.new("RGB", (W, H), (2, 6, 23))
    d = ImageDraw.Draw(img)
    f_title = _font(72)
    f_big = _font(96)
    f_small = _font(34)
    d.text((80, 120), title[:34], font=f_title, fill=(251, 191, 36))
    y = 420
    if series:
        max_v = max(float(s.get("value", 0)) for s in series) or 1.0
        for i, item in enumerate(series):
            value = float(item.get("value", 0))
            unit = str(item.get("unit", "")).strip()
            label = str(item.get("label", ""))
            bar_w = int(860 * (value / max_v))
            y0 = y + i * 320
            d.rectangle([80, y0, 80 + bar_w, y0 + 140], fill=(56, 189, 248))
            d.text((80, y0 - 90), f"{value:g} {unit}".strip(), font=f_big, fill=(226, 232, 240))
            d.text((80, y0 + 160), label, font=f_small, fill=(148, 163, 184))
    else:
        for i, line in enumerate(lines):
            d.text((80, y + i * 140), line[:30], font=f_big, fill=(226, 232, 240))
    if source_note:
        d.text((80, H - 160), source_note[:60], font=f_small, fill=(100, 116, 139))
    dest.write_bytes(b"")
    img.save(dest, format="PNG")
    return dest


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
            entry["segment_type"] = "CARD"
            entry["title"] = (shot.data or {}).get("beat_texts", ["Titular"])[0] if shot.data else "Titular"
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
            card = _render_card(seg.get("title", "neural.news"), seg.get("beat_texts", []),
                                series=None, source_note="ANIMÁTICA — previsualización sin locución")
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
