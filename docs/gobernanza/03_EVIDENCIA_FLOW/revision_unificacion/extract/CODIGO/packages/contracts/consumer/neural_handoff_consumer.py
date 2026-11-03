"""Consumidor mínimo e independiente del contrato `production_handoff.v1`.

No depende del motor editorial (sólo de la biblioteca estándar y de
`jsonschema`): valida el documento contra el JSON Schema, recomputa el hash de
cada guion aprobado y evita importar dos veces el mismo traspaso o la misma
noticia+revisión. Pensado para que NeuralStories Studio lo use al recibir
noticias desde editorial.

Uso:
    from neural_handoff_consumer import HandoffRegistry, import_handoff
    registry = HandoffRegistry(ruta_json_opcional)
    noticias = import_handoff(documento, registry)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "El consumidor necesita el paquete 'jsonschema' (pip install jsonschema)."
    ) from exc

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "production_handoff.v1.schema.json"
SCHEMA_VERSION = "production_handoff.v1"


class HandoffValidationError(ValueError):
    """El documento no cumple el contrato o su contenido no es íntegro."""


class DuplicateHandoffError(ValueError):
    """El traspaso (o una noticia+revisión) ya se había importado."""


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_document(document: dict) -> None:
    """Valida la estructura completa contra el esquema Draft 2020-12."""
    schema = load_schema()
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.path) or "(raíz)"
        raise HandoffValidationError(
            f"El traspaso no cumple el contrato {SCHEMA_VERSION} en «{location}»: {first.message}"
        )


def verify_story_integrity(story: dict) -> None:
    """Recomputa el SHA-256 del guion y lo compara con el hash transportado."""
    expected = hashlib.sha256(story["approved_script"].encode("utf-8")).hexdigest()
    if expected != story["content_hash"]:
        raise HandoffValidationError(
            f"La noticia {story['story_id']} (revisión {story['revision']}) llego con el guion "
            "alterado: el hash de contenido no coincide. Se rechaza para no producir sobre "
            "un texto que editorial no aprobó."
        )


@dataclass
class HandoffRegistry:
    """Registro persistente opcional de traspasos importados (anti-duplicados)."""

    path: Path | None = None
    entries: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.path is not None and self.path.exists():
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))["entries"]

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"entries": self.entries}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def seen_handoff(self, handoff_id: str) -> bool:
        return any(entry["handoff_id"] == handoff_id for entry in self.entries)

    def seen_story(self, story_id: str, revision: int) -> dict | None:
        for entry in self.entries:
            for item in entry["stories"]:
                if item["story_id"] == story_id and item["revision"] == revision:
                    return entry
        return None


def _normalize_story(story: dict) -> dict:
    """Mapa de trabajo para Studio: campos que la preproducción necesita."""
    return {
        "story_id": story["story_id"],
        "revision": story["revision"],
        "title": story["title"],
        "summary": story["summary"],
        "language": story["language"],
        "script": story["approved_script"],
        "script_version_id": story["script_version_id"],
        "content_hash": story["content_hash"],
        "sources": story["sources"],
        "approval": story["editorial_approval"],
        "handoff_id": None,  # se rellena en import_handoff
    }


def import_handoff(document: dict, registry: HandoffRegistry | None = None) -> list[dict]:
    """Valida, verifica y acepta un traspaso. Devuelve las noticias listas para Studio.

    Lanza `HandoffValidationError` si el documento no cumple el contrato o algún
    guion llega alterado, y `DuplicateHandoffError` si ya se había importado.
    """
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION:
        raise HandoffValidationError(
            f"Este consumidor sólo acepta documentos «{SCHEMA_VERSION}»."
        )
    validate_document(document)
    for story in document["stories"]:
        verify_story_integrity(story)
    if registry is not None:
        if registry.seen_handoff(document["handoff_id"]):
            raise DuplicateHandoffError(
                f"El traspaso {document['handoff_id']} ya se había importado: no se vuelve a cargar."
            )
        for story in document["stories"]:
            previous = registry.seen_story(story["story_id"], story["revision"])
            if previous is not None and previous["handoff_id"] != document["handoff_id"]:
                raise DuplicateHandoffError(
                    f"La noticia {story['story_id']} revisión {story['revision']} ya llegó en el "
                    f"traspaso {previous['handoff_id']}: no se importa dos veces."
                )
    stories = [_normalize_story(story) for story in document["stories"]]
    for item in stories:
        item["handoff_id"] = document["handoff_id"]
    if registry is not None:
        registry.entries.append(
            {
                "handoff_id": document["handoff_id"],
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "mode": document["mode"],
                "stories": [
                    {"story_id": s["story_id"], "revision": s["revision"]}
                    for s in document["stories"]
                ],
            }
        )
        registry.save()
    return stories
