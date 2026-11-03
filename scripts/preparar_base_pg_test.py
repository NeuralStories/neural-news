r"""Prepara una base de datos PostgreSQL **aislada** para la prueba real.

La prueba `tests/test_postgres_projects.py` (gate de la fase NN-107) solo se
ejecuta si existe la variable `NEURAL_TEST_POSTGRES`. Para no ensuciar la base
de desarrollo, este script crea una base aparte (por defecto `nn_pgtest`) en el
PostgreSQL local.

Uso:
    python scripts\preparar_base_pg_test.py
    $env:NEURAL_TEST_POSTGRES="postgresql+psycopg://neural@127.0.0.1:5433/nn_pgtest"
    python -m pytest tests\test_postgres_projects.py -q

El servidor local de PostgreSQL del workspace se arranca con:
    ..\pglocal\pgsql\bin\pg_ctl.exe -D ..\pglocal\data -l ..\pglocal\logfile.log -o "-p 5433" start
"""
from __future__ import annotations

import os
import sys

import psycopg

ADMIN_URL = os.environ.get(
    "NEURAL_PG_ADMIN_URL", "postgresql://neural@127.0.0.1:5433/postgres"
)
NOMBRE = os.environ.get("NEURAL_PG_TEST_DB", "nn_pgtest")


def main() -> int:
    try:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conexion:
            with conexion.cursor() as cur:
                cur.execute("select 1 from pg_database where datname = %s", (NOMBRE,))
                if cur.fetchone() is None:
                    cur.execute(f'create database "{NOMBRE}"')
                    print(f"Base '{NOMBRE}' creada.")
                else:
                    print(f"Base '{NOMBRE}' ya existía.")
    except psycopg.Error as exc:
        print(f"No se pudo preparar la base de prueba: {exc}", file=sys.stderr)
        print(
            "Comprueba que el PostgreSQL local esté en marcha (puerto 5433) o "
            "define NEURAL_PG_ADMIN_URL.",
            file=sys.stderr,
        )
        return 1
    print(f"NEURAL_TEST_POSTGRES=postgresql+psycopg://neural@127.0.0.1:5433/{NOMBRE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
