# -*- coding: utf-8 -*-
"""Normalizacion de requisitos al codigo canonico de la tabla ``concepto``.

La tabla ``concepto`` (migracion 009) mapea variantes de texto a codigos
canonicos. La migracion 010 relleno ``job_requirements.codigo_canonico`` como
backfill ONE-TIME: en ningun punto del codigo se rellenaba al INSERTAR, asi
que todo requisito nuevo queda en NULL y el Paso 5 lo descarta
(``matching`` filtra ``AND codigo_canonico IS NOT NULL``) -> la vacante se
evalua con 0 requisitos y cae en ``sin_requisitos``.

Este modulo cierra el hueco: resuelve el codigo AL GUARDAR el analisis y
encola las variantes sin concepto en ``concepto_no_normalizado`` para que la
taxonomia crezca con datos reales (la cola solo la llenaba la migracion 010).

Regla de resolucion (identica a la del backfill de la migracion 010):
``concepto.variante = LOWER(TRIM(value_code))`` y ``categoria = category``.
Solo se usan conceptos activos (``activa = 1``).
"""
from __future__ import annotations

import sqlite3
from typing import Any, Mapping, Sequence

# Categorias que la tabla `concepto` puede cubrir (CHECK de la migracion 009).
CATEGORIAS_CONCEPTO = ("skill", "language", "license", "education", "experience")

#: Categorias cuyo `value_code` del perfil es un CONCEPTO (una skill, un
#: idioma, una licencia, un nivel de estudio). Las demas (titulo de puesto,
#: area, contacto) NO son conceptos: encolarlas ensuciaria la taxonomia.
CATEGORIAS_PERFIL_CONCEPTO = ("skill", "language", "license", "education")


def _variante(value_code: str | None) -> str:
    return (value_code or "").strip().lower()


def _variantes_alternas(variante: str) -> tuple[str, ...]:
    """Variantes equivalentes a la dada (para tolerar slugs).

    El importador de CV produce SLUGS ('active-directory', 'excel-avanzado')
    y la taxonomia esta escrita en texto natural ('active directory'). Son la
    MISMA variante: se prueban las dos formas (y la de guiones bajos).
    """
    if not variante:
        return ()
    alternas: list[str] = []
    con_espacios = variante.replace("-", " ").replace("_", " ").strip()
    if con_espacios and con_espacios != variante:
        alternas.append(con_espacios)
    con_guiones = variante.replace(" ", "-").replace("_", "-").strip()
    if con_guiones and con_guiones != variante:
        alternas.append(con_guiones)
    return tuple(alternas)


def _mapa_conceptos(connection: sqlite3.Connection) -> dict[tuple[str, str], str]:
    """Carga ``(categoria, variante) -> codigo_canonico`` de los conceptos activos."""
    try:
        rows = connection.execute(
            """
            SELECT categoria, variante, codigo_canonico
            FROM concepto
            WHERE activa = 1
            """
        ).fetchall()
    except sqlite3.OperationalError:
        # Sin la tabla `concepto` (esquema viejo o BD minima en tests):
        # se deja el requisito sin codigo, igual que hacia la migracion 010.
        return {}
    return {
        (row[0], row[1]): row[2]
        for row in rows
    }


def resolver(
    connection: sqlite3.Connection,
    requirements: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """Resuelve el codigo canonico de cada requisito.

    Devuelve ``(requisitos, sin_concepto)``:
    - requisitos: copias con la clave ``codigo_canonico`` (``None`` si no hay
      concepto para esa variante);
    - sin_concepto: pares ``(categoria, variante)`` que no tienen concepto y
      deben encolarse en ``concepto_no_normalizado``.
    """
    mapa = _mapa_conceptos(connection)
    resueltos: list[dict[str, Any]] = []
    sin_concepto: list[tuple[str, str]] = []
    vistas: set[tuple[str, str]] = set()
    for requirement in requirements:
        copia = dict(requirement)
        category = copia.get("category")
        variante = _variante(copia.get("value_code"))
        codigo = None
        if category in CATEGORIAS_CONCEPTO and variante:
            codigo = mapa.get((category, variante))
            if codigo is None:
                # Slug del CV ('active-directory') vs texto de la taxonomia
                # ('active directory'): son la misma variante.
                for alterna in _variantes_alternas(variante):
                    codigo = mapa.get((category, alterna))
                    if codigo is not None:
                        break
        copia["codigo_canonico"] = codigo
        resueltos.append(copia)
        if codigo is None and category in CATEGORIAS_CONCEPTO and variante:
            clave = (category, variante)
            if clave not in vistas:
                vistas.add(clave)
                sin_concepto.append(clave)
    return resueltos, sin_concepto


def encolar_sin_concepto(
    connection: sqlite3.Connection,
    sin_concepto: Sequence[tuple[str, str]],
    *,
    origen: str = "oferta",
) -> None:
    """Suma las variantes sin concepto a la cola ``concepto_no_normalizado``.

    `origen`: 'oferta' (requisito del aviso), 'cv' (hecho del perfil) o
    'ambos'. La cola usa la variante como texto.
    """
    if origen not in ("oferta", "cv", "ambos"):
        raise ValueError("origen debe ser 'oferta', 'cv' o 'ambos'.")
    for category, variante in sin_concepto:
        connection.execute(
            """
            INSERT INTO concepto_no_normalizado (categoria, texto, origen, veces)
            VALUES (?, ?, ?, 1)
            ON CONFLICT (categoria, texto, origen)
            DO UPDATE SET veces = veces + 1
            """,
            (category, variante, origen),
        )
