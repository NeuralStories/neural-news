"""Registro estructurado: una línea JSON por evento (NN-110.e).

Motivo: con el registro en texto libre, un fallo del worker solo se podía leer
«a ojo» en el log. Con JSON, cada evento es consultable y correlacionable
(job_id, tipo, duración, estado) sin parsear mensajes.

Convenio de la traza del worker:
  - **stdout** → consola legible para la persona delante del terminal.
  - **stderr** → eventos JSON, que es lo que consulta el resto del sistema.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import sys


class JsonFormatter(logging.Formatter):
    """Cada registro se serializa como una línea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", "log"),
            "message": record.getMessage(),
        }
        campos = getattr(record, "fields", None)
        if isinstance(campos, dict):
            payload.update(campos)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(stream=None) -> None:
    """Instala el registro estructurado. Idempotente (no duplica handlers)."""
    raiz = logging.getLogger()
    if any(getattr(h, "_neural_json", False) for h in raiz.handlers):
        return
    for h in list(raiz.handlers):
        raiz.removeHandler(h)
    manejador = logging.StreamHandler(stream or sys.stderr)
    manejador.setFormatter(JsonFormatter())
    manejador._neural_json = True  # type: ignore[attr-defined]
    raiz.addHandler(manejador)
    raiz.setLevel(os.getenv("NEURAL_LOG_LEVEL", "INFO").upper())


def log_event(logger: logging.Logger, event: str, message: str, **fields) -> None:
    """Registra un evento con campos estructurados (`extra` no lo usa el
    formateador estándar, por eso van en `fields`)."""
    logger.info(message, extra={"event": event, "fields": fields})
