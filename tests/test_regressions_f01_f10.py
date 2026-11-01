"""NN-107 F5 — Regresiones de auditoría F-01…F-10 (02_AUDITORIA_FLOW.md).

Las fuentes recuperadas de Flow son evidencia; estos tests fijan, a nivel de
fichero y de API, las diez correcciones obligatorias de la reintegración.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STUDIO = REPO / "apps" / "web" / "features" / "studio"


def read(rel: str) -> str:
    return (STUDIO / rel).read_text(encoding="utf-8")


def test_f01_identity_is_maxdotai_only():
    constants = read("constants.ts")
    assert "MAXDOTAI_CANONICAL" in constants
    assert "NeuralDotAI" not in constants
    assert "@neuraldotai" not in constants
    assert "pendiente de confirmar" in constants  # handle aún sin confirmar en cuenta
    # Ningún componente revierte la identidad. Se recorre TODO el árbol del
    # Studio en vez de una lista fija: así la comprobación no se debilita si un
    # componente se retira (p. ej. el «Manual y Contrato», eliminado en NN-109.11)
    # y además cubre los componentes que la lista no mencionaba.
    revisados = 0
    for ts in sorted(STUDIO.rglob("*.ts*")):
        texto = ts.read_text(encoding="utf-8")
        revisados += 1
        assert "NeuralDotAI" not in texto, str(ts)
        assert "@neuraldotai" not in texto, str(ts)
    assert revisados > 10, "el recorrido debe seguir cubriendo el árbol del Studio"


def test_f02_no_initial_reference_is_preapproved():
    constants = read("constants.ts")
    assert "status: 'aprobado'" not in constants, "ningún activo arranca aprobado (F-02)"
    assert "INITIAL_VISUAL_REFERENCES" in constants


def test_f03_demo_editorial_references_are_not_news():
    constants = read("constants.ts")
    assert "status: 'pendiente'" in constants
    # Las referencias editoriales de demostración no pueden alimentar noticias
    assert "verificationStatus: 'verificado'" not in constants


def test_f04_voice_profile_is_labelled_hypothesis():
    voice = read("components/VoiceTab.tsx")
    assert "hipótesis Algenib, sin calibrar" in voice


def test_f05_no_forced_eight_second_cuts():
    analyzer = read("utils/scriptAnalyzer.ts")
    assert "exactly 8 seconds" not in analyzer
    assert "${estSec} seconds" in analyzer  # duración calculada por escena
    # El director persiste beats sin cortes impuestos (prueba de comportamiento)
    from tests.test_director_package import (  # noqa: F401
        test_director_never_forces_eight_second_cuts,
    )


def test_f06_generation_only_through_adapter_and_blocked_outside():
    adapter = read("flow/adapter.ts")
    assert "FlowUnavailableError" in adapter
    assert "BLOCKED" in adapter
    # Cero import del SDK propietario en el árbol integrado
    for ts in STUDIO.rglob("*.ts*"):
        if "extract" in str(ts):
            continue
        assert "'flow-sdk'" not in ts.read_text(encoding="utf-8"), str(ts)


def test_f07_mediaid_only_in_hosted_context():
    from neuralnews.api import projects as projects_mod

    source = Path(projects_mod.__file__).read_text(encoding="utf-8")
    assert "PROMPT_ONLY" in source
    # y la regla queda declarada en el paquete (prueba de comportamiento en F3)
    from tests.test_director_package import (  # noqa: F401
        test_flow_manual_package_requires_prompt_and_carries_full_instructions,
    )


def test_f08_imported_articles_start_unverified():
    constants = read("constants.ts")
    assert "verificationStatus: 'sin_verificar'" in constants
    assert "verificationStatus: 'verificado'" not in constants
    # El traspaso manual se retiró por duplicado (D7): la conexión es el dossier,
    # que lee los estados del motor y nunca verifica al importar (R-BUG-3).
    assert not (STUDIO / "integration" / "components" / "HandoffImport.tsx").exists()
    dossier = read("components/DossierPanel.tsx")
    assert "importar o traspasar nunca verifica" in dossier


def test_f09_dedup_is_canonical_first_and_labelled_heuristic():
    dedup = read("utils/newsDeduplication.ts")
    assert "URL canónica/fuente primero" in dedup  # capa canónica antes que léxica
    assert "heurística" in dedup and "revisión humana" in dedup
    # La puntuación de similitud se expone para la revisión
    assert "similarityScore" in dedup


def test_f10_backup_json_is_not_a_database_backup():
    backup = read("components/BackupModal.tsx")
    assert "no es un backup de la base de datos" in backup
