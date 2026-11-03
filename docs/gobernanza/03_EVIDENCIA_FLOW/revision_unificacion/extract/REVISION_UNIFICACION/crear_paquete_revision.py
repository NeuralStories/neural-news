"""Crea el ZIP de revisión desde una lista explícita, sin datos locales ni secretos.

Ejecutar desde la raíz del repositorio: python REVISION_UNIFICACION/crear_paquete_revision.py
No modifica archivos fuente ni Git.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "REVISION_UNIFICACION"
ZIP_PATH = ROOT / "REVISION_UNIFICACION_NEURAL_NEWS.zip"
MANIFEST = REVIEW / "MANIFIESTO_ARCHIVOS_SHA256.txt"

REVIEW_FILES = [
    "README_REVISION.md",
    "INVENTARIO_FUNCIONAL.md",
    "MATRIZ_UNIFICACION.md",
    "MAPA_NAVEGACION_ACTUAL.md",
    "PROPUESTA_FLUJO_UNICO.md",
    "ESTADO_REAL.md",
    "crear_paquete_revision.py",
]
CODE_DIRS = [
    "apps/api/src",
    "apps/api/scripts",
    "apps/studio/src",
    "apps/studio/tests",
    "apps/web/app",
    "apps/web/components",
    "apps/web/lib",
    "apps/web/e2e",
    "packages/contracts",
    "flow-recovery/source",
    "fixtures",
    "tests",
    "infra/migrations",
]
CODE_FILES = [
    "apps/api/pyproject.toml",
    "apps/studio/package.json",
    "apps/studio/package-lock.json",
    "apps/studio/index.html",
    "apps/studio/vite.config.ts",
    "apps/studio/tsconfig.json",
    "apps/studio/README.md",
    "apps/web/package.json",
    "apps/web/package-lock.json",
    "apps/web/next.config.ts",
    "apps/web/playwright.config.ts",
    "apps/web/tsconfig.json",
    "apps/web/postcss.config.mjs",
    "infra/Dockerfile.api",
    "infra/Dockerfile.web",
    "flow-recovery/reports/manifest.json",
    "README.md",
    "INVENTARIO_FLOW.md",
    "UNIFICATION_MANIFEST.md",
    "docs/ARCHITECTURE.md",
    "docs/EDITORIAL_STYLE.md",
    "docs/PROVIDER_STATUS.md",
]

EXCLUDED_PARTS = {
    ".git", ".next", "node_modules", "dist", "storage", "__pycache__",
    ".pytest_cache", "test-results", "test-results-verificacion-090412",
}
EXCLUDED_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3", ".mp4", ".mov", ".zip"}
SECRET_MARKERS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(rb"\bsk-[A-Za-z0-9]{20,}\b"),
]


def allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if any(part.startswith(".env") for part in rel.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.is_symlink() or not path.is_file():
        return False
    return True


def code_paths() -> list[Path]:
    paths: set[Path] = set()
    for relative in CODE_DIRS:
        folder = ROOT / relative
        if not folder.is_dir():
            raise FileNotFoundError(folder)
        paths.update(path for path in folder.rglob("*") if allowed(path))
    for relative in CODE_FILES:
        path = ROOT / relative
        if not allowed(path):
            raise FileNotFoundError(path)
        paths.add(path)
    return sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix())


def review_paths() -> list[Path]:
    paths = [REVIEW / name for name in REVIEW_FILES]
    paths.extend(sorted((REVIEW / "CAPTURAS").glob("*.png")))
    if not all(path.is_file() for path in paths):
        raise FileNotFoundError("Falta un documento o una captura de revisión")
    return paths


def main() -> None:
    entries: list[tuple[str, Path]] = []
    entries.extend(
        (f"REVISION_UNIFICACION/{path.relative_to(REVIEW).as_posix()}", path)
        for path in review_paths()
    )
    entries.extend((f"CODIGO/{path.relative_to(ROOT).as_posix()}", path) for path in code_paths())

    # La copia conserva cambios sin confirmar de los archivos fuente, pero nunca
    # incorpora bases de datos, cookies, .env, Git, dependencias ni builds.
    manifest_lines = ["SHA-256  bytes  ruta_en_zip"]
    for archive_name, path in entries:
        data = path.read_bytes()
        if archive_name.startswith("CODIGO/"):
            for marker in SECRET_MARKERS:
                if marker.search(data):
                    raise RuntimeError(f"Posible secreto en {path.relative_to(ROOT)}; revisar antes de empaquetar")
        digest = hashlib.sha256(data).hexdigest()
        manifest_lines.append(f"{digest}  {len(data)}  {archive_name}")
    MANIFEST.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    with ZipFile(ZIP_PATH, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for archive_name, path in entries:
            archive.write(path, archive_name)
        archive.write(MANIFEST, "REVISION_UNIFICACION/MANIFIESTO_ARCHIVOS_SHA256.txt")
    with ZipFile(ZIP_PATH) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"CRC inválido en {bad}")
        recovered = [name for name in archive.namelist() if name.startswith("CODIGO/flow-recovery/source/")]
        if len(recovered) != 17:
            raise RuntimeError(f"Se esperaban 17 fuentes Flow, encontradas {len(recovered)}")
    print(f"ZIP: {ZIP_PATH}")
    print(f"Entradas: {len(entries) + 1}; Flow: {len(recovered)}; bytes: {ZIP_PATH.stat().st_size}")


if __name__ == "__main__":
    main()
