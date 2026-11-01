# -*- coding: utf-8 -*-
"""
jobpulse_v15.location_utils — Utilidades de ubicacion, modalidad y contrato.

La normalizacion de ubicaciones vive en ``jobpulse_v15.ubicaciones_cr``: un
UNICO catalogo (pais -> provincia -> canton -> distrito) con la division
territorial completa y la tabla de lugares (Ultra Park, AFZ...). Este modulo
conserva la fachada que usan los adaptadores y las utilidades de fecha,
modalidad y tipo de contrato.

Historico: aqui habia una tabla de cantones escrita a mano, con erratas y sin
distritos; producia basura ("Cr", "Lagar", "Lagarte") y REGIONES EQUIVOCADAS
("Tres Rios" -> San Jose cuando es Cartago, "Jaco" -> San Jose cuando es
Puntarenas). Todo eso queda corregido por el catalogo compartido.
"""

from __future__ import annotations

from typing import Dict, Optional

from jobpulse_v15.ubicaciones_cr import resolver_direccion


def normalize_cr_location(
    location: str,
    *,
    descripcion: str | None = None,
    work_mode: str | None = None,
) -> Dict[str, Optional[str]]:
    """Normaliza una ubicacion de Costa Rica a ``{"city", "region"}``.

    Delega en ``ubicaciones_cr.resolver_direccion`` (jerarquia pais ->
    provincia -> canton -> distrito). Si el aviso trae la descripcion y la
    modalidad, se pueden usar como ULTIMO recurso para los campos de ciudad
    que la ubicacion no resuelve (tabla de lugares); no se usa en avisos
    remotos.
    """
    if not location:
        return {"city": None, "region": None}
    return resolver_direccion(
        location, descripcion=descripcion, work_mode=work_mode
    )


def extract_date_from_source_updated(
    source_updated_at: Optional[str], scrape_date: Optional[str] = None
) -> Optional[str]:
    """
    Extrae date_published usando source_updated_at como fallback.

    Para fuentes que no exponen fecha de publicacion (CINDE, etc.),
    usamos la fecha de actualizacion de la fuente o la fecha de scrape.
    """
    if source_updated_at:
        try:
            # Acepta ISO date o ISO datetime
            if "T" in source_updated_at:
                return source_updated_at.split("T")[0]
            return source_updated_at[:10]
        except (ValueError, IndexError):
            pass

    if scrape_date:
        try:
            if "T" in scrape_date:
                return scrape_date.split("T")[0]
            return scrape_date[:10]
        except (ValueError, IndexError):
            pass

    return None


def normalize_work_mode(wfh: Optional[str]) -> str:
    """Normaliza modalidad de trabajo."""
    if not wfh:
        return "unknown"
    w = wfh.strip().lower()
    if w in ("remoto", "remote", "teletrabajo", "100% remoto", "100 % remoto"):
        return "remote"
    if w in ("híbrido", "hibrido", "hybrid", "mixto", "semipresencial"):
        return "hybrid"
    if w in ("presencial", "onsite", "oficina", "en sitio", "en sitio "):
        return "onsite"
    return "unknown"


def normalize_employment_type(raw: Optional[str]) -> Optional[str]:
    """Normaliza tipo de empleo desde texto estructurado (no desde descripcion libre)."""
    if not raw:
        return None
    r = raw.strip().lower()
    # Solo normalizar valores conocidos, NO intentar inferir de texto libre
    if r in ("full-time", "tiempo completo", "full time", "tiempo-completo"):
        return "Full-time"
    if r in ("part-time", "medio tiempo", "part time", "medio-tiempo", "parttime"):
        return "Part-time"
    if r in ("contract", "contrato", "freelance", "temporal"):
        return "Contract"
    if r in ("internship", "pasantía", "pasantia", "practicante"):
        return "Internship"
    # Si no coincide con valores conocidos, devolver None en lugar de texto basura
    return None
