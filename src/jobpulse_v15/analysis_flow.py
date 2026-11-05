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
