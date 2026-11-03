# -*- coding: utf-8 -*-
"""Sondas de scraping (tabla `source_sites`): lectura y activación SIN Tk.

La única verdad sobre qué se ejecuta es `source_sites.enabled`:
`Repository.select_sites()` (y por ende `run_scrapes.py`, `run_full_flow.py`
y las corridas de la UI clásica) solo selecciona sitios habilitados.
Pausar aquí = la sonda no corre; nada se borra ni se pierde.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from jobpulse_v15.repository import Repository


@dataclass(frozen=True)
class SitioFila:
    """Fila de la tabla de sondas (dataclass, testeable sin Tk)."""

    site_id: str
    nombre: str
    plataforma: str
    tipo: str        # api | rss | browser (browser necesita Brave/CDP 9222)
    grupos: str      # "directos, cr-gov"
    activo: bool
    revision: bool   # needs_review (racha de corridas sin ofertas)


class FuentesStore:
    """Operaciones de las sondas sobre el Repository."""

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def sitios(self) -> list[SitioFila]:
        filas: list[SitioFila] = []
        for sitio in self.repository.list_sites():
            filas.append(
                SitioFila(
                    site_id=sitio["site_id"],
                    nombre=sitio.get("site_name") or sitio["site_id"],
                    plataforma=sitio.get("platform_name") or sitio["platform_id"],
                    tipo=sitio.get("provider_type") or "",
                    grupos=", ".join(sitio.get("run_groups") or []) or "—",
                    activo=bool(sitio["enabled"]),
                    revision=bool(sitio.get("review_required")),
                )
            )
        return filas

    def plataformas(self) -> list[str]:
        return sorted({fila.plataforma for fila in self.sitios()})

    def conteo(self) -> tuple[int, int]:
        """(activas, total)."""
        filas = self.sitios()
        return sum(1 for f in filas if f.activo), len(filas)

    def alternar(self, site_ids: Sequence[str], activo: bool) -> int:
        """Activa o pausa los sitios indicados; devuelve cuántos cambiaron."""
        total = 0
        for site_id in site_ids:
            if self.repository.set_site_enabled(site_id, activo):
                total += 1
        return total
