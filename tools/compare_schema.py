"""Compara el esquema de una base de datos con el de los modelos.

Uso:
    python tools/compare_schema.py [ruta.sqlite | postgresql+psycopg://...]

Para PostgreSQL hace falta el paquete `psycopg`.
"""
from __future__ import annotations

import sys

from neuralnews.models import Base

ESQUEMA = {
    "sqlite": "sqlite_master",
    "postgresql": "information_schema.tables",
}


def _columnas_sqlite(ruta: str) -> dict[str, set[str]]:
    import sqlite3

    conn = sqlite3.connect(ruta)
    try:
        tablas = {
            r[0]
            for r in conn.execute("select name from sqlite_master where type='table'")
        }
        tablas -= {"alembic_version", "sqlite_sequence"}
        return {
            t: {c[1] for c in conn.execute(f'PRAGMA table_info("{t}")')} for t in tablas
        }
    finally:
        conn.close()


def _columnas_postgres(url: str) -> dict[str, set[str]]:
    from sqlalchemy import create_engine, inspect

    motor = create_engine(url)
    try:
        insp = inspect(motor)
        tablas = set(insp.get_table_names()) - {"alembic_version"}
        return {t: {c["name"] for c in insp.get_columns(t)} for t in tablas}
    finally:
        motor.dispose()


def main() -> int:
    destino = sys.argv[1] if len(sys.argv) > 1 else "storage/neural-news.db"
    if destino.startswith("postgres"):
        real = _columnas_postgres(destino)
    else:
        real = _columnas_sqlite(destino)

    modelo = {
        tabla: {c.name for c in t.columns} for tabla, t in Base.metadata.tables.items()
    }

    print(f"destino            : {destino}")
    print(f"tablas en el modelo: {len(modelo)}")
    print(f"tablas en la base  : {len(real)}")
    solo_base = set(real) - set(modelo)
    solo_modelo = set(modelo) - set(real)
    print(f"solo en la base    : {sorted(solo_base) or '—'}")
    print(f"solo en el modelo  : {sorted(solo_modelo) or '—'}")

    problemas = 0
    print("\ncolumnas que faltan por tabla:")
    for tabla in sorted(modelo):
        if tabla not in real:
            continue
        faltan = modelo[tabla] - real[tabla]
        sobran = real[tabla] - modelo[tabla]
        if faltan or sobran:
            problemas += 1
            print(f"  {tabla}: faltan {sorted(faltan) or '—'} | sobran {sorted(sobran) or '—'}")
    if not problemas:
        print("  (ninguna)")

    if solo_base or solo_modelo or problemas:
        print("\nEl esquema NO coincide con los modelos.")
        return 1
    print("\nEl esquema coincide EXACTAMENTE con los modelos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
