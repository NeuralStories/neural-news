"""Generación audiovisual simulada (Fase 5, T502/T508).

Interfaz de proveedor sustituible: cada adaptador declara sus capacidades y
devuelve un resultado normalizado. `SimulatedAvProvider` produce artefactos
deterministas sin llamar a ningún servicio de pago (coste 0): mismo
contenido de entrada → mismo artefacto (idempotente). Los adaptadores reales
se incorporarán sólo con autorización explícita (T512).
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field

from .. import config

AvJobKind = Literal["image", "video", "voice"]


class AvGenerationError(Exception):
    """La petición de generación no es válida para el proveedor."""


class AvGenerationRequest(BaseModel):
    kind: AvJobKind
    project_id: str
    scene_index: int = Field(ge=0)
    prompt: str = Field(min_length=1)
    output_format: Literal["9:16", "16:9"] = "9:16"
    language: str = "es-ES"


class AvGenerationResult(BaseModel):
    kind: AvJobKind
    provider: str
    artifact_relpath: str
    sha256: str
    cost_estimate_eur: float = 0.0
    simulated: bool = True


class AvProvider:
    """Contrato mínimo que debe cumplir cualquier adaptador (T508)."""

    name: str = "base"
    simulated: bool = False
    capabilities: dict = {}

    def generate(self, request: AvGenerationRequest) -> AvGenerationResult:
        raise NotImplementedError


class SimulatedAvProvider(AvProvider):
    """Artefactos simulados deterministas, escritos bajo `storage/av/`."""

    name = "simulated_av"
    simulated = True
    capabilities = {
        "image": {"formats": ["9:16", "16:9"], "note": "placeholder determinista"},
        "video": {"formats": ["9:16", "16:9"], "durations_s": [8], "note": "placeholder determinista"},
        "voice": {"locales": ["es-ES"], "note": "placeholder determinista"},
    }

    def generate(self, request: AvGenerationRequest) -> AvGenerationResult:
        if request.kind not in self.capabilities:
            raise AvGenerationError(
                f"El proveedor {self.name} no soporta el tipo «{request.kind}»."
            )
        if not request.prompt.strip():
            raise AvGenerationError("El prompt de generación está vacío.")

        fingerprint = hashlib.sha256(
            json.dumps(
                request.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        artifact_relpath = f"av/{request.kind}-{fingerprint[:16]}.json"
        path = config.STORAGE_DIR / "av" / f"{request.kind}-{fingerprint[:16]}.json"

        if not path.exists():  # idempotencia: mismo pedido → mismo artefacto
            path.parent.mkdir(parents=True, exist_ok=True)
            artifact = {
                "simulated": True,
                "kind": request.kind,
                "project_id": request.project_id,
                "scene_index": request.scene_index,
                "output_format": request.output_format,
                "language": request.language,
                "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
                "prompt_chars": len(request.prompt),
                "provider": self.name,
                "fingerprint": fingerprint,
            }
            payload = json.dumps(artifact, ensure_ascii=False, indent=2)
            path.write_text(payload, encoding="utf-8")

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return AvGenerationResult(
            kind=request.kind,
            provider=self.name,
            artifact_relpath=artifact_relpath,
            sha256=digest,
        )
