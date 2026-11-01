"""El esquema de la base de datos sale SOLO de Alembic, y coincide con los modelos.

Este fichero es la red de seguridad del hallazgo P3/B20: `create_all()` solo
crea tablas nuevas y no añade columnas a las existentes, así que una base de
datos de una versión anterior se quedaba desfasada en silencio. En producción
eso dejó el Studio entero devolviendo 500 («no such column:
generated_takes.needs_review») sin que ninguna prueba lo detectara.

Tres comprobaciones:
  1) Las migraciones aplicadas desde cero producen EXACTAMENTE el esquema de
     los modelos (si alguien añade una columna al modelo y olvida la
     migración, aquí falla).
  2) La aplicación NO llama a `create_all()` al arrancar.
  3) Una base recién creada queda en la revisión 'head' y no le queda nada por
     migrar frente a los modelos.
"""
from __future__ import annotations

import ast
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from neuralnews.models import Base

MIGRATIONS = Path(__file__).resolve().parents[1] / "infra" / "migrations"


def _aplicar_migraciones(db_path: Path, monkeypatch) -> None:
    """Aplica `alembic upgrade head` sobre una base de datos nueva.

    `env.py` toma la URL de `NEURAL_DATABASE_URL`, así que hay que fijarla
    antes de invocar Alembic.
    """
    from alembic import command
    from alembic.config import Config

    monkeypatch.setenv("NEURAL_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cfg = Config(str(MIGRATIONS / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS))
    command.upgrade(cfg, "head")


def _esquema_real(engine) -> dict[str, set[str]]:
    insp = inspect(engine)
    return {
        tabla: {c["name"] for c in insp.get_columns(tabla)}
        for tabla in insp.get_table_names()
        if tabla != "alembic_version"
    }


def test_las_migraciones_producen_el_esquema_de_los_modelos(tmp_path, monkeypatch):
    """`alembic upgrade head` desde cero == `Base.metadata` (tablas y columnas)."""
    db_path = tmp_path / "esquema.db"
    _aplicar_migraciones(db_path, monkeypatch)

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        real = _esquema_real(engine)
        modelo = {
            tabla: {c.name for c in tabla_modelo.columns}
            for tabla, tabla_modelo in Base.metadata.tables.items()
        }
        assert set(real) == set(modelo), (
            f"tablas distintas: solo en la base {set(real) - set(modelo)}, "
            f"solo en el modelo {set(modelo) - set(real)}"
        )
        for tabla in sorted(modelo):
            faltan = modelo[tabla] - real[tabla]
            sobran = real[tabla] - modelo[tabla]
            assert not faltan, f"{tabla}: faltan columnas {sorted(faltan)}"
            assert not sobran, f"{tabla}: columnas de más {sorted(sobran)}"
    finally:
        engine.dispose()


def test_la_aplicacion_no_crea_el_esquema_con_create_all():
    """El arranque no puede volver a introducir la deriva del esquema."""
    from neuralnews import main as main_mod

    arbol = ast.parse(Path(main_mod.__file__).read_text(encoding="utf-8"))
    llamadas = [
        n
        for n in ast.walk(arbol)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "create_all"
    ]
    assert not llamadas, "create_all solo crea tablas nuevas: el esquema sale de Alembic"
    assert hasattr(main_mod, "ensure_schema")


def test_la_base_de_datos_arranca_con_la_ultima_migracion(tmp_path, monkeypatch):
    """Una base recién creada queda en la revisión 'head' y sin nada por migrar."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    db_path = tmp_path / "arranque.db"
    _aplicar_migraciones(db_path, monkeypatch)

    with sqlite3.connect(db_path) as conn:
        filas = conn.execute("select version_num from alembic_version").fetchall()
    assert filas, "la base debe registrar su versión de esquema"

    # La comparación directa entre el esquema migrado y los modelos: si no hay
    # diferencias, no queda nada por migrar.
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        with engine.connect() as conn:
            contexto = MigrationContext.configure(conn)
            diferencias = compare_metadata(contexto, Base.metadata)
    finally:
        engine.dispose()
    assert not diferencias, f"la base migrada difiere de los modelos: {diferencias}"
