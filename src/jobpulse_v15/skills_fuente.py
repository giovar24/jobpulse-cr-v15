# -*- coding: utf-8 -*-
"""Requisitos del aviso que vienen de sus CAMPOS ESTRUCTURADOS.

Por que existe: el extractor por reglas (``analysis.RuleBasedExtractor``) solo
lee el TEXTO y reconoce una lista corta de skills. El corpus, en cambio,
trae las skills y los idiomas del aviso en campos estructurados:

* ``jobs.skills``   -> lista de competencias que declara la fuente.
* ``jobs.languages``-> ``{"ingles": "B2"}``: los idiomas que el aviso PIDE y
  con que nivel (los tableros los dan; el pase de IA los extrae del texto).

Sin usar esos campos, **135 de 535 avisos quedan sin NINGUN requisito
comparable**: el motor no puede decir si el perfil califica (banda
``sin_datos``). El dato existia; el sistema no lo usaba.

REGLAS DURAS (mismas que el resto del repo):

1. **Solo lo que resuelve a un concepto canonico.** Si la skill de la fuente
   no esta en la taxonomia (``concepto``), NO se inventa un codigo: se encola
   en ``concepto_no_normalizado`` para que la taxonomia crezca con datos
   reales.
2. **Las frases de tarea no son competencias.** ``jobs.skills`` mezcla
   herramientas ("ServiceNow") con tareas ("apertura de caja", "soporte a
   equipos Dell"). Se descarta lo que sea tarea (mismo criterio que el
   ranking ATS, ``ats.es_frase_de_tarea``): contarlas como competencia
   penaliza a todos los avisos por igual y esconde los gaps reales.
3. **El nivel del requisito es ``inferred``**: el campo estructurado dice QUE
   pide el aviso, no si es obligatorio o deseable. No se inventa obligatoriedad.
4. **La evidencia es literal**: la etiqueta que trae el campo.
5. **No se duplica**: si el texto del aviso ya dio ese requisito (mismo codigo
   canonico), el de la fuente se descarta (contarlo dos veces infla el
   denominador y falsea el score).
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

from jobpulse_v15 import ats, conceptos, idiomas

#: Orden en que se busca la categoria de una etiqueta de la fuente. Un mismo
#: texto puede existir en varias categorias; el idioma gana porque su regla de
#: negocio es distinta, y la licencia antes que la skill.
ORDEN_CATEGORIAS = ("language", "license", "skill")

#: "Licencia B3", "licencia de conducir B3", "licencia para equipo especial D3"
_LICENCIA = re.compile(
    r"licencia\s+(?:de\s+conducir|para\s+conducir)?\s*"
    r"(?:para\s+[a-z]+\s+(?:especial\s+)?)?([a-d]\d?)\b",
    re.IGNORECASE,
)


def _sin_acentos(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in plano if not unicodedata.combining(c)).lower()


def _normalizar(texto: str) -> str:
    """Clave de busqueda en la taxonomia: minusculas, sin acentos, sin ruido.

    Se usa la MISMA normalizacion que el filtro de frases de tarea
    (``ats._normalize_skill``): asi "CI/CD", "TCP/IP" y "GMP's" se comparan
    igual que en el ranking ATS ("ci cd", "tcp ip", "gmp s").
    """
    return " ".join(ats._normalize_skill(str(texto or "")).split())


def parsear_skills(texto: Any) -> list[str]:
    """Lista de skills de ``jobs.skills``.

    Acepta el formato real (JSON array) y, por tolerancia, texto plano o
    lista separada por comas (datos viejos de otros tableros).
    """
    if texto is None:
        return []
    if isinstance(texto, (list, tuple)):
        items: Iterable[Any] = texto
    else:
        crudo = str(texto).strip()
        if not crudo or crudo in {"null", "[]", "{}"}:
            return []
        try:
            datos = json.loads(crudo)
        except (TypeError, ValueError):
            datos = [p.strip() for p in crudo.split(",")]
        if isinstance(datos, dict):
            datos = list(datos)
        if not isinstance(datos, (list, tuple)):
            datos = [datos]
        items = datos
    salida: list[str] = []
    vistos: set[str] = set()
    for item in items:
        etiqueta = str(item or "").strip()
        if not etiqueta:
            continue
        clave = _normalizar(etiqueta)
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append(etiqueta)
    return salida


def parsear_languages(texto: Any) -> dict[str, str]:
    """Diccionario ``{idioma: nivel}`` de ``jobs.languages``.

    Acepta el formato real (JSON object) y, por tolerancia, pares separados
    por ";" o ",".
    """
    if texto is None:
        return {}
    if isinstance(texto, Mapping):
        return {str(k): str(v) for k, v in texto.items()}
    crudo = str(texto).strip()
    if not crudo or crudo in {"null", "{}", "[]"}:
        return {}
    try:
        datos = json.loads(crudo)
    except (TypeError, ValueError):
        datos = {}
        for parte in re.split(r"[;,]", crudo):
            if ":" in parte:
                nombre, nivel = parte.split(":", 1)
                datos[nombre.strip()] = nivel.strip()
    if not isinstance(datos, dict):
        return {}
    return {str(k): str(v) for k, v in datos.items() if str(k).strip()}


def _mapa_normalizado(
    connection: sqlite3.Connection,
) -> dict[tuple[str, str], tuple[str, str]]:
    """Mapa ``(categoria, variante normalizada) -> (codigo, variante cruda)``.

    Se guarda la variante CRUDA de la taxonomia porque es la que se emite
    como ``value_code``: el resolutor de ``conceptos`` busca
    ``LOWER(TRIM(value_code))`` contra la variante tal cual esta en la base.
    Si se emitiera la etiqueta normalizada ("driver s license"), el
    resolutor no encontraria "driver's license" y el requisito quedaria SIN
    codigo canonico (invisible para el motor).
    """
    mapa: dict[tuple[str, str], tuple[str, str]] = {}
    for (categoria, variante), codigo in conceptos.mapa_conceptos(connection).items():
        clave = _normalizar(variante)
        if not clave:
            continue
        mapa.setdefault((categoria, clave), (codigo, variante.strip().lower()))
    return mapa


def _codigo_de_clase_licencia(etiqueta: str) -> str | None:
    """Clase de licencia de una etiqueta ("Licencia B3" -> "b3")."""
    match = _LICENCIA.search(_sin_acentos(etiqueta))
    if not match:
        return None
    return match.group(1).lower()


def clasificar(
    connection: sqlite3.Connection,
    etiqueta: str,
    mapa: Mapping[tuple[str, str], tuple[str, str]] | None = None,
) -> tuple[str, str, str] | None:
    """Clasifica una etiqueta de la fuente: ``(categoria, variante, codigo)``.

    ``None`` si no resuelve a un concepto de la taxonomia.
    """
    if mapa is None:
        mapa = _mapa_normalizado(connection)
    clave = _normalizar(etiqueta)
    if not clave:
        return None
    for categoria in ORDEN_CATEGORIAS:
        encontrado = mapa.get((categoria, clave))
        if encontrado:
            codigo, variante = encontrado
            return categoria, variante, codigo
    # "Licencia B3": la clase va como codigo ("b3"), no como etiqueta.
    clase = _codigo_de_clase_licencia(etiqueta)
    if clase:
        encontrado = mapa.get(("license", clase))
        if encontrado:
            codigo, variante = encontrado
            return "license", variante, codigo
    return None


def requisitos_de_fuente(
    connection: sqlite3.Connection,
    *,
    skills: Any = None,
    languages: Any = None,
    ya_cubiertos: Iterable[str] = (),
    posting_language: str | None = None,
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """Requisitos comparables que traen los campos estructurados del aviso.

    Devuelve ``(requisitos, sin_concepto)``:

    * ``requisitos``: dicts listos para ``Repository.save_analysis``
      (``origin='source_field'``, ``requirement_level='inferred'``).
    * ``sin_concepto``: pares ``(categoria, variante)`` que no resuelven y
      hay que encolar en ``concepto_no_normalizado``.

    `ya_cubiertos`: codigos canonicos que el TEXTO del aviso ya dio (no se
    duplican). `posting_language`: idioma del aviso (solo informativo; la
    regla de idioma la aplica el matching).
    """
    mapa = _mapa_normalizado(connection)
    cubiertos = set(ya_cubiertos)
    requisitos: list[dict[str, Any]] = []
    sin_concepto: list[tuple[str, str]] = []

    # -- IDIOMAS: el aviso PIDE estos idiomas, con este nivel --------------
    for nombre, nivel in parsear_languages(languages).items():
        variante = idiomas.nombre_idioma_a_variante(nombre)
        if variante is None:
            sin_concepto.append(("language", _normalizar(nombre)))
            continue
        encontrado = mapa.get(("language", _normalizar(variante)))
        if encontrado is None:
            sin_concepto.append(("language", variante))
            continue
        codigo, valor = encontrado
        if codigo in cubiertos:
            continue
        cubiertos.add(codigo)
        nivel_normalizado = idiomas.normalizar_nivel(nivel)
        evidencia = f"{nombre} {nivel}".strip()
        requisitos.append(
            {
                "category": "language",
                "value_code": valor,
                "value_text": nombre,
                "qualifier": nivel_normalizado,
                "requirement_level": "inferred",
                "evidence": evidencia,
                "origin": "source_field",
                "confidence": None,
            }
        )

    # -- SKILLS: competencias que declara la fuente ------------------------
    for etiqueta in parsear_skills(skills):
        if ats.es_frase_de_tarea(etiqueta):
            continue
        resolucion = clasificar(connection, etiqueta, mapa)
        if resolucion is None:
            sin_concepto.append(("skill", _normalizar(etiqueta)))
            continue
        categoria, variante, codigo = resolucion
        if codigo in cubiertos:
            continue
        cubiertos.add(codigo)
        requisitos.append(
            {
                "category": categoria,
                "value_code": variante,
                "value_text": etiqueta,
                "qualifier": None,
                "requirement_level": "inferred",
                "evidence": etiqueta,
                "origin": "source_field",
                "confidence": None,
            }
        )

    return requisitos, sin_concepto
