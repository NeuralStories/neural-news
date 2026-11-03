"""Imprime el esquema de una petición del OpenAPI (herramienta de apoyo)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
d = json.loads((RAIZ / "docs" / "openapi.json").read_text(encoding="utf-8"))

ruta = sys.argv[1]
metodo = sys.argv[2] if len(sys.argv) > 2 else "post"

esquema = (
    d["paths"][ruta][metodo]
    .get("requestBody", {})
    .get("content", {})
    .get("application/json", {})
    .get("schema", {})
)
nombre = str(esquema.get("$ref", esquema)).split("/")[-1]
s = d["components"]["schemas"].get(nombre, {})
print("esquema:", nombre)
print("required:", s.get("required"))
for clave, valor in s.get("properties", {}).items():
    print(
        f"  {clave}: {valor.get('type')} default={valor.get('default')!r} "
        f"— {(valor.get('description') or '')[:70]}"
    )
