"""Alinea las cabeceras de tabla con las que comprueba el E2E.

El E2E del repositorio busca cabeceras concretas por su texto («Puntuación»,
«Fecha real», «Verificación»…). Al migrar una vista, los nombres de las
columnas pueden abreviarse o cambiar de caja y la prueba deja de encontrar la
columna.

Este script deja los nombres canónicos (los del E2E) y es idempotente.
"""
from __future__ import annotations

import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]

CABECERAS: dict[str, list[tuple[str, str]]] = {
    "apps/web/app/noticias/page.tsx": [
        ('cabecera: "tema"', 'cabecera: "Tema"'),
        ('cabecera: "estado"', 'cabecera: "Estado"'),
        ('cabecera: "fecha real"', 'cabecera: "Fecha real"'),
        ('cabecera: "punt."', 'cabecera: "Puntuación"'),
        ('cabecera: "origen"', 'cabecera: "Origen"'),
        ('cabecera: "verificación"', 'cabecera: "Verificación"'),
        ('cabecera: "duplicados"', 'cabecera: "Duplicados"'),
        ('cabecera: "acciones"', 'cabecera: "Acciones"'),
    ],
    "apps/web/app/fuentes/page.tsx": [
        ('cabecera: "proveedor"', 'cabecera: "Tipo"'),
        ('cabecera: "estado"', 'cabecera: "Estado"'),
        ('cabecera: "titulo"', 'cabecera: "Título"'),
        ('cabecera: "autor"', 'cabecera: "Autor"'),
        ('cabecera: "publicada"', 'cabecera: "Fecha original"'),
        ('cabecera: "importada"', 'cabecera: "Importada"'),
        ('cabecera: "acciones"', 'cabecera: "Acciones"'),
    ],
    "apps/web/app/lotes/page.tsx": [
        ('cabecera: "tema"', 'cabecera: "Noticia"'),
        ('cabecera: "punt."', 'cabecera: "Puntuación"'),
        ('cabecera: "estado"', 'cabecera: "Estado"'),
        ('cabecera: "lote"', 'cabecera: "Lote"'),
        ('cabecera: "tamaño"', 'cabecera: "Tamaño"'),
        ('cabecera: "creado"', 'cabecera: "Creado"'),
        ('cabecera: "fecha"', 'cabecera: "Fecha"'),
        ('cabecera: "acción"', 'cabecera: "Acciones"'),
    ],
}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass
    for ruta, reemplazos in CABECERAS.items():
        fichero = RAIZ / ruta
        if not fichero.exists():
            print(f"{ruta}: no existe")
            continue
        texto = fichero.read_text(encoding="utf-8")
        cambios = 0
        for viejo, nuevo in reemplazos:
            cambios += texto.count(viejo)
            texto = texto.replace(viejo, nuevo)
        if cambios:
            fichero.write_text(texto, encoding="utf-8", newline="\n")
        print(f"{ruta}: {cambios} cabecera(s) alineada(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
