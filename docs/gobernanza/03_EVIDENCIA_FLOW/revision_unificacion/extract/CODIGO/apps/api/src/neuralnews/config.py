"""Configuración por entorno. Ninguna clave real se guarda en el repositorio."""
from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
STORAGE_DIR = REPO_ROOT / "storage"


class Settings(BaseSettings):
    """Ajustes leídos de variables NEURAL_* o de .env en la raíz del monorepo."""

    model_config = SettingsConfigDict(
        env_prefix="NEURAL_", env_file=str(REPO_ROOT / ".env"), extra="ignore"
    )

    app_name: str = "neural.news"
    database_url: str = f"sqlite:///{(REPO_ROOT / 'storage' / 'neural-news.db').as_posix()}"
    demo_mode: bool = True

    # Autenticación básica de un único editor. En demo se permite el acceso rápido.
    admin_username: str = "editor"
    admin_password: str = ""

    session_ttl_minutes: int = 60 * 12
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Studio local (apps/studio: vite dev 5173 / preview 4173)
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    # Descargas web (conector RSS/artículo)
    max_download_bytes: int = 5 * 1024 * 1024
    fetch_timeout_s: int = 20
    fetch_max_redirects: int = 3
    allowed_url_schemes: list[str] = ["http", "https"]
    blocked_hosts: list[str] = []
    # Hosts de confianza explícitos (p. ej. servidor de pruebas local); saltan el bloqueo de redes privadas.
    allowed_hosts: list[str] = []

    # Trabajos
    job_lease_seconds: int = 300
    job_max_attempts: int = 3

    # Costes: los servicios de pago empiezan desactivados por defecto.
    paid_services_enabled: bool = False
    budget_daily_eur: float = 0.0

    # Claves de proveedores (vacías = no configurado; el adaptador real no se puede usar).
    youtube_api_key: str = ""
    gemini_api_key: str = ""
    spotify_access_token: str = ""
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    search_api_key: str = ""
    search_base_url: str = "https://api.search.brave.com/res/v1/web/search"

    def secrets_status(self) -> dict[str, bool]:
        return {
            "youtube_api_key": bool(self.youtube_api_key),
            "gemini_api_key": bool(self.gemini_api_key),
            "spotify_access_token": bool(self.spotify_access_token),
            "llm_api_key": bool(self.llm_api_key),
            "search_api_key": bool(self.search_api_key),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def new_token() -> str:
    return secrets.token_urlsafe(32)
