# -*- coding: utf-8 -*-
"""Analisis por reglas de una vacante (implementacion UNICA).

Antes esta logica estaba triplicada: ``cli._extract_job_analysis``,
``ui._analyze_job`` y ``run_full_flow.run_analysis``. La de ``run_full_flow``
llamaba a ``IngestionService.analyze_job``, que no existe (fallaba en todas
las vacantes), y la de la UI era una copia que podia divergir.

Ademas, el analisis ya no lee SOLO el texto: integra los requisitos que
traen los **campos estructurados** del aviso (``jobs.skills`` y
``jobs.languages``), que es donde esta la mayor parte de las competencias
de los avisos reales (ver ``skills_fuente``).
"""
from __future__ import annotations

import hashlib
import sqlite3
from typing import Any, Mapping, Sequence

from jobpulse_v15 import conceptos, skills_fuente
from jobpulse_v15.analysis import EXTRACTOR_VERSION, RuleBasedExtractor
from jobpulse_v15.repository import Repository

#: Version del ANALISIS COMPLETO (texto + campos estructurados). Distinta de
#: ``analysis.EXTRACTOR_VERSION`` (que solo identifica el extractor de
#: reglas): el contenido guardado cambio (se integro ``jobs.skills`` y
#: ``jobs.languages``), asi que las revisiones viejas siguen siendo
#: distinguibles en ``job_analysis`` y el historial queda auditable.
VERSION_ANALISIS = f"{EXTRACTOR_VERSION}+fuente"


def _estados_de_campo(
    field_statuses: Mapping[str, str],
    requisitos_texto: Sequence[Mapping[str, Any]],
    requisitos_fuente: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    """Ajusta los estados de campo al integrar los requisitos de la fuente.

    Regla dura del repositorio (``Repository.save_analysis``): el estado de
    una categoria y el nivel de sus requisitos van juntos:

    * estado ``ambiguous`` -> TODOS sus requisitos son ``ambiguous``;
    * estado ``found``     -> NINGUNO es ``ambiguous``.

    Los requisitos de la fuente son ``inferred`` (el campo dice QUE pide el
    aviso, no si es obligatorio). Si la categoria ya era ``ambiguous`` o
    ``unknown`` (el texto dejo duda), los de la fuente tambien son
    ``ambiguous``; si no, la categoria pasa a ``found`` (el campo se encontro:
    en la fuente).
    """
    estados = dict(field_statuses)
    for requisito in requisitos_fuente:
        categoria = requisito["category"]
        estado = estados.get(categoria)
        if estado in {"ambiguous", "unknown"}:
            requisito["requirement_level"] = "ambiguous"
            estados[categoria] = "ambiguous"
        else:
            estados[categoria] = "found"
    return estados


def _analysis_status(field_statuses: Mapping[str, str]) -> str:
    """``complete`` si ninguna categoria quedo con duda; ``partial`` si no."""
    if any(
        estado in {"unknown", "ambiguous"}
        for estado in field_statuses.values()
    ):
        return "partial"
    return "complete"


def _texto_del_aviso(job: Mapping[str, Any]) -> str:
    """Texto del aviso (descripcion + requisitos), tal como lo lee el motor."""
    return "\n\n".join(
        value.strip()
        for value in (job.get("description_raw"), job.get("requirements_raw"))
        if isinstance(value, str) and value.strip()
    )


def preparar_analisis(
    job: Mapping[str, Any], connection: sqlite3.Connection
) -> dict[str, Any]:
    """Analiza una vacante (texto + campos estructurados) SIN guardar nada.

    Devuelve el "plan" del analisis: texto, hash, estados, requisitos y las
    etiquetas de la fuente que no resolvieron a un concepto. Sirve para la
    simulacion (dry-run) del comando ``enrich requirements-source`` y es el
    MISMO calculo que despues se guarda (una sola implementacion).
    """
    text = _texto_del_aviso(job)
    if not text:
        raise ValueError(
            f"La vacante {job.get('job_id')!r} no tiene descripcion ni "
            "requisitos para analizar."
        )
    result = RuleBasedExtractor().extract(text)

    # Lo que el TEXTO ya dio no se duplica (mismo codigo canonico).
    resueltos_texto, _sin_texto = conceptos.resolver(connection, result.requirements)
    cubiertos = {
        requisito["codigo_canonico"]
        for requisito in resueltos_texto
        if requisito.get("codigo_canonico")
    }
    requisitos_fuente, sin_concepto = skills_fuente.requisitos_de_fuente(
        connection,
        skills=job.get("skills"),
        languages=job.get("languages"),
        ya_cubiertos=cubiertos,
        posting_language=job.get("posting_language"),
    )

    field_statuses = _estados_de_campo(
        result.field_statuses, result.requirements, requisitos_fuente
    )
    requirements = list(result.requirements) + list(requisitos_fuente)
    analysis_status = _analysis_status(field_statuses)
    return {
        "job_id": job.get("job_id"),
        "text": text,
        "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "analysis_status": analysis_status,
        "field_statuses": field_statuses,
        "requirements": requirements,
        "requisitos_fuente": requisitos_fuente,
        "sin_concepto": sin_concepto,
    }


# ──────────────────────────────────────────────────────────────
# Re-análisis incremental (O12 · Ola 1.1 y 1.2)
# ──────────────────────────────────────────────────────────────
#
# El hueco que separaba la CLI de las UIs: el análisis se hacía ANTES del
# pase IA, así que `jobs.skills` / `jobs.languages` (que produce la IA)
# nunca se convertían en requisitos comparables. La CLI lo resolvía con
# `enrich requirements-source --apply` (re-análisis de TODO); las UIs no
# tienen ese paso → 231 avisos quedaban `sin_requisitos` (vs 11 de la CLI).
#
# Aquí se hace lo mismo pero SOLO sobre los avisos que lo necesitan:
# los que tienen campos estructurados y cuyo análisis vigente NO los
# integró (0 requisitos `origin='source_field'`).

#: Valores de `jobs.skills` / `jobs.languages` que NO son "hay dato".
_VALORES_VACIOS = ("", "[]", "{}", "null")


def avisos_con_campos_sin_integrar(repository: Repository) -> list[str]:
    """Job ids con campos estructurados cuyo análisis vigente no los integró.

    Consulta barata (una sola SQL): el aviso tiene `skills`/`languages`
    informados y su análisis vigente **no** tiene ningún requisito
    `origin='source_field'` → el análisis se hizo antes de que la IA
    rellenara los campos (o con un extractor que los ignoraba).
    """
    with repository.database.connection() as connection:
        rows = connection.execute(
            """
            SELECT j.job_id
            FROM jobs AS j
            JOIN job_analysis AS ja
              ON ja.job_id = j.job_id AND ja.is_current = 1
            WHERE (
                    COALESCE(TRIM(j.skills), '') NOT IN ('', '[]', '{}', 'null')
                 OR COALESCE(TRIM(j.languages), '') NOT IN ('', '[]', '{}', 'null')
               )
              AND NOT EXISTS (
                    SELECT 1
                    FROM job_requirements AS r
                    WHERE r.analysis_id = ja.analysis_id
                      AND r.origin = 'source_field'
                  )
            ORDER BY j.job_id
            """
        ).fetchall()
    return [row["job_id"] for row in rows]


def cuenta_analisis_obsoletos(repository: Repository, *, exacto: bool = True) -> int:
    """Cuántos avisos tienen el análisis REALMENTE obsoleto (badge de la UI).

    ``exacto=True`` (por defecto) confirma cada candidato calculando el
    análisis en seco (``analisis_refleja_campos``). **La SQL sola SOBRE-cuenta**:
    un aviso cuyos ``skills``/``languages`` no resuelven a ningún concepto de la
    taxonomía no aporta requisitos nuevos y su análisis ya es correcto (medido
    en la BD real: la SQL daba 67 y el re-análisis 0 actualizados / 67 sin
    cambio). Contar los candidatos como "obsoletos" dejaría el badge mintiendo
    para siempre y pediría un re-análisis que no cambia nada.
    """
    candidatos = avisos_con_campos_sin_integrar(repository)
    if not exacto:
        return len(candidatos)
    return sum(
        1
        for job_id in candidatos
        if not analisis_refleja_campos(repository, job_id)
    )


def _firma_requisitos(requisitos) -> tuple:
    """Firma comparable de un conjunto de requisitos.

    Se comparan categoría + código canónico + texto (sin distinguir mayúsculas
    ni espacios): lo que el MOTOR ve, no el detalle de la escritura.
    """
    return tuple(
        sorted(
            (
                str(r.get("category") or ""),
                str(r.get("codigo_canonico") or ""),
                str(r.get("value_text") or "").strip().lower(),
                str(r.get("origin") or ""),
            )
            for r in requisitos
        )
    )


def analisis_refleja_campos(repository: Repository, job_id: str) -> bool:
    """True si el análisis vigente ya refleja los campos estructurados actuales.

    Calcula el análisis en seco (`preparar_analisis`, SIN guardar) y lo
    compara con el guardado: así no se toca (ni se reescribe) un análisis
    cuyo resultado sería el mismo.

    La comparación se hace **con los códigos canónicos ya resueltos** (igual
    que al guardar): el motor solo ve el código, no el texto escrito.
    """
    job = repository.get_job(job_id)
    if job is None:
        return True
    actual = repository.get_current_analysis(job_id)
    if actual is None:
        return False
    try:
        with repository.database.connection() as connection:
            prepared = preparar_analisis(job, connection)
            resueltos, _sin_concepto = conceptos.resolver(
                connection, prepared["requirements"]
            )
    except ValueError:
        # Sin texto no hay análisis que hacer (lo trata el análisis normal).
        return True
    return _firma_requisitos(resueltos) == _firma_requisitos(
        actual.get("requirements") or []
    )


def avisos_con_texto_cambiado(repository: Repository) -> list[str]:
    """Job ids cuyo TEXTO cambió después de su análisis vigente.

    El análisis guarda el `text_hash` del texto con el que se hizo (sha256
    de descripción + requisitos). Si el scraper vuelve a traer el aviso con
    más texto (p. ej. los campos que ANE no se leían: "Nivel académico",
    "Experiencia laboral"), el análisis vigente **ya no describe** al aviso:
    el motor evaluaría requisitos que ya no son los del texto.

    Esta es la señal de "hay que re-analizar" que faltaba (la de la Ola 1.1
    solo miraba los campos estructurados `skills`/`languages`).
    """
    with repository.database.connection() as connection:
        filas = connection.execute(
            """
            SELECT j.job_id, j.description_raw, j.requirements_raw,
                   ja.text_hash
            FROM jobs AS j
            JOIN job_analysis AS ja
              ON ja.job_id = j.job_id AND ja.is_current = 1
            """
        ).fetchall()
    cambiados: list[str] = []
    for fila in filas:
        texto = "\n\n".join(
            valor.strip()
            for valor in (fila["description_raw"], fila["requirements_raw"])
            if isinstance(valor, str) and valor.strip()
        )
        if not texto:
            continue
        if hashlib.sha256(texto.encode("utf-8")).hexdigest() != fila["text_hash"]:
            cambiados.append(fila["job_id"])
    return cambiados


def reananalizar_texto_cambiado(
    repository: Repository,
    on_progress: Any = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Re-analiza los avisos cuyo texto cambió (el hash ya no cuadra).

    Idempotente: al terminar, el `text_hash` del análisis vigente vuelve a
    ser el del texto actual, así que el segundo llamado no encuentra nada.
    """
    candidatos = avisos_con_texto_cambiado(repository)
    stats: dict[str, Any] = {
        "candidatos": len(candidatos),
        "reanalizados": 0,
        "errores": 0,
    }
    for job_id in candidatos:
        try:
            if not dry_run:
                extract_job_analysis(repository, job_id)
            stats["reanalizados"] += 1
        except Exception as exc:  # noqa: BLE001 - un aviso malo no para el lote
            stats["errores"] += 1
            if on_progress:
                on_progress(f"  error en {job_id}: {exc}")
            continue
        if on_progress:
            on_progress(
                f"  re-analizado (texto nuevo) {job_id} "
                f"({stats['reanalizados']}/{len(candidatos)})"
            )
    return stats


def reananalizar_con_campos_fuente(
    repository: Repository,
    on_progress: Any = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Re-analiza los avisos cuyo análisis quedó obsoleto (Ola 1.1).

    "Obsoleto" = el aviso tiene `skills`/`languages` y su análisis vigente
    no los integró. Para cada candidato se calcula el análisis en seco y
    solo se guarda si el resultado **cambia** (así no se infla el historial
    de `job_analysis` con filas idénticas).

    Idempotente: al terminar, el segundo llamado no encuentra candidatos.
    """
    candidatos = avisos_con_campos_sin_integrar(repository)
    stats: dict[str, Any] = {
        "candidatos": len(candidatos),
        "reanalizados": 0,
        "sin_cambio": 0,
        "errores": 0,
        "requisitos_fuente": 0,
    }
    for job_id in candidatos:
        try:
            if analisis_refleja_campos(repository, job_id):
                stats["sin_cambio"] += 1
                continue
            if not dry_run:
                resultado = extract_job_analysis(repository, job_id)
                stats["requisitos_fuente"] += int(resultado.get("requisitos_fuente", 0))
            stats["reanalizados"] += 1
        except Exception as exc:  # noqa: BLE001 - un aviso malo no para el lote
            stats["errores"] += 1
            if on_progress:
                on_progress(f"  error en {job_id}: {exc}")
            continue
        if on_progress:
            on_progress(
                f"  re-analizado {job_id} "
                f"({stats['reanalizados']}/{len(candidatos)})"
            )
    return stats


def extract_job_analysis(repository: Repository, job_id: str) -> dict[str, Any]:
    """Extrae requisitos (texto + campos estructurados) y guarda el analisis."""
    job = repository.get_job(job_id)
    if job is None:
        raise ValueError(f"No existe la vacante {job_id!r}.")
    with repository.database.connection() as connection:
        prepared = preparar_analisis(job, connection)

    source_context = repository.get_job_source_context(job_id)
    source_site_id = (
        source_context["site_id"] if source_context is not None else None
    )
    source_config_hash = (
        hashlib.sha256(source_context["site_config_json"].encode("utf-8")).hexdigest()
        if source_context is not None
        else None
    )
    analysis_id = repository.save_analysis(
        job_id,
        text_hash=prepared["text_hash"],
        extractor_version=VERSION_ANALISIS,
        analysis_status=prepared["analysis_status"],
        field_statuses=prepared["field_statuses"],
        requirements=prepared["requirements"],
        source_site_id=source_site_id,
        source_config_hash=source_config_hash,
    )
    # Las skills de la fuente que NO resuelven van a la cola de la taxonomia
    # (`concepto_no_normalizado`): es la lista de trabajo para que la
    # taxonomia crezca con datos reales.
    if prepared["sin_concepto"]:
        with repository.database.connection() as connection:
            conceptos.encolar_sin_concepto(
                connection, prepared["sin_concepto"], origen="oferta"
            )
    return {
        "analysis_id": analysis_id,
        "job_id": job_id,
        "analysis_status": prepared["analysis_status"],
        "field_statuses": prepared["field_statuses"],
        "requirements": prepared["requirements"],
        "requisitos_fuente": len(prepared["requisitos_fuente"]),
        "sin_concepto": sorted(
            {f"{categoria}:{variante}" for categoria, variante in prepared["sin_concepto"]}
        ),
    }
