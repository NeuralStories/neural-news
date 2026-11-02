"""Aplicación FastAPI principal. Arranque: `neuralnews-api` o `uvicorn neuralnews.main:app`."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api import auth, batches, ops, projects, sources, stories
from .config import get_settings
from .db import session_scope
from .logging_setup import configure_logging
from .services import secrets as services_secrets
from . import vault

# Los errores del servidor se registran en el log en vez de filtrarse al cliente
# (hallazgo B7) y en vez de perderse por stderr (hallazgo P5). El formato es
# JSON por evento: cada línea se puede consultar sin parsear texto.
configure_logging()


def ensure_schema() -> None:
    """Aplica las migraciones pendientes: el esquema sale SOLO de Alembic.

    Antes se usaba `Base.metadata.create_all()`, que solo crea tablas nuevas y
    no añade columnas a las ya existentes. Una base de datos de una versión
    anterior se quedaba desfasada en silencio y la aplicación fallaba con
    «no such column» — fue lo que dejó el Studio entero devolviendo 500
    (hallazgo P3/B20). Ahora el arranque aplica las migraciones pendientes y,
    si no puede, lo dice en voz alta en vez de fingir que la base está bien.
    """
    migrations_dir = Path(__file__).resolve().parents[4] / "infra" / "migrations"
    if not (migrations_dir / "env.py").exists():
        raise RuntimeError(
            f"No se encuentra el directorio de migraciones en {migrations_dir}. "
            "El esquema solo puede aplicarse con Alembic; revise la instalación."
        )
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError as exc:  # pragma: no cover - dependencia declarada en pyproject
        raise RuntimeError(
            "Alembic es necesario para preparar el esquema: "
            "instale el backend con `python -m pip install -e \".[dev]\"`."
        ) from exc
    cfg = Config(str(migrations_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(migrations_dir))
    command.upgrade(cfg, "head")


def create_app() -> FastAPI:
    settings = get_settings()
    # La configuración incoherente para el entorno impide arrancar (ADR-017).
    # Es preferible no levantar a levantar exponiendo el modo demo o una
    # cookie de sesión sin cifrar por HTTPS.
    settings.comprobar()
    app = FastAPI(
        title="neural.news API",
        version=__version__,
        description="MVP editorial: fuentes, noticias, investigación, guiones, lotes y exportación.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # El esquema se prepara con Alembic, nunca con create_all (ver ensure_schema).
    ensure_schema()
    # La bóveda de secretos se carga en memoria (NN-117.3). Sin clave maestra la
    # aplicación **arranca igual**: lo que dependa de un secreto queda bloqueado
    # y se dice con claridad, en vez de fallar sin explicación.
    vault.configurar(settings.master_key)
    with session_scope() as db:
        services_secrets.cargar_desde_db(db)

    app.include_router(auth.router)
    app.include_router(sources.router)
    app.include_router(stories.router)
    app.include_router(batches.router)
    app.include_router(projects.router)
    app.include_router(ops.router)

    @app.get("/api/v1/health")
    def health() -> dict:
        """Estado real del sistema, no sólo «la API está viva» (NN-115.2).

        Comprueba lo que de verdad puede romper el producto: la base de datos,
        FFmpeg (montaje), yt-dlp (transcripción) y las claves de proveedor.
        """
        from .health import comprobar_salud

        return {
            "ok": True,
            "app": settings.app_name,
            "version": __version__,
            "demo_mode": settings.demo_mode,
            "env": settings.env,
            "checks": comprobar_salud(),
        }

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("neuralnews.main:app", host="127.0.0.1", port=8000, reload=False)
