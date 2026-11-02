"""NN-110 / B24 — Dos borradores simultáneos no chocan con la restricción UNIQUE.

El número de versión se calculaba como «el último + 1»: dos borradores a la vez
sobre la misma noticia calculaban el mismo número y el `INSERT` fallaba con
`UNIQUE constraint failed: script_versions.story_id, script_versions.version`.
La sesión quedaba rota y el trabajo se perdía con un error interno.

Ahora el intento va dentro de un *savepoint*: si choca, sólo se revierte ese
savepoint y se recalcula el número libre.
"""
from __future__ import annotations

from sqlalchemy import select

from neuralnews.db import get_session_factory
from neuralnews.models import ScriptVersion
from neuralnews.services import scripts as scripts_service


def _crear_noticia(contenido: str) -> int:
    from neuralnews.models import Story, utcnow

    with get_session_factory()() as db:
        story = Story(
            topic_key="carrera-de-version",
            title="Noticia de la carrera",
            summary="Noticia de la carrera",
            status="CANDIDATE",
            created_at=utcnow(),
        )
        db.add(story)
        db.flush()
        story_id = story.id
        db.commit()
    return story_id


def test_dos_borradores_simultaneos_no_chocan(app_env, monkeypatch):
    """Simula la carrera: la primera lectura del máximo devuelve un valor viejo."""
    story_id = _crear_noticia("Cortexa Labs ha anunciado Radar.")

    # Ya existe una versión 1 en la base de datos.
    with get_session_factory()() as db:
        db.add(
            ScriptVersion(
                story_id=story_id,
                version=1,
                content="primera versión",
                language="es-ES",
                author_type="user",
                content_hash="x",
            )
        )
        db.commit()

    # La primera llamada a `latest_version` es la comprobación de «texto
    # idéntico» de `_add_version` (necesita el valor real). Las siguientes —la
    # de `_create_version`— ven un máximo **obsoleto**, como ocurriría si otro
    # borrador se crease entre la lectura y la inserción.
    llamadas = {"n": 0}
    original = scripts_service.latest_version

    def _latest_obsoleto(db, sid):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            # La lectura que hace `_create_version` ve un máximo **obsoleto**:
            # el cálculo daría el número 1 → choca con la restricción UNIQUE
            # de (story_id, version).
            return ScriptVersion(story_id=sid, version=0, content="", language="es-ES",
                                 author_type="AI", content_hash="obsoleto")
        # El resto (la comprobación de «idéntico» y el reintento tras el
        # choque) ven el valor real: en producción, cuando el INSERT choca, la
        # fila del otro borrador ya está confirmada y el reintento encuentra el
        # número libre.
        return original(db, sid)

    monkeypatch.setattr(scripts_service, "latest_version", _latest_obsoleto)

    with get_session_factory()() as db:
        from neuralnews.models import Story

        story = db.get(Story, story_id)
        assert story is not None
        version = scripts_service.create_draft_version(db, story)
        assert version.version == 2, (
            f"debería haberse reasignado el número libre, quedó en {version.version}"
        )
        db.commit()

    with get_session_factory()() as db:
        numeros = [
            v.version
            for v in db.scalars(
                select(ScriptVersion).where(ScriptVersion.story_id == story_id)
            ).all()
        ]
    assert sorted(numeros) == [1, 2], numeros


def test_el_numero_de_version_es_unico(app_env):
    """Varias ediciones seguidas numeran 1, 2, 3… sin huecos ni repeticiones.

    Se usa `save_user_edit` (contenido distinto cada vez): el proveedor de
    demostración devuelve siempre el **mismo** texto, y en ese caso el sistema
    no crea una versión repetida (eso es correcto y es otra cosa).
    """
    story_id = _crear_noticia("Vireo AI levanta 40 millones.")
    with get_session_factory()() as db:
        from neuralnews.models import Story

        story = db.get(Story, story_id)
        assert story is not None
        for i in range(3):
            v = scripts_service.save_user_edit(
                db,
                story,
                content=f"Versión {i + 1} del guion con texto distinto.",
                expected_version=i,
                actor_id="demo",
            )
            assert v.version == i + 1, f"esperaba {i + 1}, obtuve {v.version}"
        db.commit()
