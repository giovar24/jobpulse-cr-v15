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

from typing import Any, Callable, Mapping

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
) -> Callable[[], Any]:
    """Devuelve un ``lambda`` sin argumentos que trae las ofertas del sitio.

    El resultado puede ser una lista o una corrutina: ``IngestionService.
    fetch_and_import`` resuelve las dos (``asyncio.run`` si es corrutina),
    asi que el llamador debe estar FUERA de un event loop en ejecucion.
    """
    if platform_id == "ane":
        return lambda: fetcher.fetch(
            site, pages=pages, port=port, dias=dias
        )
    if platform_id in ("indeed", "linkedin"):
        return lambda: fetcher.fetch(site, pages=pages, port=port)
    if platform_id == "elempleo":
        return lambda: fetcher.fetch(site, port=port)
    if platform_id in _CON_PAGINAS:
        return lambda: fetcher.fetch(site, pages=pages)
    # greenhouse, ashby, lever, recruitee, successfactors, harvie: sin pages.
    return lambda: fetcher.fetch(site)


def necesita_navegador(platform_id: str) -> bool:
    """True si el fetcher necesita Brave/CDP (y por tanto sesion iniciada)."""
    return platform_id in _CON_PUERTO
