# Fuentes públicas consultadas — corte 30/10/2026

*Estas referencias no sustituyen las fuentes del proyecto Flow aportado. Las capacidades y precios deben revalidarse al implementar o contratar.*

- Google Flow, crear vídeos, personajes `@` e ingredientes: https://support.google.com/flow/answer/16353334?hl=es . Documenta la interfaz Flow, NO concede automáticamente una API externa compatible con su SDK interno.
- Google Flow, modelos y opciones soportadas por modo: https://support.google.com/flow/answer/16352836?hl=es . Duración 4/6/8 según modelo y función, no asumir 8 universal.
- Google Flow, edición con Omni Flash y clips/vídeos: https://support.google.com/flow/answer/16935718?hl=es-ES . Capacidades sujetas a país/modelo/cuenta.
- Google AI API vídeo, aviso de cierre Veo Preview 22 octubre 2026: https://ai.google.dev/gemini-api/docs/video . Verificar modelos vivos antes de programar.
- Gemini API, salida estructurada y necesidad de validar semántica: https://ai.google.dev/gemini-api/docs/structured-output . Un JSON correcto no es una afirmación cierta.
- Next.js Security advisories: https://github.com/vercel/next.js/security/advisories ; aviso 14 octubre: https://nextjs.org/blog/nextjs-security-update-october-14-2026 ; referencia Gobierno de Singapur: https://www.csa.gov.sg/alerts-and-advisories/alerts/al-2026-148/ . Verificar y fijar revisión parcheada disponible.
- Next.js policy: https://nextjs.org/support-policy . Seleccionar rama soportada.
- PostgreSQL SKIP LOCKED: https://www.postgresql.org/about/featurematrix/detail/skip-locked-clause/ . Útil para cola DB, complementado con leases y reconciliación.
- Remotion licencias: https://www.remotion.pro/license y https://www.remotion.dev/docs/license/pricing . El coste/licencia depende de tamaño y tipo de automatización.
- OWASP SSRF prevention: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html . Controlar esquemas, hosts, DNS, redirects y rangos de red.
- OWASP Secrets management: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html . Protección de claves y rotación.
- Python urllib.robotparser: https://docs.python.org/3/library/urllib.robotparser.html . Apoyo a políticas de rastreo, no sustituto de términos de uso.
- FFmpeg/ffprobe: https://ffmpeg.org/documentation.html . Render y validación real de medios.

## Etiquetado de evidencia
`SOURCE_FLOW` = código, manifiesto o informe incluido; `SOURCE_USER` = requisito explícito; `PUBLIC_DOCS` = documentación pública; `ARCHITECTURAL_DECISION` = propuesta comprobable; `UNVERIFIED` = requiere permiso o prueba. Cada afirmación crítica del proyecto debe conservar estas diferencias para impedir confundir inspiración con función operativa.
