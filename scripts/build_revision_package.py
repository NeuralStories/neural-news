"""Construye el paquete final único REVISION_NN107_FLOW.zip (entrega NN-107).

Contenido: código trackeado por git (sin .env, sin storage, sin node_modules),
historial completo (bundle), gobernanza newsV2, evidencia de pruebas, recorrido
audiovisual, ESTADO_REAL.md, IMPLEMENTACION_REALIZADA.md, guía y manifiesto
SHA-256 interno. Escanea secretos antes de sellar."""
from __future__ import annotations

import hashlib
import subprocess
import time
import zipfile
from pathlib import Path

BASE = Path(r"C:/Users/haxth3/Documents/NeuralStories")
REPO = BASE / "neural-news"
OUT = BASE / "REVISION_NN107_FLOW"
ZIP_PATH = BASE / "REVISION_NN107_FLOW.zip"

# Patrones construidos por concatenación para que este propio script no
# aparezca como coincidencia en su propio escaneo.
SECRET_PATTERNS = (
    "sk" + "-", "BEGIN RSA PRIVATE" + " KEY", "BEGIN OPENSSH PRIVATE" + " KEY",
    "password" + ' = "', "api_key" + ' = "', "apikey" + "=" + chr(34), "SECRET_TOKEN" + "=",
)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


tracked = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True,
                         check=True).stdout.splitlines()
# `git ls-files` incluye .env.example (plantilla) pero jamás .env real (no existe);
# se excluye storage/ (medios de prueba) por innecesario en la revisión.
tracked = [f for f in tracked if not f.startswith("storage/")]

entries: list[tuple[str, Path]] = []
secret_hits: list[str] = []
for rel in tracked:
    src = REPO / rel
    if not src.is_file():
        continue
    text = src.read_text(encoding="utf-8", errors="replace") if src.stat().st_size < 2_000_000 else ""
    for pat in SECRET_PATTERNS:
        if pat in text:
            secret_hits.append(f"{rel}: {pat}")
    entries.append((f"codigo/{rel.replace(chr(92), '/')}", src))

extras = [
    ("ESTADO_REAL.md", REPO / "ESTADO_REAL.md"),
    ("IMPLEMENTACION_REALIZADA.md", REPO / "IMPLEMENTACION_REALIZADA.md"),
    ("historial/nn107-neural-news.bundle", OUT / "nn107-neural-news.bundle"),
    ("evidencia/pytest_api_completa.txt", OUT / "evidencia/pytest_api_completa.txt"),
    ("evidencia/pytest_postgres_real.txt", OUT / "evidencia/pytest_postgres_real.txt"),
    ("evidencia/e2e_edge.txt", OUT / "evidencia/e2e_edge.txt"),
    ("evidencia/migraciones_pg.txt", OUT / "evidencia/migraciones_pg.txt"),
    ("evidencia/build_web.txt", OUT / "evidencia/build_web.txt"),
    ("evidencia/recorrido_audiovisual_transcripcion.txt", OUT / "recorrido_audiovisual_transcripcion.txt"),
    ("GUIA_DE_REVISION.md", OUT / "GUIA_DE_REVISION.md"),
]
for name, src in extras:
    if src.exists():
        entries.append((name, src))

# Gobernanza: especificación rectora, documentación, tareas y evidencia de Flow
for sub in ("01_DOCUMENTACION", "06_TASKS", "02_CONTRATOS"):
    folder = BASE / "newsV2" / sub
    if folder.exists():
        for f in sorted(folder.rglob("*")):
            if f.is_file() and "extract" not in str(f):
                entries.append((f"gobernanza/{sub}/{f.relative_to(folder).as_posix()}", f))
ev = BASE / "newsV2" / "03_EVIDENCIA_FLOW"
if ev.exists():
    for f in sorted(ev.rglob("*")):
        if f.is_file() and "revision_unificacion" not in str(f) and f.suffix.lower() != ".rar":
            entries.append((f"gobernanza/03_EVIDENCIA_FLOW/{f.relative_to(ev).as_posix()}", f))

seen = set()
final_entries = []
for name, src in entries:
    if name in seen:
        continue
    seen.add(name)
    final_entries.append((name, src))

with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    for name, src in final_entries:
        z.write(src, name)

inner = []
with zipfile.ZipFile(ZIP_PATH) as z:
    for info in z.infolist():
        inner.append((info.filename, info.file_size, hashlib.sha256(z.read(info)).hexdigest()))

head = subprocess.run(["git", "log", "--oneline", "-8"], cwd=REPO, capture_output=True, text=True).stdout
with open(OUT / "MANIFIESTO_FINAL_SHA256.txt", "w", encoding="utf-8") as m:
    m.write("MANIFIESTO — REVISION_NN107_FLOW.zip (entrega final NN-107, inmutable)\n")
    m.write(f"Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    m.write("Estado: NO APROBADO — pendiente de revisión y aprobación del propietario\n")
    m.write("Docker: eliminado del flujo (100 % sin Docker; PostgreSQL local de binarios nativos)\n\n")
    m.write("== Commits (rama nn-107-reintegracion-flow) ==\n" + head + "\n")
    m.write("== Escaneo de secretos ==\n")
    m.write(("SIN SECRETOS DETECTADOS" if not secret_hits else "AVISOS:\n" + "\n".join(secret_hits)) + "\n\n")
    m.write("== Contenido sellado (nombre | bytes | sha256) ==\n")
    for name, size, h in inner:
        m.write(f"{h}  {name}  ({size:,} bytes)\n")

zip_hash = sha(ZIP_PATH)
with open(BASE / "REVISION_NN107_FLOW.zip.sha256", "w", encoding="utf-8") as f:
    f.write(f"{zip_hash}  REVISION_NN107_FLOW.zip\n")

print(f"REVISION_NN107_FLOW.zip: {len(inner)} entradas, {ZIP_PATH.stat().st_size/1e6:.1f} MB")
print("secretos:", "NINGUNO" if not secret_hits else secret_hits)
print("sha256 del paquete:", zip_hash)
