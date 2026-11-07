# -*- coding: utf-8 -*-
"""Metricas por etapa del pipeline (Ola 4.3).

Por que existe: el pipeline encadena siete etapas y cada una devuelve
contadores propios, en formatos distintos. Al terminar, la pregunta que de
verdad importa ("por que esta corrida dio menos") no se puede responder:
¿cuantos avisos entraron?, ¿cuantos llegaron al Paso 5?, ¿cuantos tenian
requisitos?, ¿en que etapa se perdieron?

Este modulo convierte el resultado de cada etapa en tres numeros
COMPARABLES y los guarda en la tabla `pipeline_etapa` (migracion 024):

============  ==========================  ==========================  ==================
etapa         `avisos`                   `requisitos`               `errores`
============  ==========================  ==========================  ==================
scrape        encontrados en la fuente   0 (no produce requisitos)  sitios con error
analisis      analizados                 requisitos guardados       analyses fallidos
ia            avisos enriquecidos        0 (no produce requisitos)  avisos fallidos
reanalisis    re-analizados              requisitos de la fuente    avisos con error
backfill      0 (no toca avisos)         requisitos con codigo      0
paso5         evaluados                  requisitos EVALUADOS       0
evidencia     avisos documentados        0                          discrepancias
============  ==========================  ==========================  ==================

Ademas guarda un `detalle_json` con los contadores ESPECIFICOS de la etapa
(por estado del Paso 5, por campo rellenado por la IA, por sitio del
barrido...), que es lo que hace falta para auditar en detalle.

Reglas del proyecto que este modulo NO cambia:

* no borra ni funde datos: solo anade filas de auditoria;
* no toca `job_match`, `job_analysis` ni los umbrales del motor;
* si la BD no tiene la migracion 024Todavía, se aplican las migraciones
  pendientes (con la convencion del proyecto: "migrar al abrir") y se avisa;
* si algo falla al registrar, el pipeline SIGUE: una metrica nunca rompe una
  corrida.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from jobpulse_v15.db import Database

#: Prefijo de los identificadores de corrida del PIPELINE (distintos de los
#: de `job_match`, que son timestamps pelados como `20261106_182554`).
PREFIJO_CORRIDA = "pipe_"

#: Las etapas del pipeline, en el ORDEN en que se ejecutan. Vive aquí (y no
#: en `pipeline.py`) para que este módulo pueda recorrer un resultado en
#: memoria sin importar el orquestador (evita un ciclo de imports).
ETAPAS: tuple[str, ...] = (
    "scrape",
    "analisis",
    "ia",
    "reanalisis",
    "backfill",
    "paso5",
    "evidencia",
)


def _int(valor: Any) -> int:
    """Entero tolerante: `None`, `""` o un string raro son 0."""
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def nuevo_corrida_id(base: Database | None = None) -> str:
    """Identificador de la EJECUCION del pipeline (`pipe_<timestamp>`).

    Si dos pipelines arrancan en el MISMO segundo tienen que ser dos
    corridas distintas (igual que en `matching._nuevo_corrida_id`), asi que
    se anade un sufijo si el identificador ya existe.
    """
    base_id = PREFIJO_CORRIDA + datetime.now().strftime("%Y%m%d_%H%M%S")
    if base is None:
        return base_id
    try:
        with base.connection() as connection:
            if not _existe_corrida(connection, base_id):
                return base_id
            for sufijo in range(1, 1000):
                candidata = "%s_%02d" % (base_id, sufijo)
                if not _existe_corrida(connection, candidata):
                    return candidata
    except sqlite3.Error:
        pass
    return "%s_%s" % (base_id, datetime.now().microsecond)


def _existe_corrida(connection: sqlite3.Connection, corrida_id: str) -> bool:
    fila = connection.execute(
        "SELECT 1 FROM pipeline_etapa WHERE corrida_id = ? LIMIT 1",
        (corrida_id,),
    ).fetchone()
    return fila is not None


def asegurar_esquema(base: Database, log=None) -> int:
    """Aplica las migraciones pendientes y AVISA si el esquema cambio.

    Devuelve la version resultante del esquema. La migracion 024 (tabla
    `pipeline_etapa`) se aplica aqui con la convencion del proyecto: "el
    esquema se migra al abrir la base".
    """
    antes = base.schema_version()
    despues = base.initialize()
    if despues != antes and log is not None:
        log(
            "[esquema] Se aplicaron las migraciones %d-%d."
            % (antes + 1, despues)
        )
    return despues


def contadores_etapa(nombre: str, resultado: Mapping[str, Any]) -> dict[str, int]:
    """Traduce el resultado de una etapa a los tres numeros comparables.

    Devuelve ``{"avisos": n, "requisitos": n, "errores": n}``. Una etapa
    desconocida (o un resultado vacio) da ceros: la metrica nunca inventa.
    """
    r: Mapping[str, Any] = resultado or {}
    if nombre == "scrape":
        return {
            "avisos": _int(r.get("jobs_found")),
            "requisitos": 0,
            "errores": _int(r.get("errores")),
        }
    if nombre == "analisis":
        return {
            "avisos": _int(r.get("analizados")),
            "requisitos": _int(r.get("requisitos_guardados")),
            "errores": _int(r.get("fallos")),
        }
    if nombre == "ia":
        stats = r.get("stats_ia") or {}
        ciclos = list(stats.get("ciclos") or [])
        completo = stats.get("completo") or {}
        enriquecidos = sum(_int(c.get("enriched")) for c in ciclos) + _int(
            completo.get("enriched")
        )
        # OJO: `failed` en el pase IA NO es un error de red: cuenta "el
        # modelo no encontró el campo" ("no mencionado"). Los errores REALES
        # vienen en `stats_ia["error"]` (y se loguean como "IA extract
        # {campo} fallo tras 3 intentos"). Contar `failed` como errores
        # inflaría la auditoría con lo que es, sencillamente, "el aviso no
        # lo dice".
        errores = 1 if stats.get("error") else 0
        return {"avisos": enriquecidos, "requisitos": 0, "errores": errores}
    if nombre == "reanalisis":
        return {
            "avisos": _int(r.get("reanalizados")) + _int(r.get("texto_reanalizados")),
            "requisitos": _int(r.get("requisitos_fuente")),
            "errores": _int(r.get("errores")) + _int(r.get("texto_errores")),
        }
    if nombre == "backfill":
        return {
            "avisos": 0,
            "requisitos": _int(r.get("actualizados")),
            "errores": 0,
        }
    if nombre == "paso5":
        return {
            "avisos": _int(r.get("evaluadas")),
            "requisitos": _int(r.get("requisitos_evaluados")),
            "errores": 0,
        }
    if nombre == "evidencia":
        fallos = r.get("fallos")
        n_fallos = len(fallos) if isinstance(fallos, (list, tuple)) else _int(fallos)
        documentados = r.get("documentados")
        if documentados is None:
            documentados = _int(r.get("descartadas")) + _int(r.get("no_confirmadas"))
        return {
            "avisos": _int(documentados),
            "requisitos": 0,
            "errores": n_fallos,
        }
    return {"avisos": 0, "requisitos": 0, "errores": 0}


def detalle_etapa(nombre: str, resultado: Mapping[str, Any]) -> dict[str, Any]:
    """Contadores ESPECIFICOS de la etapa (lo que hace falta para auditar)."""
    r: Mapping[str, Any] = resultado or {}
    if nombre == "scrape":
        detalle = {
            "sitios": _int(r.get("sitios")),
            "sitios_ok": _int(r.get("sitios_ok")),
            "jobs_found": _int(r.get("jobs_found")),
            "jobs_new": _int(r.get("jobs_new")),
            "jobs_duplicate": _int(r.get("jobs_duplicate")),
            "jobs_skipped": _int(r.get("jobs_skipped")),
            "cancelado": bool(r.get("cancelado")),
        }
        por_sitio = r.get("por_sitio")
        if isinstance(por_sitio, (list, tuple)):
            detalle["por_sitio"] = [
                {
                    "site_id": s.get("site_id"),
                    "estado": s.get("estado"),
                    "jobs_found": _int(s.get("jobs_found")),
                    "jobs_new": _int(s.get("jobs_new")),
                }
                for s in por_sitio
                if isinstance(s, Mapping)
            ]
        return detalle
    if nombre == "analisis":
        return {
            "pendientes": _int(r.get("pendientes")),
            "analizados": _int(r.get("analizados")),
            "fallos": _int(r.get("fallos")),
            "requisitos_guardados": _int(r.get("requisitos_guardados")),
        }
    if nombre == "ia":
        stats = r.get("stats_ia") or {}
        ciclos = list(stats.get("ciclos") or [])
        completo = stats.get("completo") or {}
        avance = r.get("avance") or {}
        return {
            "estado": r.get("estado"),
            "motivo": r.get("motivo"),
            "enriquecidos": sum(_int(c.get("enriched")) for c in ciclos)
            + _int(completo.get("enriched")),
            # "no_encontrado" = el modelo NO halló el campo en el texto
            # (NO es un error); "sin_cambio" = lo devolvió, pero ya estaba.
            "no_encontrado": sum(_int(c.get("failed")) for c in ciclos)
            + _int(completo.get("failed")),
            "sin_cambio": sum(_int(c.get("skipped")) for c in ciclos)
            + _int(completo.get("skipped")),
            "total": sum(_int(c.get("total")) for c in ciclos)
            + _int(completo.get("total")),
            "campos_llenados": _int(avance.get("campos_llenados")),
            "por_campo": avance.get("por_campo") or {},
        }
    if nombre == "reanalisis":
        return {
            "candidatos": _int(r.get("candidatos")),
            "reanalizados": _int(r.get("reanalizados")),
            "sin_cambio": _int(r.get("sin_cambio")),
            "requisitos_fuente": _int(r.get("requisitos_fuente")),
            "texto_candidatos": _int(r.get("texto_candidatos")),
            "texto_reanalizados": _int(r.get("texto_reanalizados")),
            "texto_errores": _int(r.get("texto_errores")),
        }
    if nombre == "backfill":
        return {
            "sin_codigo": _int(r.get("sin_codigo")),
            "actualizados": _int(r.get("actualizados")),
            "revisados": _int(r.get("revisados")),
            "sin_concepto": _int(r.get("sin_concepto")),
        }
    if nombre == "paso5":
        return {
            "corrida": r.get("corrida"),
            "evaluadas": _int(r.get("evaluadas")),
            "requisitos_evaluados": _int(r.get("requisitos_evaluados")),
            "por_estado": r.get("por_estado") or {},
            "por_motivo": r.get("por_motivo") or {},
        }
    if nombre == "evidencia":
        fallos = r.get("fallos")
        return {
            "corrida": r.get("corrida"),
            "documento": r.get("documento"),
            "documentados": _int(r.get("documentados")),
            "descartadas": _int(r.get("descartadas")),
            "no_confirmadas": _int(r.get("no_confirmadas")),
            "verificaciones": _int(r.get("verificaciones")),
            "fallos": len(fallos) if isinstance(fallos, (list, tuple)) else _int(fallos),
        }
    return {}


def registrar_etapa(
    base: Database,
    *,
    corrida_id: str,
    etapa: str,
    ok: bool,
    duracion_ms: int,
    resultado: Mapping[str, Any],
    iniciado_en: datetime,
    terminado_en: datetime,
    error: str | None = None,
) -> dict[str, int]:
    """Guarda la metrica de UNA etapa en `pipeline_etapa`.

    Devuelve los contadores que se guardaron (``avisos``, ``requisitos``,
    ``errores``). Si la escritura falla, la excepcion sube: el orquestador
    decide si continuar (una metrica no puede romper una corrida).
    """
    contadores = contadores_etapa(etapa, resultado)
    detalle = detalle_etapa(etapa, resultado)
    if error is None:
        # El error suele venir DENTRO del resultado de la etapa (la que
        # reventó): si no, el detalle perdía la causa del fallo.
        error = resultado.get("error")
    if error:
        detalle = dict(detalle)
        detalle["error"] = error
    with base.connection() as connection:
        connection.execute(
            """
            INSERT INTO pipeline_etapa (
                corrida_id, etapa, ok, duracion_ms, avisos, requisitos,
                errores, detalle_json, iniciado_en, terminado_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                corrida_id,
                etapa,
                1 if ok else 0,
                max(0, int(duracion_ms)),
                contadores["avisos"],
                contadores["requisitos"],
                contadores["errores"],
                json.dumps(detalle, ensure_ascii=False, default=str),
                iniciado_en.isoformat(timespec="seconds"),
                terminado_en.isoformat(timespec="seconds"),
            ),
        )
    return contadores


def consultar_corridas(
    connection: sqlite3.Connection, limite: int = 10
) -> list[dict[str, Any]]:
    """Ultimas corridas del pipeline con el desglose de sus etapas."""
    filas = connection.execute(
        """
        SELECT corrida_id, MAX(id) AS ultimo
        FROM pipeline_etapa
        GROUP BY corrida_id
        ORDER BY ultimo DESC
        LIMIT ?
        """,
        (max(1, int(limite)),),
    ).fetchall()
    corridas = []
    for fila in filas:
        corrida = consultar_corrida(connection, str(fila["corrida_id"]))
        if corrida:
            corridas.append(corrida)
    return corridas


def consultar_corrida(
    connection: sqlite3.Connection, corrida_id: str
) -> dict[str, Any] | None:
    """Una corrida del pipeline con todas sus etapas (en orden)."""
    filas = connection.execute(
        """
        SELECT etapa, ok, duracion_ms, avisos, requisitos, errores,
               detalle_json, iniciado_en, terminado_en
        FROM pipeline_etapa
        WHERE corrida_id = ?
        ORDER BY id
        """,
        (corrida_id,),
    ).fetchall()
    if not filas:
        return None
    etapas = []
    for fila in filas:
        try:
            detalle = json.loads(fila["detalle_json"] or "{}")
        except (TypeError, ValueError):
            detalle = {}
        etapas.append(
            {
                "etapa": fila["etapa"],
                "ok": bool(fila["ok"]),
                "duracion_ms": int(fila["duracion_ms"]),
                "avisos": int(fila["avisos"]),
                "requisitos": int(fila["requisitos"]),
                "errores": int(fila["errores"]),
                "detalle": detalle,
                "iniciado_en": fila["iniciado_en"],
                "terminado_en": fila["terminado_en"],
            }
        )
    return {
        "corrida_id": corrida_id,
        "etapas": etapas,
        "duracion_ms": sum(e["duracion_ms"] for e in etapas),
        "avisos": sum(e["avisos"] for e in etapas),
        "requisitos": sum(e["requisitos"] for e in etapas),
        "errores": sum(e["errores"] for e in etapas),
        "ok": all(e["ok"] for e in etapas),
    }


def resumen_linea(corrida: Mapping[str, Any]) -> str:
    """Una linea legible de una corrida con sus etapas."""
    partes = []
    for etapa in corrida.get("etapas", []):
        partes.append(
            "%s=%s(%dms,%dav,%drq,%derr)"
            % (
                etapa["etapa"],
                "ok" if etapa["ok"] else "ERROR",
                etapa["duracion_ms"],
                etapa["avisos"],
                etapa["requisitos"],
                etapa["errores"],
            )
        )
    return "PIPELINE[%s]: %s" % (
        corrida.get("corrida_id", "?"),
        " · ".join(partes) if partes else "sin etapas",
    )


def resumen_linea_etapas(resultado: Mapping[str, Any]) -> str:
    """Una linea con los contadores por etapa de un resultado EN MEMORIA.

    La misma linea que deja la UI v2 y el envoltorio `run_full_flow.py`
    (una sola implementacion: si cada llamador compusiera su propia linea,
    los numeros podrian divergir).
    """
    etapas = resultado.get("etapas") or {}
    partes = []
    for nombre in ETAPAS:
        etapa = etapas.get(nombre)
        if not etapa:
            continue
        contadores = contadores_etapa(nombre, etapa)
        partes.append(
            "%s: %d av · %d rq · %d err"
            % (
                nombre,
                contadores["avisos"],
                contadores["requisitos"],
                contadores["errores"],
            )
        )
    if not partes:
        return ""
    return "MÉTRICAS: " + " · ".join(partes)


def base_de(ruta: str | Path) -> Database:
    """`Database` sobre una ruta (util para el CLI)."""
    return Database(ruta)
