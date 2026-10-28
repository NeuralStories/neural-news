# fixtures/

Los contenidos ficticios del modo demo (empresas, productos y personas inexistentes, marcados «DEMO») viven en el paquete Python:

- `apps/api/src/neuralnews/providers/fixtures.py` — vídeo ficticio (transcripción con marcas temporales), artículo sobre el mismo lanzamiento, artículo antiguo de 2024, episodio de Spotify sin transcripción y texto malicioso de prueba.

Las pruebas de `tests/` los consumen directamente, y el modo demo de los conectores los sirve cuando no hay claves configuradas. Las URLs de evidencia demo usan el dominio reservado `.invalid` (`demo.neuralnews.invalid`), imposible de resolver: nunca apuntan a recursos reales.
