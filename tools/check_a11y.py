"""Auditoría básica de accesibilidad de la web (NN-113.8).

Una auditoría de a11y hecha «a ojo» no es una evidencia: se puede decir que
la interfaz es accesible y no haber comprobado nada. Este script comprueba, en
el código, las tres cosas que más se olvidan y que bloquean el uso con teclado
o con lector de pantalla:

  1. **Botones sin nombre accesible**: un `<button>` sin texto y sin
     `aria-label`/`title` es un botón vacío: el lector de pantalla anuncia
     «botón» y el teclado no dice qué hace.
  2. **Imágenes sin `alt`**.
  3. **Campos de formulario sin etiqueta**: `<input>`, `<select>` y
     `<textarea>` sin `id`+`<label htmlFor>`, sin `aria-label` ni con un
     `<label>` envolvente.

**Nota sobre el analizador:** no se puede usar `[^>]*` para leer los atributos
de un elemento JSX: dentro de los manejadores hay flechas (`=>`) que
terminan la expresión regular antes de tiempo y el elemento se analiza a medias
(hasta el botón vacío del «Cargando...» de la aplicación). Aquí se escanea el
código carácter a carácter, contando llaves y comillas.

Uso:
    python tools/check_a11y.py           # informa y sale con error si hay bloqueantes
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"

RE_LABEL_HTMLFOR = re.compile(r"htmlFor\s*=\s*[\"'](?P<id>[^\"']+)[\"']", re.IGNORECASE)


def _ficheros() -> list[Path]:
    return [
        p
        for p in WEB.rglob("*")
        if p.suffix == ".tsx"
        and "node_modules" not in p.parts
        and ".next" not in p.parts
    ]


def _elementos(texto: str, etiqueta: str):
    """Devuelve (atributos, cuerpo, posición) de cada elemento `<etiqueta>`.

    El escaneo respeta las llaves `{...}` y las comillas, de modo que un
    manejador como `onClick={() => setX(true)}` no rompe la lectura.
    """
    i = 0
    while True:
        inicio = texto.find(f"<{etiqueta}", i)
        if inicio == -1:
            return
        i = inicio + 1 + len(etiqueta)
        if i < len(texto) and (texto[i].isalnum() or texto[i] in "-_"):
            continue  # era otro nombre: `<buttonX`
        j = i
        profundidad = 0
        comilla: str | None = None
        while j < len(texto):
            c = texto[j]
            if comilla:
                if c == "\\":
                    j += 2
                    continue
                if c == comilla:
                    comilla = None
            elif c in "\"'`":
                comilla = c
            elif c == "{":
                profundidad += 1
            elif c == "}":
                profundidad -= 1
            elif c == ">" and profundidad == 0:
                break
            j += 1
        if j >= len(texto):
            return
        atributos = texto[i:j]
        if texto[j - 1] == "/":
            cuerpo = ""
            fin = j + 1
        else:
            cierre = texto.find(f"</{etiqueta}", j)
            if cierre == -1:
                cuerpo = texto[j + 1 :]
                fin = len(texto)
            else:
                cuerpo = texto[j + 1 : cierre]
                fin = cierre
        yield atributos, cuerpo, inicio
        i = fin


def _tiene_texto(cuerpo: str) -> bool:
    """¿El elemento tiene texto visible (una etiqueta de icono cuenta como texto)?"""
    limpio = re.sub(r"<[^>]+>", " ", cuerpo)
    limpio = limpio.replace("{", " ").replace("}", " ")
    return bool(limpio.strip())


def bloqueantes_boton() -> list[str]:
    problemas = []
    for fichero in _ficheros():
        texto = fichero.read_text(encoding="utf-8", errors="replace")
        for atributos, cuerpo, inicio in _elementos(texto, "button"):
            if "aria-label" in atributos or "title=" in atributos:
                continue
            if not _tiene_texto(cuerpo):
                numero = texto[:inicio].count("\n") + 1
                problemas.append(
                    f"{fichero.relative_to(RAIZ)}:{numero} — <button> sin texto ni aria-label"
                )
    return problemas


def bloqueantes_imagen() -> list[str]:
    problemas = []
    for fichero in _ficheros():
        texto = fichero.read_text(encoding="utf-8", errors="replace")
        for atributos, _cuerpo, inicio in _elementos(texto, "img"):
            if "alt=" not in atributos:
                numero = texto[:inicio].count("\n") + 1
                problemas.append(f"{fichero.relative_to(RAIZ)}:{numero} — <img> sin alt")
    return problemas


def avisos_campo() -> list[str]:
    """Campos sin etiqueta: aviso, no bloqueante (pueden tener un label envolvente)."""
    avisos = []
    for fichero in _ficheros():
        texto = fichero.read_text(encoding="utf-8", errors="replace")
        etiquetas = set(RE_LABEL_HTMLFOR.findall(texto))
        for etiqueta in ("input", "select", "textarea"):
            for atributos, _cuerpo, inicio in _elementos(texto, etiqueta):
                if "aria-label" in atributos or "aria-labelledby" in atributos:
                    continue
                identificador = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", atributos)
                if identificador and identificador.group(1) in etiquetas:
                    continue
                # Label envolvente: el campo está dentro de un <label>…</label>.
                # Tras el último `<label` no debe aparecer ningún `</label>`.
                antes = texto[:inicio]
                cola = antes.rsplit("<label", 1)[-1]
                if "</label>" not in cola and cola.strip():
                    continue
                numero = texto[:inicio].count("\n") + 1
                avisos.append(
                    f"{fichero.relative_to(RAIZ)}:{numero} — <{etiqueta}> sin etiqueta"
                )
    return avisos


def bloqueantes_foco() -> list[str]:
    """`focus:outline-none` sin otra señal de foco = el teclado no ve dónde está.

    Es un bloqueante real: al navegar con el teclado, el usuario no sabe qué
    elemento está seleccionado.
    """
    problemas = []
    alternativas = ("focus:border-", "focus:ring-", "focus:bg-", "focus:text-", "focus:shadow-")
    for fichero in _ficheros():
        texto = fichero.read_text(encoding="utf-8", errors="replace")
        # Se recorren todas las etiquetas con foco propio.
        for etiqueta in ("input", "select", "textarea", "button", "a"):
            for atributos, _cuerpo, inicio in _elementos(texto, etiqueta):
                if "focus:outline-none" not in atributos:
                    continue
                if any(alternativa in atributos for alternativa in alternativas):
                    continue
                numero = texto[:inicio].count("\n") + 1
                problemas.append(
                    f"{fichero.relative_to(RAIZ)}:{numero} — <{etiqueta}> sin indicador de foco "
                    f"(focus:outline-none y nada más)"
                )
    return problemas


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass

    bloqueantes = (
        bloqueantes_boton()
        + bloqueantes_imagen()
        + bloqueantes_foco()
    )
    avisos = avisos_campo()

    for linea in bloqueantes:
        print(f"BLOQUEANTE  {linea}")
    for linea in avisos:
        print(f"AVISO       {linea}")

    print(
        f"\n{len(bloqueantes)} bloqueantes · {len(avisos)} avisos "
        f"(botones sin nombre accesible, imágenes sin alt, campos sin etiqueta)"
    )
    return 1 if bloqueantes else 0


if __name__ == "__main__":
    raise SystemExit(main())
