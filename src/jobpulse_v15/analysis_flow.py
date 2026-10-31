# -*- coding: utf-8 -*-
"""Analisis por reglas de una vacante (implementacion UNICA).

Antes esta logica estaba triplicada: ``cli._extract_job_analysis``,
``ui._analyze_job`` y ``run_full_flow.run_analysis``. La de ``run_full_flow``
llamaba a ``IngestionService.analyze_job``, que no existe (fallaba en todas
las vacantes), y la de la UI era una copia que podia divergir.
"""
from __future__ import annotations

import hashlib
from typing import Any

from jobpulse_v15.analysis import EXTRACTOR_VERSION, RuleBasedExtractor
from jobpulse_v15.repository import Repository


def extract_job_analysis(repository: Repository, job_id: str) -> dict[str, Any]:
    """Extrae requisitos por reglas y guarda el analisis de la vacante."""
    job = repository.get_job(job_id)
    if job is None:
        raise ValueError(f"No existe la vacante {job_id!r}.")
    text = "\n\n".join(
        value.strip()
        for value in (job.get("description_raw"), job.get("requirements_raw"))
        if isinstance(value, str) and value.strip()
    )
    if not text:
        raise ValueError(
            f"La vacante {job_id!r} no tiene descripcion ni requisitos para analizar."
        )
    result = RuleBasedExtractor().extract(text)
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
        text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        extractor_version=EXTRACTOR_VERSION,
        analysis_status=result.analysis_status,
        field_statuses=result.field_statuses,
        requirements=result.requirements,
        source_site_id=source_site_id,
        source_config_hash=source_config_hash,
    )
    return {
        "analysis_id": analysis_id,
        "job_id": job_id,
        "analysis_status": result.analysis_status,
        "field_statuses": result.field_statuses,
        "requirements": result.requirements,
    }
