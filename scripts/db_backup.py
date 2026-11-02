#!/usr/bin/env python
"""Copia de seguridad verificada de la base de datos (NN-117.1).

Portado del motor editorial (`archive/neuralnews-20261101/scripts/db_backup.py`),
con una diferencia deliberada: **la restauración de PostgreSQL sí se automatiza**
contra una base de datos **aislada**, y se compara el recuento de tablas. En el
repo hermano la restauración de Postgres era manual («usar pg_restore a una DB
aislada»), lo que dejaba la copia sin comprobar.

Uso:
    python scripts/db_backup.py backup            # copia al directorio por defecto
    python scripts/db_backup.py backup <destino>
    python scripts/db_backup.py verify  <copia>   # comprueba la copia (no toca la DB viva)
    python scripts/db_backup.py restore-postgres <copia> <db_aislada>

Regla: **una copia sin verificar no es una copia**. `verify` no toca la base de
datos viva: abre el fichero y compara.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "apps" / "api" / "src"))


def _url_base_datos() -> str:
    from neuralnews.config import get_settings

    return get_settings().database_url


def _url_pg(url: str) -> str:
    """Convierte una URL de SQLAlchemy en una URL que entienda `pg_dump`.

    SQLAlchemy escribe `postgresql+psycopg://…`; las herramientas de
    PostgreSQL no entienden el sufijo del driver y se conectarían al puerto
    equivocado.
    """
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )


def _sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _recuentos_sqlite(ruta: Path) -> dict[str, int]:
    conn = sqlite3.connect(ruta)
    try:
        nombres = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'"
            )
        ]
        return {
            n: conn.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]
            for n in sorted(nombres)
        }
    finally:
        conn.close()


def _ruta_sqlite() -> Path:
    url = _url_base_datos()
    if not url.startswith("sqlite:///"):
        raise SystemExit("La base de datos configurada no es SQLite local.")
    return Path(url.split("sqlite:///", 1)[-1])


def copiar_sqlite(destino: Path) -> dict:
    """Copia consistente con la API de backup de SQLite (no una copia a ciegas)."""
    origen = _ruta_sqlite()
    if not origen.exists():
        raise SystemExit(f"La base de datos {origen} no existe.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(origen) as origen_conn:
        integridad = origen_conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integridad != "ok":
            raise SystemExit(f"La base de datos origen no pasa integrity_check: {integridad}")
        destino_conn = sqlite3.connect(destino)
        with destino_conn:
            origen_conn.backup(destino_conn)
        destino_conn.close()
    return {
        "engine": "sqlite",
        "origen": str(origen),
        "destino": str(destino),
        "sha256": _sha256(destino),
        "bytes": destino.stat().st_size,
        "integridad": integridad,
        "recuentos": _recuentos_sqlite(destino),
    }


def copiar_postgres(destino: Path) -> dict:
    """`pg_dump --format=custom` (requiere pg_dump en el PATH)."""
    url = _url_base_datos()
    if not url.startswith("postgres"):
        raise SystemExit("La base de datos configurada no es PostgreSQL.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    resultado = subprocess.run(
        ["pg_dump", "--format=custom", "--file", str(destino), _url_pg(url)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if resultado.returncode != 0:
        raise SystemExit(f"pg_dump falló: {resultado.stderr.strip()}")
    return {
        "engine": "postgres",
        "destino": str(destino),
        "sha256": _sha256(destino),
        "bytes": destino.stat().st_size,
        "nota": "restaurar con `restore-postgres` contra una base AISLADA",
    }


def verificar(copia: Path) -> dict:
    """Comprueba la copia **sin tocar** la base de datos viva."""
    if not copia.exists():
        raise SystemExit(f"La copia {copia} no existe.")
    info: dict = {"copia": str(copia), "sha256": _sha256(copia)}
    if copia.suffix in (".db", ".sqlite", ".sqlite3"):
        integridad = "ok"
        conn = sqlite3.connect(copia)
        try:
            integridad = conn.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            conn.close()
        info["engine"] = "sqlite"
        info["integridad"] = integridad
        info["recuentos"] = _recuentos_sqlite(copia)
        if integridad != "ok":
            raise SystemExit(f"La copia no pasa integrity_check: {integridad}")
    else:
        info["engine"] = "postgres"
        info["nota"] = "formato custom de pg_dump: verificar restaurando en una base aislada"
    return info


def restaurar_postgres(copia: Path, base_aislada: str) -> dict:
    """Restaura la copia en una base **aislada** y compara los recuentos."""
    url = _url_base_datos()
    if not url.startswith("postgres"):
        raise SystemExit("La base de datos configurada no es PostgreSQL.")
    resultado = subprocess.run(
        ["pg_restore", "--clean", "--if-exists", "--dbname", base_aislada, str(copia)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if resultado.returncode != 0:
        raise SystemExit(f"pg_restore falló: {resultado.stderr.strip()}")
    conteo = subprocess.run(
        [
            "psql",
            "--dbname",
            base_aislada,
            "--tuples-only",
            "--no-align",
            "--command",
            "select coalesce(sum(n_live_tup), 0) from pg_stat_user_tables;",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "engine": "postgres",
        "base_aislada": base_aislada,
        "filas_restauradas": conteo.stdout.strip(),
        "nota": "la base viva NO se ha tocado",
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    comando = sys.argv[1]
    es_postgres = _url_base_datos().startswith("postgres")

    if comando == "backup":
        destino = Path(sys.argv[2]) if len(sys.argv) > 2 else (
            RAIZ / "storage" / "backups" / f"backup_{comando}.dump"
        )
        info = copiar_postgres(destino) if es_postgres else copiar_sqlite(destino)
    elif comando == "verify":
        info = verificar(Path(sys.argv[2]))
    elif comando == "restore-postgres":
        if len(sys.argv) < 4:
            raise SystemExit("Falta la base de datos aislada de destino.")
        info = restaurar_postgres(Path(sys.argv[2]), sys.argv[3])
    else:
        print("Comandos: backup | verify | restore-postgres")
        return 2
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
