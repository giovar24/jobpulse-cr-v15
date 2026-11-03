# -*- coding: utf-8 -*-
"""Como se llama a cada fetcher, en un solo sitio.

Cada adaptador tiene su propia firma y hay tres variations que se confunden
facilmente:

- algunos son ``async def fetch`` (cinde, procomer, indeed, linkedin,
  elempleo) y otros son ``def fetch`` (workday, greenhouse, workable, ane,
  harvie...);
- algunos reciben el puerto CDP (``port``) y otros no;
- algunos aceptan ``pages`` y otros no (greenhouse, ashby, lever, recruitee,
  successfactors y harvie NO lo aceptan: barren su tablero completo).

La UI y los scripts CLI necesitan la misma verdad; antes cada uno armaba su
propio ``lambda`` y por eso el barrido de la UI fallaba con los tableros de
API que no aceptan ``pages`` y ``run_full_flow.py``-awaited a los sync (o al
reves, con los async).
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

# Plataformas que aceptan el parametro ``pages``.
_CON_PAGINAS = frozenset({
    "workday", "workable", "cinde", "procomer", "ane", "indeed", "linkedin",
})
# Plataformas que necesitan el puerto CDP del navegador.
_CON_PUERTO = frozenset({"ane", "indeed", "linkedin", "elempleo"})


def construir_llamada(
    platform_id: str,
    fetcher: Any,
    site: Mapping[str, Any],
    *,
    pages: int = 1,
    port: int = 9222,
    dias: int = 30,
    skip_source_job_ids: Sequence[str] | None = None,
) -> Callable[[], Any]:
    """Devuelve un ``lambda`` sin argumentos que trae las ofertas del sitio.

    El resultado puede ser una lista o una corrutina: ``IngestionService.
    fetch_and_import`` resuelve las dos (``asyncio.run`` si es corrutina),
    asi que el llamador debe estar FUERA de un event loop en ejecucion.

    ``skip_source_job_ids`` son los ``source_job_id`` que el usuario descarto
    a mano (``user_job_state.skip_automatic``): no se vuelven a ofrecer. TODOS
    los fetchers lo aceptan, asi que se pasa siempre (el CLI ya lo hacia; el
    dispatcher se quedaba sin el y re-procesaba lo descartado).
    """
    omitidos = frozenset(skip_source_job_ids or ())
    if platform_id == "ane":
        return lambda: fetcher.fetch(
            site, pages=pages, port=port, dias=dias,
            skip_source_job_ids=omitidos,
        )
    if platform_id in ("indeed", "linkedin"):
        return lambda: fetcher.fetch(
            site, pages=pages, port=port, skip_source_job_ids=omitidos,
        )
    if platform_id == "elempleo":
        return lambda: fetcher.fetch(
            site, port=port, skip_source_job_ids=omitidos,
        )
    if platform_id in _CON_PAGINAS:
        return lambda: fetcher.fetch(
            site, pages=pages, skip_source_job_ids=omitidos,
        )
    # greenhouse, ashby, lever, recruitee, successfactors, harvie: sin pages.
    return lambda: fetcher.fetch(site, skip_source_job_ids=omitidos)


def necesita_navegador(platform_id: str) -> bool:
    """True si el fetcher necesita Brave/CDP (y por tanto sesion iniciada)."""
    return platform_id in _CON_PUERTO
