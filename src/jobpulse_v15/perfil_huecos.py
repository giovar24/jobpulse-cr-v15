# -*- coding: utf-8 -*-
"""Huecos del perfil: lo que el corpus pide y el perfil no registra (SIN Tk).

Implementación **única** de la detección de huecos. La usan la pestaña
**Perfil** de la UI v2 (:mod:`jobpulse_v15.ui_v2.data.profile`) y la
herramienta de verificación ``tools/perfil_preguntas.py``. No hay una segunda
copia: si cambia la regla, cambia **aquí**.

Principios
----------
- **Agnóstico del titular**: todo se deriva de la BD cargada (lo que el
  *corpus* pide vs. lo que el *perfil* registra). No asume nada sobre la
  persona; sirve para cualquier perfil y cambia solo si cambian los datos.
- **Determinista**: es una consulta, no lo redacta la IA sesión a sesión.
- **Solo lectura**: no escribe nada (ni siquiera encola conceptos).
- **Relleno una sola vez**: se recalcula en cada llamada, así que lo que ya
  quedó registrado deja de aparecer como hueco (idempotente).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Mapping

# Categorías que el motor del Paso 5 lee (matching.py): sin `codigo_canonico`
# las ignora en silencio. Las demás no generan hueco porque no las evalúa.
MOTOR_CATEGORIAS: tuple[str, ...] = ("skill", "language", "education", "license")

# Categorías "cerradas": el titular elige entre las variantes de la taxonomía
# (educación = escalera; licencia = tipo de licencia), no escribe libre.
CATEGORIAS_CERRADAS: frozenset[str] = frozenset({"education", "license"})


@dataclass(frozen=True)
class Hueco:
    """Un código que el corpus exige y el perfil no registra."""

    categoria: str
    codigo: str
    avisos: int
    niveles: tuple[str, ...] = ()
    calificadores: tuple[str, ...] = ()

    @property
    def clave(self) -> str:
        return f"{self.categoria}:{self.codigo}"


@dataclass(frozen=True)
class Opcion:
    """Variante de la taxonomía para una categoría cerrada."""

    categoria: str
    codigo: str


@dataclass(frozen=True)
class HuecoSinCanonico:
    """Hecho de categoría motor guardado SIN código: el motor lo ignora."""

    categoria: str
    value_code: str
    value_text: str


@dataclass(frozen=True)
class HuecosPerfil:
    """Resultado completo del cálculo de huecos."""

    faltan: tuple[Hueco, ...] = ()
    opciones: tuple[Opcion, ...] = ()
    areas_catalogo: tuple[tuple[str, str], ...] = ()
    areas_marcadas: tuple[str, ...] = ()
    sin_canonico: tuple[HuecoSinCanonico, ...] = ()
    avisos_evaluables: int = 0
    avisos_con_perfil: int = 0

    @property
    def total(self) -> int:
        """Huecos de categorías motor (sin contar áreas)."""
        return len(self.faltan)

    @property
    def vacios(self) -> bool:
        """¿No queda nada por registrar?"""
        return not self.faltan and not self.sin_canonico and bool(self.areas_marcadas)

    def por_categoria(self) -> Mapping[str, tuple[Hueco, ...]]:
        """Huecos agrupados por categoría, en el orden de ``MOTOR_CATEGORIAS``."""
        agrupado: dict[str, list[Hueco]] = {c: [] for c in MOTOR_CATEGORIAS}
        for hueco in self.faltan:
            agrupado.setdefault(hueco.categoria, []).append(hueco)
        return {c: tuple(v) for c, v in agrupado.items() if v}

    def resumen_linea(self) -> str:
        """Una línea tipo ``skill 272 · language 3 · education 1``."""
        partes = [
            f"{categoria} {len(huecos)}"
            for categoria, huecos in self.por_categoria().items()
        ]
        if not partes:
            return "sin huecos de categorías motor"
        return " · ".join(partes)


# ---------------------------------------------------------------------
# consultas
# ---------------------------------------------------------------------
def _requisitos_corpus(
    con: sqlite3.Connection, categoria: str
) -> list[tuple[str, int, str | None, str | None]]:
    """``(codigo, n_avisos, niveles, calificadores)`` evaluables del corpus.

    Solo lo que el motor puede evaluar: `codigo_canonico` presente y nivel
    distinto de `preferred` (preferred no bloquea ni entra al denominador).
    """
    return con.execute(
        """
        SELECT r.codigo_canonico,
               COUNT(DISTINCT a.job_id) AS n,
               GROUP_CONCAT(DISTINCT r.requirement_level),
               GROUP_CONCAT(DISTINCT COALESCE(r.qualifier, ''))
        FROM job_requirements r
        JOIN job_analysis a ON a.analysis_id = r.analysis_id
        WHERE a.is_current = 1
          AND r.category = ?
          AND r.requirement_level != 'preferred'
          AND r.codigo_canonico IS NOT NULL
        GROUP BY r.codigo_canonico
        ORDER BY n DESC, r.codigo_canonico
        """,
        (categoria,),
    ).fetchall()


def _perfil_codigos(con: sqlite3.Connection, categoria: str) -> set[str]:
    return {
        fila[0]
        for fila in con.execute(
            "SELECT DISTINCT codigo_canonico FROM candidate_profile_facts "
            "WHERE category = ? AND codigo_canonico IS NOT NULL",
            (categoria,),
        )
    }


def _variantes(con: sqlite3.Connection, categoria: str) -> tuple[str, ...]:
    """Variantes de la taxonomía (para redactar la pregunta cerrada)."""
    return tuple(
        fila[0]
        for fila in con.execute(
            "SELECT DISTINCT variante FROM concepto "
            "WHERE categoria = ? AND activa = 1 ORDER BY variante",
            (categoria,),
        )
    )


def _partir(texto: str | None) -> tuple[str, ...]:
    return tuple(sorted(x for x in (texto or "").split(",") if x))


# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------
def calcular_huecos(con: sqlite3.Connection) -> HuecosPerfil:
    """Calcula los huecos del perfil contra el corpus de esa BD.

    ``con`` puede abrirse en modo lectura (``file:...?mode=ro``): esta
    función **nunca escribe**.
    """
    faltan: list[Hueco] = []
    opciones: list[Opcion] = []

    for categoria in MOTOR_CATEGORIAS:
        perfil = _perfil_codigos(con, categoria)
        for codigo, avisos, niveles, calificadores in _requisitos_corpus(
            con, categoria
        ):
            if codigo in perfil:
                continue
            faltan.append(
                Hueco(
                    categoria=categoria,
                    codigo=codigo,
                    avisos=int(avisos),
                    niveles=_partir(niveles),
                    calificadores=_partir(calificadores),
                )
            )
        if categoria in CATEGORIAS_CERRADAS:
            opciones.extend(
                Opcion(categoria=categoria, codigo=v)
                for v in _variantes(con, categoria)
            )

    areas_marcadas = tuple(
        fila[0]
        for fila in con.execute(
            "SELECT value_code FROM candidate_profile_facts "
            "WHERE category = 'area' ORDER BY value_code"
        )
    )
    areas_catalogo = tuple(
        (fila[0], fila[1])
        for fila in con.execute(
            "SELECT codigo, nombre FROM area WHERE activa = 1 "
            "ORDER BY orden, codigo"
        )
    )

    sin_canonico = tuple(
        HuecoSinCanonico(
            categoria=fila[0],
            value_code=fila[1] or "",
            value_text=fila[2] or "",
        )
        for fila in con.execute(
            """
            SELECT category, value_code, value_text
            FROM candidate_profile_facts
            WHERE category IN ('skill','language','education','license')
              AND codigo_canonico IS NULL
            ORDER BY category, value_code
            """
        )
    )

    avisos_evaluables = con.execute(
        """
        SELECT COUNT(DISTINCT a.job_id)
        FROM job_requirements r
        JOIN job_analysis a ON a.analysis_id = r.analysis_id
        WHERE a.is_current = 1
          AND r.category IN ('skill','language','education','license')
          AND r.requirement_level != 'preferred'
          AND r.codigo_canonico IS NOT NULL
        """
    ).fetchone()[0]

    avisos_con_perfil = con.execute(
        "SELECT COUNT(*) FROM candidate_profile_facts"
    ).fetchone()[0]

    return HuecosPerfil(
        faltan=tuple(faltan),
        opciones=tuple(opciones),
        areas_catalogo=areas_catalogo,
        areas_marcadas=areas_marcadas,
        sin_canonico=sin_canonico,
        avisos_evaluables=int(avisos_evaluables or 0),
        avisos_con_perfil=int(avisos_con_perfil or 0),
    )
