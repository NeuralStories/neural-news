"""Genera el contrato OpenAPI de la API v1 en packages/contracts/openapi.json.

Uso (desde la raíz del monorepo):
    python apps/api/scripts/export_openapi.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # raíz del monorepo (neural-news/)
sys.path.insert(0, str(REPO_ROOT / "apps" / "api" / "src"))

from neuralnews.main import app  # noqa: E402


def main() -> int:
    target = REPO_ROOT / "packages" / "contracts" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    target.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    paths = len(schema.get("paths", {}))
    print(f"Contrato OpenAPI exportado a {target} ({paths} rutas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
