# -*- coding: utf-8 -*-
"""Capa de datos de la UI v2 (SIN Tkinter).

Regla de modularidad: las pestañas no hablan con la base de datos ni con
SQLite; hablan con un "store" que devuelve modelos de vista planos
(dataclasses). Así se puede testear la lógica sin abrir una ventana y
cambiar la base de datos no obliga a tocar las pestañas.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jobpulse_v15.repository import Repository


@dataclass(frozen=True)
class RawQuery:
    """Filtros de la pestaña de datos crudos."""

    texto: str = ""
    plataforma: str = ""
    solo_con_descripcion: bool = False
    limite: int = 5000


@dataclass(frozen=True)
class RawRow:
    """Un aviso tal como quedó en la base (valores crudos, sin interpretar)."""

    job_id: str
    title: str
    company: str
    location_raw: str
    country: str
    region: str
    city: str
    work_mode: str
    employment_type: str
    posting_language: str
    date_published: str
    first_seen_at: str
    last_seen_at: str
    expires_at: str
    salary_raw: str
    salary_min: float | None
    salary_max: float | None
    salary_currency: str
    salary_period: str
    skills: str
    languages: str
    platform: str
    site_id: str
    source_url: str
    description_chars: int
    requirements_chars: int
    user_status: str
    dup_of: str


@dataclass(frozen=True)
class RawDetail:
    """Todo el contenido crudo de un aviso (para el panel de detalle)."""

    row: RawRow
    description_raw: str = ""
    requirements_raw: str = ""
    sources: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    analysis_status: str = ""
    requirement_count: int = 0
    field_statuses: Mapping[str, str] = field(default_factory=dict)


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor.strip()
    return str(valor).strip()


def _numero(valor: Any) -> float | None:
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def recortar(texto: str, largo: int = 80) -> str:
    """Texto de una línea, cortado con puntos suspensivos."""
    limpio = " ".join((texto or "").split())
    if len(limpio) <= largo:
        return limpio
    return limpio[: largo - 1].rstrip() + "…"


def idioma_texto(idioma: str) -> str:
    """Nombre legible del código de idioma del aviso."""
    codigos = {
        "es": "Español",
        "en": "Inglés",
        "mixed": "Mixto",
        "undetermined": "Sin determinar",
    }
    clave = (idioma or "").strip().lower()
    if not clave:
        return "Sin determinar"
    return codigos.get(clave, idioma)


def ubicacion_texto(row: RawRow) -> str:
    """Ubicación legible (prefiere el dato crudo de la fuente)."""
    if row.location_raw:
        return row.location_raw
    partes = [p for p in (row.city, row.region, row.country) if p]
    return ", ".join(partes) if partes else "—"


def salario_texto(row: RawRow) -> str:
    """Salario legible; si no hay cifra, el texto crudo de la fuente."""
    if row.salary_min is None:
        return row.salary_raw or "—"
    moneda = row.salary_currency or ""
    periodo = {
        "monthly": "/mes",
        "annual": "/año",
        "hourly": "/hora",
        "daily": "/día",
        "weekly": "/semana",
    }.get(row.salary_period or "", "")
    if row.salary_max is not None and row.salary_max != row.salary_min:
        base = f"{_numero_texto(row.salary_min)} – {_numero_texto(row.salary_max)}"
    else:
        base = _numero_texto(row.salary_min)
    return f"{base} {moneda}{periodo}".strip()


def _numero_texto(valor: float | None) -> str:
    if valor is None:
        return "—"
    if float(valor).is_integer():
        return f"{int(valor):,}".replace(",", " ")
    return f"{valor:,.2f}".replace(",", " ").replace(".", ",")


def estado_truncado(estado: str) -> str:
    return estado or "—"


class JobsStore:
    """Acceso a los avisos para la UI v2 (envuelve el `Repository`)."""

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    # -- lectura --
    def load(self, query: RawQuery | None = None) -> list[RawRow]:
        """Avisos que cumplen el filtro, ordenados por última actividad."""
        consulta = query or RawQuery()
        jobs = self.repository.search_jobs(
            text=consulta.texto or None,
            limit=max(1, consulta.limite),
            sort_by="last_seen",
            solo_vigentes=False,
        )
        plataformas = self._platform_map()
        filas: list[RawRow] = []
        for job in jobs:
            fila = self._to_row(job, plataformas)
            if consulta.plataforma and fila.platform != consulta.plataforma:
                continue
            if consulta.solo_con_descripcion and fila.description_chars < 200:
                continue
            filas.append(fila)
        return filas

    def detail(self, job_id: str) -> RawDetail | None:
        """Contenido crudo completo de un aviso."""
        job = self.repository.get_job(job_id)
        if not job:
            return None
        plataformas = self._platform_map()
        fila = self._to_row(job, plataformas)
        analysis = self.repository.get_current_analysis(job_id) or {}
        fuentes = tuple(self.repository.get_job_sources(job_id))
        return RawDetail(
            row=fila,
            description_raw=job.get("description_raw") or "",
            requirements_raw=job.get("requirements_raw") or "",
            sources=fuentes,
            analysis_status=str(analysis.get("status") or ""),
            requirement_count=len(analysis.get("requirements") or []),
            field_statuses=dict(analysis.get("field_statuses") or {}),
        )

    def platforms(self) -> list[str]:
        """Plataformas presentes en los avisos (para el filtro)."""
        return sorted({plataforma for plataforma in self._platform_map().values() if plataforma})

    def sources_count(self) -> int:
        with self.repository.database.connection() as con:
            fila = con.execute("SELECT COUNT(*) FROM source_sites").fetchone()
        return int(fila[0]) if fila else 0

    # -- apoyo --
    def _platform_map(self) -> dict[str, str]:
        """job_id -> plataforma (vía sus registros de fuente)."""
        with self.repository.database.connection() as con:
            filas = con.execute(
                "SELECT sr.job_id, s.platform_id FROM job_source_records sr"
                " JOIN source_sites s ON s.site_id = sr.site_id"
            ).fetchall()
        mapa: dict[str, str] = {}
        for job_id, platform_id in filas:
            mapa.setdefault(job_id, platform_id)
        return mapa

    @staticmethod
    def _to_row(job: Mapping[str, Any], plataformas: Mapping[str, str]) -> RawRow:
        descripcion = job.get("description_raw") or ""
        requisitos = job.get("requirements_raw") or ""
        return RawRow(
            job_id=job.get("job_id") or "",
            title=_texto(job.get("title")),
            company=_texto(job.get("company")),
            location_raw=_texto(job.get("location_raw")),
            country=_texto(job.get("country")),
            region=_texto(job.get("region")),
            city=_texto(job.get("city")),
            work_mode=_texto(job.get("work_mode")) or "unknown",
            employment_type=_texto(job.get("employment_type")),
            posting_language=_texto(job.get("posting_language")),
            date_published=_texto(job.get("date_published")),
            first_seen_at=_texto(job.get("first_seen_at")),
            last_seen_at=_texto(job.get("last_seen_at")),
            expires_at=_texto(job.get("expires_at")),
            salary_raw=_texto(job.get("salary_raw")),
            salary_min=_numero(job.get("salary_min")),
            salary_max=_numero(job.get("salary_max")),
            salary_currency=_texto(job.get("salary_currency")),
            salary_period=_texto(job.get("salary_period")),
            skills=_texto(job.get("skills")),
            languages=_texto(job.get("languages")),
            platform=plataformas.get(job.get("job_id") or "", ""),
            site_id=_texto(job.get("site_id")),
            source_url=_texto(job.get("source_url")),
            description_chars=len(descripcion),
            requirements_chars=len(requisitos),
            user_status=_texto(job.get("user_status")),
            dup_of=_texto(job.get("dup_of")),
        )


# -- exportación --
CAMPOS_CSV = (
    "job_id",
    "title",
    "company",
    "platform",
    "location_raw",
    "city",
    "region",
    "country",
    "work_mode",
    "employment_type",
    "posting_language",
    "date_published",
    "last_seen_at",
    "salary_raw",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_period",
    "skills",
    "languages",
    "description_chars",
    "requirements_chars",
    "source_url",
)


def exportar_csv(filas: Sequence[RawRow], ruta: str | Path) -> int:
    """Escribe las filas crudas en CSV; devuelve cuántas escribió."""
    destino = Path(ruta)
    with destino.open("w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(CAMPOS_CSV))
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({campo: getattr(fila, campo) for campo in CAMPOS_CSV})
    return len(filas)


def resumen_por_campo(filas: Iterable[RawRow]) -> dict[str, int]:
    """Conteo de llenado por campo (para las tarjetas de resumen)."""
    filas = list(filas)
    total = len(filas)
    if not total:
        return {}
    return {
        "total": total,
        "con_descripcion": sum(1 for f in filas if f.description_chars >= 200),
        "con_ubicacion": sum(1 for f in filas if f.city or f.region or f.location_raw),
        "con_salario": sum(1 for f in filas if f.salary_min is not None or f.salary_raw),
        "con_requisitos": sum(1 for f in filas if f.requirements_chars),
        "con_fecha": sum(1 for f in filas if f.date_published),
    }
