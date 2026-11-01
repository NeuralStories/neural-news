"""Aplicación FastAPI principal. Arranque: `neuralnews-api` o `uvicorn neuralnews.main:app`."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api import auth, batches, ops, projects, sources, stories
from .config import get_settings
from .db import get_engine
from .models import Base


def create_app() -> FastAPI:
    settings = get_settings()
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

    # En la primera ejecución local (sin migraciones aplicadas) creamos el esquema.
    # En producción usar Alembic (infra/migrations).
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(get_engine())

    app.include_router(auth.router)
    app.include_router(sources.router)
    app.include_router(stories.router)
    app.include_router(batches.router)
    app.include_router(projects.router)
    app.include_router(ops.router)

    @app.get("/api/v1/health")
    def health() -> dict:
        return {
            "ok": True,
            "app": settings.app_name,
            "version": __version__,
            "demo_mode": settings.demo_mode,
        }

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("neuralnews.main:app", host="127.0.0.1", port=8000, reload=False)
