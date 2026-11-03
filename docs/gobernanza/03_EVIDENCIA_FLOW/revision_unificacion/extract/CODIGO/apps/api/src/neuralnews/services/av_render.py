"""Composición audiovisual local con FFmpeg (Fase 6, T602-T612).

Convierte un plan de producción (JSON emitido por el planificador de Studio,
Fase 4) en un vídeo MP4 reproducible:

1. T602 — activos simulados por escena: segmento de vídeo generado localmente
   (color + rótulo con la locución) y tono de voz con la duración exacta de la
   escena. Sin llamadas de pago: FFmpeg con fuentes lavfi.
2. T603/T607 — orden y duración: los segmentos se concatenan en el orden del
   plan y cada tono dura exactamente la escena (sin huecos ni cortes de voz).
3. T605 — rótulos: cabecera «NeuralStories News · Escena N» y locución de la
   escena sobre la imagen.
4. T606 — glitch configurable: aberración RGB sutil (rgbashift) al final, activa
   por defecto según el canon, aplicada sólo a imagen.
5. T609/T610 — formatos 9:16 (1080x1920) y 16:9 (1920x1080).
6. T612 — el resultado se registra con su sha256, duración y metadatos.

El mismo plan produce el mismo vídeo (huella determinista; idempotencia).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from .. import config
from ..models import RenderOutput, utcnow

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

RESOLUTIONS = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
MIN_SCENE_SECONDS = 1.0
MAX_SCENE_SECONDS = 30.0
FPS = 25

PALETTE = ["0x14202e", "0x2b1d12", "0x1d2b1a", "0x2b1230", "0x10262b"]

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\seguisym.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


class PlanInvalid(Exception):
    """El plan de producción no es válido; mensaje pensado para el usuario."""


class FontNotFound(Exception):
    pass


def _font_path() -> Path | None:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return path
    return None


def _filter_path(path: Path) -> str:
    """Ruta lista para un argumento de filtro: entrecomillada y con los dos
    puntos de la unidad de Windows escapados (forma requerida por drawtext)."""
    return f"'{path.as_posix().replace(':', chr(92) + ':')}'"


def validate_render_plan(plan: dict) -> list[str]:
    """Devuelve la lista de problemas del plan (vacía si es válido)."""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["El plan debe ser un objeto JSON."]
    if not str(plan.get("projectId") or "").strip():
        errors.append("Falta el identificador del proyecto (projectId).")
    if plan.get("outputFormat") not in RESOLUTIONS:
        errors.append("El formato de salida debe ser 9:16 o 16:9.")
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("El plan no tiene escenas: añade al menos una.")
    else:
        for scene in scenes:
            index = scene.get("sceneIndex") if isinstance(scene, dict) else None
            if not isinstance(index, int):
                errors.append("Hay una escena sin número de escena (sceneIndex).")
                continue
            if not str(scene.get("scriptSnippet") or "").strip():
                errors.append(f"La escena {index} no tiene texto de locución.")
            duration = scene.get("estDurationSeconds")
            if not isinstance(duration, (int, float)) or isinstance(duration, bool):
                errors.append(f"La escena {index} no tiene duración estimada.")
            elif not (MIN_SCENE_SECONDS <= duration <= MAX_SCENE_SECONDS):
                errors.append(
                    f"La escena {index} dura {duration} s; debe estar entre "
                    f"{MIN_SCENE_SECONDS:.0f} y {MAX_SCENE_SECONDS:.0f} s."
                )
    return errors


def plan_fingerprint(plan: dict) -> str:
    core = {
        "projectId": plan.get("projectId"),
        "outputFormat": plan.get("outputFormat"),
        "glitch": bool(plan.get("glitch", True)),
        "scenes": [
            {
                "sceneIndex": s.get("sceneIndex"),
                "scriptSnippet": s.get("scriptSnippet"),
                "estDurationSeconds": s.get("estDurationSeconds"),
                "transition": s.get("transition"),
                "movement": s.get("movement"),
            }
            for s in plan.get("scenes", [])
        ],
    }
    canonical = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _wrap_text(text: str, width: int = 38, max_lines: int = 10) -> str:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > width and current:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return "\n".join(lines)


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg terminó con error: {result.stderr[-800:]}")


def probe_media(path: Path) -> dict:
    """Metadatos reales del fichero (T611): duración y dimensiones."""
    result = subprocess.run(
        [
            FFPROBE, "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,width,height,codec_name",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe no pudo leer el fichero: {result.stderr[-400:]}")
    data = json.loads(result.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
    return {
        "duration_s": float(data.get("format", {}).get("duration") or 0.0),
        "width": video.get("width"),
        "height": video.get("height"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "has_audio": bool(audio),
    }


def _render_scene_segment(
    scene: dict,
    index: int,
    total: int,
    width: int,
    height: int,
    duration: float,
    workdir: Path,
) -> Path:
    """Segmento por escena: color de fondo + rótulos + tono de voz (T602/T605)."""
    color = PALETTE[index % len(PALETTE)]
    frequency = min(880, 320 + 60 * index)
    font = _font_path()
    filters = ["format=yuv420p"]
    if font is not None:
        header = f"NeuralStories News · Escena {index} de {total}"
        body = _wrap_text(str(scene["scriptSnippet"]))
        header_file = workdir / f"rotulo_{index:03d}_cabecera.txt"
        body_file = workdir / f"rotulo_{index:03d}_texto.txt"
        header_file.write_text(header, encoding="utf-8")
        body_file.write_text(body, encoding="utf-8")
        escaped = _filter_path(font)
        header_escaped = _filter_path(header_file)
        body_escaped = _filter_path(body_file)
        label_size = max(28, width // 26)
        body_size = max(24, width // 32)
        filters.insert(
            0,
            "drawtext=fontfile=" + escaped
            + f":textfile={header_escaped}:fontcolor=0xd9c08a:fontsize={label_size}"
            f":x=(w-text_w)/2:y=h*0.10",
        )
        filters.insert(
            1,
            "drawtext=fontfile=" + escaped
            + f":textfile={body_escaped}:fontcolor=white:fontsize={body_size}"
            f":x=(w-text_w)/2:y=h*0.30:line_spacing={body_size // 2}",
        )
    segment = workdir / f"escena_{index:03d}.mp4"
    _run_ffmpeg(
        [
            "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:d={duration:.3f}:r={FPS}",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration={duration:.3f}",
            "-filter_complex",
            f"[0:v]{','.join(filters)}[v];[1:a]aresample=44100[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
            "-c:a", "aac", "-b:a", "96k",
            "-t", f"{duration:.3f}",
            segment.as_posix(),
        ]
    )
    return segment


def render_plan_video(db: Session, plan: dict, *, job_id: int, max_cost_eur: float | None = None) -> RenderOutput:
    """Compone el vídeo del plan y registra el resultado (T603-T612)."""
    from ..services import budget as budget_service

    errors = validate_render_plan(plan)
    if errors:
        raise PlanInvalid(
            "El plan de producción no es válido:\n- " + "\n- ".join(errors)
        )

    # T514: techo de coste por trabajo. El proveedor simulado declara coste 0;
    # un adaptador real que estimase por encima del techo no llegaría a renderizar.
    estimated_cost_eur = 0.0
    if max_cost_eur is not None and estimated_cost_eur > max_cost_eur:
        raise budget_service.BudgetExceeded(
            f"El coste estimado ({estimated_cost_eur:.2f} €) supera el techo del trabajo "
            f"({max_cost_eur:.2f} €)."
        )

    fingerprint = plan_fingerprint(plan)
    width, height = RESOLUTIONS[plan["outputFormat"]]
    glitch = bool(plan.get("glitch", True))
    scenes = plan["scenes"]

    renders_dir = config.STORAGE_DIR / "av" / "renders"
    final_path = renders_dir / f"render-{plan['projectId']}-{fingerprint[:16]}.mp4"
    if final_path.exists():
        # Idempotencia: el mismo plan ya se compuso; se reutiliza el fichero.
        return _register_render(
            db, job_id=job_id, plan=plan, fingerprint=fingerprint, path=final_path,
            glitch=glitch, scenes_count=len(scenes),
        )

    workdir = renders_dir / f"work-{fingerprint[:12]}-{job_id}"
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        segments: list[Path] = []
        for position, scene in enumerate(scenes, start=1):
            duration = float(
                min(max(float(scene["estDurationSeconds"]), MIN_SCENE_SECONDS), MAX_SCENE_SECONDS)
            )
            segments.append(
                _render_scene_segment(
                    scene, position, len(scenes), width, height, duration, workdir
                )
            )

        list_file = workdir / "concat.txt"
        list_file.write_text(
            "\n".join(f"file '{path.as_posix()}'" for path in segments), encoding="utf-8"
        )
        concat_path = workdir / "concat.mp4"
        _run_ffmpeg(
            ["-f", "concat", "-safe", "0", "-i", list_file.as_posix(), "-c", "copy", concat_path.as_posix()]
        )

        if glitch:
            _run_ffmpeg(
                ["-i", concat_path.as_posix(),
                 "-vf", "rgbashift=rh=-4:bh=4",
                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                 "-c:a", "copy", final_path.as_posix()]
            )
        else:
            shutil.move(str(concat_path), str(final_path))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return _register_render(
        db, job_id=job_id, plan=plan, fingerprint=fingerprint, path=final_path,
        glitch=glitch, scenes_count=len(scenes),
    )


def _register_render(
    db: Session,
    *,
    job_id: int,
    plan: dict,
    fingerprint: str,
    path: Path,
    glitch: bool,
    scenes_count: int,
) -> RenderOutput:
    media = probe_media(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    row = RenderOutput(
        job_id=job_id,
        project_id=str(plan.get("projectId")),
        plan_fingerprint=fingerprint,
        output_format=str(plan.get("outputFormat")),
        storage_path=path.as_posix(),
        sha256=digest,
        duration_s=media["duration_s"],
        scene_count=scenes_count,
        glitch_applied=glitch,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return row
