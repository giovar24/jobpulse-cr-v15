# -*- coding: utf-8 -*-
"""Fuentes que se pueden barrir (selección del barrido) — SIN Tk.

La lista sale de `source_sites` (la misma tabla que la tarjeta "Sondas de
scraping" de Configuración): lo que está **pausado** no entra en la corrida.

Los grupos (`run_groups_json`) son los mismos que usa el CLI
(`scrape <plataforma> --group directos|cr-gov|cr-jobs`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jobpulse_v15.repository import Repository

TODOS = "Todos los grupos"


@dataclass(frozen=True)
class SitioScrape:
    """Sitio que se puede barrear."""

    site_id: str
    nombre: str
    plataforma: str
    grupos: tuple[str, ...]
    activo: bool
    paginas: int


class ScrapingStore:
    """Selección de sitios para el barrido (operaciones sobre el Repository)."""

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def sitios(self, grupo: str | None = None) -> list[SitioScrape]:
        filas: list[SitioScrape] = []
        for sitio in self.repository.list_sites():
            grupos = tuple(sitio.get("run_groups") or ())
            if grupo and grupo not in grupos:
                continue
            config = sitio.get("site_config") or {}
            filas.append(SitioScrape(
                site_id=sitio["site_id"],
                nombre=sitio.get("site_name") or sitio["site_id"],
                plataforma=sitio.get("platform_name") or sitio.get("platform_id", ""),
                grupos=grupos,
                activo=bool(sitio.get("enabled")),
                paginas=int(config.get("pages", 0) or 0),
            ))
        return filas

    def grupos(self) -> list[str]:
        """Grupos de corrida que existen en la BD (ordenados)."""
        vistos: set[str] = set()
        for sitio in self.repository.list_sites():
            vistos.update(sitio.get("run_groups") or ())
        return sorted(vistos)

    def sitios_para_barrer(self, grupo: str | None = None) -> list[str]:
        """Ids de los sitios **activos** del grupo (lo que sí entra al barrido)."""
        return [f.site_id for f in self.sitios(grupo) if f.activo]

    def resumen(self, grupo: str | None = None) -> dict[str, Any]:
        """Conteos por plataforma para mostrar antes de barrer."""
        filas = self.sitios(grupo)
        por_plataforma: dict[str, int] = {}
        for fila in filas:
            por_plataforma[fila.plataforma] = por_plataforma.get(fila.plataforma, 0) + 1
        return {
            "total": len(filas),
            "activos": sum(1 for f in filas if f.activo),
            "por_plataforma": por_plataforma,
        }
