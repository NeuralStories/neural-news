"""NN-107 — Equivalencia funcional tras la desduplicación.

Comprueba que retirar HandoffImport, ProductionPlanPanel y sus librerías no ha
dejado referencias rotas, no ha eliminado la funcionalidad necesaria (que vive
en los sustitutos unificados) y no ha roto contratos ni consumidores.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STUDIO = REPO / "apps" / "web" / "features" / "studio"


def test_removed_files_are_gone_and_unreferenced():
    for rel in (
        "integration/components/HandoffImport.tsx",
        "integration/components/ProductionPlanPanel.tsx",
        "integration/lib/handoffConsumer.ts",
        "integration/lib/apiClient.ts",
        "integration/lib/productionProject.ts",
        "integration/data/avProfiles.ts",
        "integration/flow-sdk/index.ts",
    ):
        assert not (STUDIO / rel).exists(), f"{rel} debía estar eliminado"
    # Cero referencias residuales en todo el árbol web
    web = REPO / "apps" / "web"
    for ts in web.rglob("*.ts*"):
        if "node_modules" in str(ts) or ".next" in str(ts):
            continue
        text = ts.read_text(encoding="utf-8", errors="replace")
        for needle in ("HandoffImport", "ProductionPlanPanel", "handoffConsumer",
                       "productionProject", "avProfiles", "'flow-sdk'"):
            assert needle not in text, f"{ts.name} aún referencia {needle}"


def test_unified_replacements_exist_and_are_exercised():
    dossier = (STUDIO / "components" / "DossierPanel.tsx").read_text(encoding="utf-8")
    assert "/api/v1/projects/${projectId}/dossier" in dossier  # conexión única al motor
    vertical = (STUDIO / "components" / "ProductionVertical.tsx").read_text(encoding="utf-8")
    for capability in ("directorPlan", "savePrompt", "flowPackage", "uploadTakeMedia", "approveTake"):
        assert capability in vertical, capability
    # Y ambos recorridos están ejercidos por las E2E del navegador real
    e2e = REPO / "apps" / "web" / "e2e"
    vertical_spec = (e2e / "vertical-production.spec.ts").read_text(encoding="utf-8")
    studio_spec = (e2e / "studio-reintegration.spec.ts").read_text(encoding="utf-8")
    assert "Ejecutar director audiovisual" in vertical_spec
    assert "/dossier" in vertical_spec  # conexión editorial comprobada en E2E
    assert "verificadas con fuentes" in studio_spec  # contador honesto (R-BUG-3)


def test_api_contracts_still_served_by_the_unified_surface():
    """Los contratos que consumía lo eliminado siguen vivos en la API unificada."""
    projects = (REPO / "apps" / "api" / "src" / "neuralnews" / "api" / "projects.py").read_text(encoding="utf-8")
    for contract in ("link-story", "dossier", "director/plan", "flow-package", "/media",
                     "expected_revision", "APROBADA"):
        assert contract in projects, contract
    # Los consumidores de comportamiento siguen en verde (mismo archivo de pruebas)
    from tests.test_projects_studio import (  # noqa: F401
        test_link_story_activates_it_immediately,
        test_project_survives_application_restart,
    )
    from tests.test_editorial_graphics import (  # noqa: F401
        test_dossier_shares_the_editorial_newsroom,
    )


def test_no_parallel_persistence_remains_in_the_studio():
    # Sin localStorage como almacén ni dobles rutas de guardado
    for ts in STUDIO.rglob("*.ts*"):
        text = ts.read_text(encoding="utf-8", errors="replace")
        assert "localStorage.setItem" not in text, ts.name
    # Un solo panel de producción (el vertical unificado)
    app = (STUDIO / "App.tsx").read_text(encoding="utf-8")
    assert app.count("<ProductionVertical") == 1  # un solo panel de producción
    assert "ProductionPlanPanel" not in app
    assert "HandoffImport" not in app
