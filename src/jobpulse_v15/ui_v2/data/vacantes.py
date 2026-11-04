# -*- coding: utf-8 -*-
"""Capa de datos de la pestana "Vacantes" (RANKING ATS) para la UI v2.

Sin Tkinter: la pestaña habla con :class:`AtsStore`, que devuelve dataclasses
planas. El score es un RANKING (como lo haria un ATS: "que vacante encaja
mas con este perfil"), NO una calificacion: no toca los umbrales congelados
del Paso 5 ni sus estados.

El score usa los REQUISITOS REALES de cada aviso (con evidencia) y, como
respaldo, las skills extraidas de su descripcion (`jobs.skills`). Los
componentes sin dato NO penalizan: su peso se redistribuye.
"""
from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from jobpulse_v15 import areas
from jobpulse_v15.ats import (
    VEREDICTO_SIN_DATOS,
    componentes_ats,
    percentiles,
    perfil_ats_desde_facts,
    promedios_componentes,
    ranking_ats,
)
from jobpulse_v15.repository import Repository
from jobpulse_v15.ui_v2.i18n import t

logger = logging.getLogger("jobpulse.vacantes")

VEREDICTOS = ("fuerte", "ajustable", "debil", VEREDICTO_SIN_DATOS)

# Mezcla de las dos senales semanticas (calibrada sobre el corpus real):
# 65 % la familia de puesto (cargos del perfil vs TITULO del aviso) y 35 %
# el contenido (cargos del perfil vs aviso completo). Con solo el titulo se
# pierde precision; con solo el documento el ruido del texto domina.
PESO_SEMANTICA_TITULO = 0.65
PESO_SEMANTICA_DOCUMENTO = 0.35

ETIQUETAS_VEREDICTO = {
    "fuerte": t("Fuerte"),
    "ajustable": t("Ajustable"),
    "debil": t("Débil"),
    VEREDICTO_SIN_DATOS: t("Sin datos"),
}


@dataclass(frozen=True)
class VacanteAts:
    """Una vacante con su score ATS y el desglose de los componentes."""

    job_id: str
    title: str
    company: str
    area: str
    score: float | None
    veredicto: str
    semantica_pct: float | None
    skills_pct: float | None
    experiencia_pct: float | None
    educacion_pct: float | None
    idiomas_pct: float | None
    skills_cubiertas: tuple[str, ...] = ()
    skills_faltantes: tuple[str, ...] = ()
    posting_language: str = ""
    analysis_status: str = ""
    estado_paso5: str = ""
    source_url: str = ""
    # O2.2: cuantos requisitos OBLIGATORIOS declara el aviso (analisis
    # vigente). Los `preferred` no cuentan (misma regla dura del Paso 5).
    req_obligatorios: int = 0
    componentes: Mapping[str, str] = field(default_factory=dict)

    @property
    def veredicto_legible(self) -> str:
        return ETIQUETAS_VEREDICTO.get(self.veredicto, self.veredicto or "—")

    @property
    def tiene_score(self) -> bool:
        return self.score is not None


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor.strip()
    return str(valor).strip()


def _pct(valor: float | None) -> str:
    if valor is None:
        return "n/d"
    return f"{valor:.0f} %"


def skills_de_aviso(valor: Any) -> list[str]:
    """Lee `jobs.skills` (JSON) y devuelve la lista de skills."""
    if not valor:
        return []
    if isinstance(valor, (list, tuple)):
        return [_texto(item) for item in valor if _texto(item)]
    texto = _texto(valor)
    if not texto:
        return []
    try:
        datos = json.loads(texto)
    except (TypeError, ValueError):
        return [texto]
    if isinstance(datos, list):
        return [_texto(item) for item in datos if _texto(item)]
    return [texto]


class AtsStore:
    """Calcula y ordena el ranking ATS de las vacantes contra el perfil."""

    def __init__(self, repository: Repository, retencion_store: Any = None) -> None:
        self.repository = repository
        if retencion_store is None:
            from jobpulse_v15.ui_v2.data.retencion import RetencionStore

            retencion_store = RetencionStore()
        self.retencion = retencion_store

    # -- datos base --
    def perfil(self) -> dict[str, Any]:
        """Perfil del candidato en el formato que espera el ranking."""
        return perfil_ats_desde_facts(self.repository.list_candidate_profile_facts())

    def avisos(self, limite: int = 5000) -> list[dict[str, Any]]:
        """Avisos guardados (los que la UI puede ver).

        Respeta la **retención** (O8/O10): por defecto solo los avisos
        vigentes (la preferencia se cambia en Configuración).
        """
        solo_vigentes, ventana = self.retencion.ventana_consulta()
        return self.repository.search_jobs(
            limit=limite,
            solo_vigentes=solo_vigentes,
            ventana_retencion_meses=ventana,
        )

    def areas_por_aviso(self) -> dict[str, str]:
        with self.repository.database.connection() as connection:
            return areas.areas_por_oferta(connection)

    def areas_del_perfil(self) -> set[str]:
        with self.repository.database.connection() as connection:
            return areas.areas_del_perfil(connection)

    def estados_paso5(self) -> dict[str, str]:
        """Estado del Paso 5 de la corrida vigente (si existe)."""
        try:
            with self.repository.database.connection() as connection:
                corrida = connection.execute(
                    "SELECT DISTINCT corrida_id FROM job_match WHERE valida = 1 "
                    "ORDER BY corrida_id DESC LIMIT 1"
                ).fetchone()
                if corrida is None:
                    return {}
                filas = connection.execute(
                    "SELECT job_id, estado FROM job_match "
                    "WHERE valida = 1 AND corrida_id = ?",
                    (corrida["corrida_id"],),
                ).fetchall()
        except Exception as error:  # pragma: no cover - base sin paso 5
            logger.debug("No hay estados del Paso 5: %s", error)
            return {}
        return {str(fila["job_id"]): str(fila["estado"] or "") for fila in filas}

    # -- ranking --
    def calcular(
        self,
        *,
        engine: Any = None,
        limite: int = 5000,
        progreso: Callable[[str], None] | None = None,
    ) -> list[VacanteAts]:
        """Calcula el score ATS de cada aviso y lo ordena de mayor a menor.

        ``engine`` es un :class:`SemanticSearchEngine` (opcional): sin el, el
        componente semantico queda "n/d" y el resto del score sigue valiendo.

        El score se calcula en DOS PASADAS para que los avisos sean
        comparables entre si: primero los componentes de cada aviso (y el
        promedio de cada componente en el corpus) y despues el total con
        pesos fijos, imputando el promedio a lo que no tiene dato.
        """
        avisos = self.avisos(limite=limite)
        if not avisos:
            return []
        if progreso:
            progreso(f"{len(avisos)} avisos · preparando requisitos…")

        perfil = self.perfil()
        comparaciones = self.repository.compare_jobs_to_candidate_profile(avisos)
        areas_por_aviso = self.areas_por_aviso()
        estados = self.estados_paso5()

        percentil_sem: dict[str, float] = {}
        if engine is not None:
            if progreso:
                progreso("Vectorizando avisos (la primera vez tarda)…")
            try:
                percentil_sem = self._similitudes(engine, avisos, perfil, progreso)
            except Exception as error:
                logger.warning("No se pudo calcular la similitud semántica: %s", error)
                if progreso:
                    progreso(f"Sin embeddings: {error}")

        # -- PASADA 1: los componentes de cada aviso ------------------------
        desgloses: dict[str, Any] = {}
        for aviso in avisos:
            job_id = str(aviso.get("job_id") or "")
            comparacion = comparaciones.get(job_id) or {}
            percentil = percentil_sem.get(job_id)
            notas = (
                {"semantica": f"percentil {percentil:.0f} del corpus"}
                if percentil is not None
                else None
            )
            desgloses[job_id] = componentes_ats(
                perfil,
                requisitos=comparacion.get("requirements") or [],
                semantic_score=(percentil / 100.0) if percentil is not None else None,
                skills_vacante=skills_de_aviso(aviso.get("skills")),
                notas=notas,
            )
        imputacion = promedios_componentes(desgloses.values())

        # -- PASADA 2: el score final (pesos fijos + imputacion) ------------
        filas: list[VacanteAts] = []
        for aviso in avisos:
            job_id = str(aviso.get("job_id") or "")
            comparacion = comparaciones.get(job_id) or {}
            ranking = ranking_ats(
                perfil,
                desglose=desgloses[job_id],
                imputacion=imputacion,
            )
            filas.append(
                VacanteAts(
                    job_id=job_id,
                    title=_texto(aviso.get("title")) or "Vacante sin título",
                    company=_texto(aviso.get("company")) or "—",
                    area=areas_por_aviso.get(job_id, "") or "—",
                    score=ranking.total,
                    veredicto=ranking.veredicto,
                    semantica_pct=ranking.componentes["semantica"].pct,
                    skills_pct=ranking.componentes["skills"].pct,
                    experiencia_pct=ranking.componentes["experiencia"].pct,
                    educacion_pct=ranking.componentes["educacion"].pct,
                    idiomas_pct=ranking.componentes["idiomas"].pct,
                    skills_cubiertas=tuple(ranking.skills_cubiertas),
                    skills_faltantes=tuple(ranking.skills_faltantes),
                    posting_language=_texto(aviso.get("posting_language")),
                    analysis_status=_texto(comparacion.get("analysis_status")),
                    estado_paso5=estados.get(job_id, ""),
                    source_url=_texto(aviso.get("source_url")),
                    req_obligatorios=int(aviso.get("req_obligatorios") or 0),
                    componentes={
                        clave: componente.detalle
                        for clave, componente in ranking.componentes.items()
                    },
                )
            )
        filas.sort(key=lambda fila: (-(fila.score if fila.score is not None else -1), fila.title))
        return filas

    def _similitudes(
        self,
        engine: Any,
        avisos: Sequence[Mapping[str, Any]],
        perfil: Mapping[str, Any],
        progreso: Callable[[str], None] | None = None,
    ) -> dict[str, float]:
        """PERCENTIL semantico de cada aviso dentro del corpus (0-100).

        Formula (calibrada sobre el corpus real): la media de los cosenos
        entre los CARGOS del perfil y (a) el titulo del aviso y (b) el aviso
        completo, mezcladas 65/35. El percentil (no el coseno crudo) es lo
        que se usa: los cosenos viven comprimidos y no distinguen nada.
        """
        titulos = [str(t) for t in (perfil.get("titulos") or []) if str(t).strip()]
        if not titulos:
            return {}
        jobs = [dict(aviso) for aviso in avisos]
        engine.index_jobs(jobs)
        engine.index_titulos(jobs)
        if progreso:
            progreso("Embeddings listos · calculando similitud…")
        e_perfil = engine.embed_texts(titulos, tipo="query")
        ids_doc, mat_doc = engine.vectors("doc")
        ids_tit, mat_tit = engine.vectors("titulo")
        if mat_doc is None or mat_tit is None or len(e_perfil) == 0:
            return {}
        indice_doc = {job_id: i for i, job_id in enumerate(ids_doc)}
        indice_tit = {job_id: i for i, job_id in enumerate(ids_tit)}
        claves: list[str] = []
        crudos: list[float] = []
        for aviso in avisos:
            job_id = str(aviso.get("job_id") or "")
            if job_id not in indice_doc or job_id not in indice_tit:
                continue
            vec_doc = mat_doc[indice_doc[job_id]]
            vec_tit = mat_tit[indice_tit[job_id]]
            titulo_score = float((e_perfil @ vec_tit).mean())
            documento_score = float((e_perfil @ vec_doc).mean())
            crudos.append(
                PESO_SEMANTICA_TITULO * titulo_score
                + PESO_SEMANTICA_DOCUMENTO * documento_score
            )
            claves.append(job_id)
        if progreso:
            progreso(f"Similitud calculada ({len(claves)} avisos).")
        return dict(zip(claves, percentiles(crudos)))


# -- presentacion --
def filtrar(
    filas: Sequence[VacanteAts],
    *,
    texto: str = "",
    veredicto: str = "",
    solo_mi_perfil: bool = False,
    areas_perfil: Sequence[str] = (),
    solo_requisitos: bool = False,
) -> list[VacanteAts]:
    """Filtra el ranking por texto, veredicto, areas del perfil y requisitos."""
    termino = (texto or "").casefold().strip()
    areas_perfil = set(areas_perfil or ())
    resultado: list[VacanteAts] = []
    for fila in filas:
        if veredicto and fila.veredicto != veredicto:
            continue
        if solo_requisitos and fila.req_obligatorios < 1:
            continue
        if solo_mi_perfil and areas_perfil and fila.area not in areas_perfil:
            continue
        if termino:
            junto = f"{fila.title} {fila.company}".casefold()
            if termino not in junto:
                continue
        resultado.append(fila)
    return resultado


def resumen(filas: Sequence[VacanteAts]) -> dict[str, int]:
    """Cifras de la franja de resumen."""
    conteo = {"total": len(filas), "fuerte": 0, "ajustable": 0, "debil": 0, "sin_datos": 0}
    for fila in filas:
        conteo[fila.veredicto] = conteo.get(fila.veredicto, 0) + 1
    return conteo


CAMPOS_CSV: tuple[str, ...] = (
    "score",
    "veredicto",
    "semantica",
    "skills",
    "experiencia",
    "educacion",
    "idiomas",
    "titulo",
    "empresa",
    "area",
    "skills_cubiertas",
    "skills_faltantes",
    "idioma_aviso",
    "analisis",
    "paso5",
    "requisitos_obligatorios",
    "job_id",
    "url",
)


def exportar_csv(filas: Sequence[VacanteAts], ruta: str | Path) -> int:
    """Escribe el ranking en CSV; devuelve quantas filas escribio."""
    destino = Path(ruta)
    with destino.open("w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(CAMPOS_CSV))
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(
                {
                    "score": fila.score if fila.score is not None else "",
                    "veredicto": fila.veredicto_legible,
                    "semantica": _pct(fila.semantica_pct),
                    "skills": _pct(fila.skills_pct),
                    "experiencia": _pct(fila.experiencia_pct),
                    "educacion": _pct(fila.educacion_pct),
                    "idiomas": _pct(fila.idiomas_pct),
                    "titulo": fila.title,
                    "empresa": fila.company,
                    "area": fila.area,
                    "skills_cubiertas": "; ".join(fila.skills_cubiertas),
                    "skills_faltantes": "; ".join(fila.skills_faltantes),
                    "idioma_aviso": fila.posting_language,
                    "analisis": fila.analysis_status,
                    "paso5": fila.estado_paso5,
                    "requisitos_obligatorios": fila.req_obligatorios,
                    "job_id": fila.job_id,
                    "url": fila.source_url,
                }
            )
    return len(filas)
