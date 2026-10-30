# -*- coding: utf-8 -*-
"""Areas de empleo: taxonomia, clasificacion de ofertas y filtro del perfil.

Reglas del proyecto que este modulo respeta:

* La taxonomia y las reglas viven en la **BD** (``area`` / ``area_regla``), no
  en el codigo: se siembran desde ``seeds/areas.json`` (``init-areas``).
* El perfil declara sus areas como **hechos** en
  ``candidate_profile_facts`` con ``category='area'`` (la UI los marca o
  desmarca). Si el perfil no marca ninguna, NO hay filtro: se evalua todo.
* La clasificacion de una oferta usa **su titulo** (no la fuente): las mismas
  reglas aplican a Workday, ANE, Indeed, LinkedIn, Elempleo, Harvie, CINDE o
  Procomer. Si el titulo no encaja o encaja en varias areas a la vez, la
  oferta queda en el area ``otros`` y **se evalua igual** (una clasificacion
  dudosa nunca oculta ofertas).
* Nada se borra ni se funde: reclasificar reescribe SOLO la tabla
  ``job_area`` (derivada) y deja intactos los avisos.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# Area que agrupa lo que no encaja en ninguna otra (o encaja en varias).
AREA_OTROS = "otros"

SEED_PATH = Path(__file__).with_name("seeds") / "areas.json"

# Confianza de la clasificacion: la del titulo puede excluir una oferta de la
# evaluacion; la de la descripcion es solo informativa (en miles de
# caracteres cualquier palabra aparece por casualidad).
CONFIANZA_TITULO = "titulo"
CONFIANZA_DESCRIPCION = "descripcion"


@dataclass(frozen=True)
class ReglaArea:
    """Una regla de clasificacion (patron + area + prioridad)."""

    area_codigo: str
    patron: re.Pattern[str]
    prioridad: int
    fuente: str

    def coincide(self, texto: str) -> str | None:
        encontrada = self.patron.search(texto or "")
        return encontrada.group(0) if encontrada else None


@dataclass(frozen=True)
class Clasificacion:
    """Resultado de clasificar una oferta en un area."""

    area_codigo: str
    evidencia: str | None = None
    ambigua: bool = False
    candidatas: tuple[str, ...] = ()

    @property
    def es_otros(self) -> bool:
        return self.area_codigo == AREA_OTROS


# --------------------------------------------------------------------------
# Lectura de la configuracion (BD)
# --------------------------------------------------------------------------


def cargar_areas(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Areas activas del sistema, en el orden declarado."""
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT codigo, nombre, descripcion, orden, activa
            FROM area
            WHERE activa = 1
            ORDER BY orden, codigo
            """
        )
    ]


def areas_por_codigo(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    return {area["codigo"]: area for area in cargar_areas(connection)}


def cargar_reglas(connection: sqlite3.Connection) -> list[ReglaArea]:
    """Reglas activas, de la BD, compiladas."""
    reglas: list[ReglaArea] = []
    for fila in connection.execute(
        """
        SELECT area_codigo, patron, fuente, prioridad
        FROM area_regla
        WHERE activa = 1
        ORDER BY prioridad DESC, regla_id
        """
    ):
        try:
            patron = re.compile(fila["patron"], re.IGNORECASE)
        except re.error as exc:  # pragma: no cover - protege de semillas malas
            raise ValueError(
                f"Patron de area invalido para {fila['area_codigo']!r}: "
                f"{fila['patron']!r} ({exc})"
            ) from exc
        reglas.append(
            ReglaArea(
                area_codigo=fila["area_codigo"],
                patron=patron,
                prioridad=int(fila["prioridad"]),
                fuente=fila["fuente"],
            )
        )
    return reglas


# --------------------------------------------------------------------------
# Clasificacion
# --------------------------------------------------------------------------


def clasificar_texto(texto: str, reglas: Sequence[ReglaArea]) -> Clasificacion:
    """Clasifica un texto (el titulo de la oferta) en un area.

    Gana la regla de **mayor prioridad**; si dos areas distintas empatan en la
    mayor prioridad, la oferta es **ambigua** y queda en ``otros``.
    """
    coincidencias: list[tuple[int, str, str]] = []
    for regla in reglas:
        evidencia = regla.coincide(texto)
        if evidencia is not None:
            coincidencias.append((regla.prioridad, regla.area_codigo, evidencia))
    if not coincidencias:
        return Clasificacion(area_codigo=AREA_OTROS)
    mayor = max(prioridad for prioridad, _area, _evidencia in coincidencias)
    areas = sorted({area for prioridad, area, _evidencia in coincidencias if prioridad == mayor})
    if len(areas) > 1:
        return Clasificacion(
            area_codigo=AREA_OTROS,
            evidencia=None,
            ambigua=True,
            candidatas=tuple(areas),
        )
    evidencia = next(
        evidencia
        for prioridad, _area, evidencia in coincidencias
        if prioridad == mayor
    )
    return Clasificacion(area_codigo=areas[0], evidencia=evidencia)


def guardar_clasificacion(
    connection: sqlite3.Connection,
    job_id: str,
    clasificacion: Clasificacion,
    confianza: str = CONFIANZA_TITULO,
) -> None:
    """Guarda el area de UNA oferta (reemplaza la anterior, no la acumula)."""
    connection.execute("DELETE FROM job_area WHERE job_id = ?", (job_id,))
    connection.execute(
        """
        INSERT INTO job_area (job_id, area_codigo, confianza, evidencia)
        VALUES (?, ?, ?, ?)
        """,
        (
            job_id,
            clasificacion.area_codigo,
            confianza,
            clasificacion.evidencia,
        ),
    )


def clasificar_oferta(
    connection: sqlite3.Connection,
    job_id: str,
    reglas: Sequence[ReglaArea] | None = None,
) -> Clasificacion:
    """Clasifica una oferta por su TITULO y guarda el resultado."""
    fila = connection.execute(
        "SELECT title FROM jobs WHERE job_id = ?", (job_id,)
    ).fetchone()
    if fila is None:
        raise ValueError(f"No existe la vacante {job_id!r}.")
    if reglas is None:
        reglas = cargar_reglas(connection)
    clasificacion = clasificar_texto(fila["title"], reglas)
    guardar_clasificacion(connection, job_id, clasificacion)
    return clasificacion


def clasificar_todas(
    connection: sqlite3.Connection,
    reglas: Sequence[ReglaArea] | None = None,
) -> dict[str, int]:
    """Reclasifica TODAS las ofertas y devuelve el conteo por area."""
    if reglas is None:
        reglas = cargar_reglas(connection)
    connection.execute("DELETE FROM job_area")
    conteo: dict[str, int] = {}
    for fila in connection.execute("SELECT job_id, title FROM jobs"):
        clasificacion = clasificar_texto(fila["title"], reglas)
        connection.execute(
            """
            INSERT INTO job_area (job_id, area_codigo, confianza, evidencia)
            VALUES (?, ?, ?, ?)
            """,
            (
                fila["job_id"],
                clasificacion.area_codigo,
                CONFIANZA_TITULO,
                clasificacion.evidencia,
            ),
        )
        conteo[clasificacion.area_codigo] = conteo.get(clasificacion.area_codigo, 0) + 1
    connection.commit()
    return dict(sorted(conteo.items(), key=lambda item: (-item[1], item[0])))


def area_de_oferta(connection: sqlite3.Connection, job_id: str) -> str | None:
    """Area de una oferta (``None`` si nunca se clasifico)."""
    fila = connection.execute(
        "SELECT area_codigo FROM job_area WHERE job_id = ?", (job_id,)
    ).fetchone()
    return fila["area_codigo"] if fila else None


def areas_por_oferta(connection: sqlite3.Connection) -> dict[str, str]:
    """Mapa ``job_id -> area_codigo`` de todas las ofertas clasificadas."""
    return {
        fila["job_id"]: fila["area_codigo"]
        for fila in connection.execute("SELECT job_id, area_codigo FROM job_area")
    }


def conteo_por_area(connection: sqlite3.Connection) -> dict[str, int]:
    """Conteo de ofertas por area (incluye las no clasificadas)."""
    return {
        fila["area_codigo"]: int(fila["n"])
        for fila in connection.execute(
            "SELECT area_codigo, COUNT(*) n FROM job_area GROUP BY area_codigo"
        )
    }


# --------------------------------------------------------------------------
# Perfil: areas que el usuario marco
# --------------------------------------------------------------------------


def areas_del_perfil(connection: sqlite3.Connection) -> set[str]:
    """Areas marcadas por el usuario en el perfil (hechos category='area').

    Vacio = el usuario no marco ninguna area = se evalua TODO.
    """
    return {
        fila["value_code"]
        for fila in connection.execute(
            """
            SELECT value_code
            FROM candidate_profile_facts
            WHERE category = 'area'
            """
        )
        if str(fila["value_code"]).strip()
    }


def fact_de_area(area: Mapping[str, Any]) -> dict[str, Any]:
    """Construye el hecho de perfil que representa un area marcada.

    Solo lleva ``category``/``value_code``/``value_text``: el area se
    identifica por su codigo (el mismo de la tabla ``area``).
    """
    codigo = str(area["codigo"]).strip()
    return {
        "category": "area",
        "value_code": codigo,
        "value_text": str(area["nombre"]).strip() or codigo,
    }


def es_fuera_de_area(area_oferta: str | None, areas_perfil: Iterable[str]) -> bool:
    """``True`` si la oferta queda fuera de las areas marcadas por el perfil.

    Reglas conservadoras:

    * sin areas marcadas en el perfil -> no hay filtro (``False``);
    * oferta sin area clasificada -> no se excluye (``False``);
    * oferta en el area ``otros`` (ambigua o sin encaje) -> no se excluye
      (``False``): una clasificacion dudosa no puede tapar una oferta;
    * en cualquier otro caso -> fuera de area si su area no esta marcada.
    """
    marcadas = {str(codigo).strip() for codigo in areas_perfil if str(codigo).strip()}
    if not marcadas:
        return False
    if not area_oferta or area_oferta == AREA_OTROS:
        return False
    return area_oferta not in marcadas


# --------------------------------------------------------------------------
# Semilla (taxonomia + reglas)
# --------------------------------------------------------------------------


def leer_semilla(path: Path | str | None = None) -> dict[str, Any]:
    """Lee la semilla de areas (JSON versionado en el paquete)."""
    ruta = Path(path) if path is not None else SEED_PATH
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict) or "areas" not in datos or "reglas" not in datos:
        raise ValueError(f"Semilla de areas invalida: {ruta}")
    return datos


def sembrar_taxonomia(
    connection: sqlite3.Connection,
    path: Path | str | None = None,
) -> dict[str, int]:
    """Carga la semilla en ``area`` / ``area_regla`` (idempotente).

    No toca ``job_area``: la clasificacion se corre aparte (``areas
    classify``) para poder medir el cambio antes de aplicarlo.
    """
    datos = leer_semilla(path)
    areas = datos["areas"]
    reglas = datos["reglas"]
    codigos = {str(area["codigo"]) for area in areas}
    for regla in reglas:
        if str(regla["area"]) not in codigos:
            raise ValueError(
                f"La regla {regla['patron']!r} apunta a un area inexistente: "
                f"{regla['area']!r}"
            )
    for orden, area in enumerate(areas, start=1):
        connection.execute(
            """
            INSERT INTO area (codigo, nombre, descripcion, orden, activa)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(codigo) DO UPDATE SET
                nombre = excluded.nombre,
                descripcion = excluded.descripcion,
                orden = excluded.orden,
                activa = 1
            """,
            (
                str(area["codigo"]),
                str(area["nombre"]),
                str(area.get("descripcion") or ""),
                orden,
            ),
        )
    connection.execute("DELETE FROM area_regla")
    connection.executemany(
        """
        INSERT INTO area_regla (area_codigo, patron, fuente, prioridad, activa)
        VALUES (?, ?, ?, ?, 1)
        """,
        [
            (
                str(regla["area"]),
                str(regla["patron"]),
                str(regla.get("fuente") or "titulo"),
                int(regla.get("prioridad") or 0),
            )
            for regla in reglas
        ],
    )
    connection.commit()
    return {"areas": len(areas), "reglas": len(reglas)}
