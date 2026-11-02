"""Depuración: qué deja realmente `alembic upgrade head` en una base nueva."""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="alembic-probe-"))
DB = TMP / "probe.db"
os.environ["NEURAL_DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"

from alembic import command
from alembic.config import Config

MIGRATIONS = Path(r"C:\Users\haxth3\Documents\NeuralStories\neural-news\infra\migrations")
cfg = Config(str(MIGRATIONS / "alembic.ini"))
cfg.set_main_option("script_location", str(MIGRATIONS))
command.upgrade(cfg, "head")

with sqlite3.connect(DB) as conn:
    tablas = sorted(r[0] for r in conn.execute("select name from sqlite_master where type='table'"))
    print("tablas:", len(tablas))
    print("¿alembic_version existe?", "alembic_version" in tablas)
    if "alembic_version" in tablas:
        print("estructura:", conn.execute("PRAGMA table_info(alembic_version)").fetchall())
        print("filas:", conn.execute("select * from alembic_version").fetchall())
print("DB:", DB)
