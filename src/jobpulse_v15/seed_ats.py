"""Directorio de tableros ATS de Costa Rica y su registro en la BD.

Porta a v1.5 los tableros que v1.x descubrió con sus sondeos (Workday,
Greenhouse, Ashby, Lever, Recruitee, Workable, SuccessFactors). Los datos
viven versionados en ``src/jobpulse_v15/seeds/*.json`` (NO en
``data/empresas/``, que está en ``.gitignore``); la fuente original fue el
escaneo de v1.x: ``data/empresas/workday_cr.json``, ``otros_ats_cr.json`` y
``successfactors_sites.json``.

Siguiendo la regla del proyecto, la config declarativa termina en la BD
(``source_sites``); este módulo solo siembra y es idempotente: un tablero ya
registrado (por ``site_id`` o por ``base_url``) se omite y nunca se pisa.

Uso::

    from jobpulse_v15.seed_ats import registrar_directorio
    stats = registrar_directorio(repository)   # {"registrados": [...], "omitidos": [...]}
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from jobpulse_v15.repository import Repository

SEEDS_DIR = Path(__file__).with_name("seeds")

# platform_id -> (nombre, provider_type, language) — mismos valores que
# `init-sources` usa para las plataformas ATS.
PLATAFORMAS: dict[str, tuple[str, str, str]] = {
    "workday": ("Workday", "api", "en"),
    "greenhouse": ("Greenhouse", "api", "en"),
    "ashby": ("Ashby", "api", "en"),
    "lever": ("Lever", "api", "en"),
    "recruitee": ("Recruitee", "api", "en"),
    "workable": ("Workable", "api", "en"),
    "successfactors": ("SuccessFactors", "rss", "en"),
}

# Plataformas de los seeds que un fetcher de v1.5 sabe ejecutar.
PLATAFORMAS_SOPORTADAS = tuple(PLATAFORMAS)

_GRUPO_DIRECTOS = ("directos",)


def _slug(texto: str) -> str:
    """'Kuehne+Nagel' -> 'kuehne-nagel' (valido para site_id)."""
    limpio = re.sub(r"[^a-z0-9]+", "-", texto.casefold()).strip("-").strip("_")
    return limpio or "board"


def _normalizar(entrada: Mapping[str, Any], plataforma: str) -> dict[str, str] | None:
    """Convierte una fila de seed en ``{"platform", "company", "base_url"}``.

    Devuelve ``None`` si falta la URL o la plataforma no tiene fetcher.
    """
    platform = str(
        entrada.get("platform") or entrada.get("plataforma") or plataforma or ""
    ).strip().casefold()
    if platform not in PLATAFORMAS:
        return None
    url = str(entrada.get("board_url") or entrada.get("base") or "").strip()
    if not url:
        return None
    company = str(
        entrada.get("company") or entrada.get("empresa") or ""
    ).strip() or url
    return {"platform": platform, "company": company, "base_url": url}


def cargar_directorio(
    plataformas: Sequence[str] | None = None,
) -> list[dict[str, str]]:
    """Lee los seeds empaquetados y devuelve tableros normalizados.

    ``plataformas`` (opcional) restringe por platform_id; sin él se cargan
    todos los archivos de :data:`SEEDS_DIR`.
    """
    permitidas = (
        {p.strip().casefold() for p in plataformas} if plataformas else None
    )
    tableros: list[dict[str, str]] = []
    if not SEEDS_DIR.is_dir():
        return tableros
    for archivo in sorted(SEEDS_DIR.glob("*.json")):
        # workday_cr.json -> workday; ats_cr.json/successfactors_cr.json -> por fila
        nombre = archivo.stem.split("_")[0]
        try:
            filas = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(filas, list):
            continue
        for fila in filas:
            if not isinstance(fila, dict):
                continue
            normalizado = _normalizar(fila, nombre)
            if normalizado is None:
                continue
            if permitidas is not None and normalizado["platform"] not in permitidas:
                continue
            tableros.append(normalizado)
    return tableros


def _config_sitio(plataforma: str) -> dict[str, Any]:
    """site_config del adapter: el texto de busqueda restringe a Costa Rica."""
    config: dict[str, Any] = {"adapter": plataforma, "country_query": "Costa Rica"}
    if plataforma == "workday":
        # Workday pagina el listado con un texto de busqueda adicional.
        config["search_text"] = "Costa Rica"
    return config


def registrar_directorio(
    repository: Repository,
    plataformas: Sequence[str] | None = None,
    *,
    enabled: bool = True,
    dry_run: bool = False,
    on_msg: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Registra los tableros del directorio como ``source_sites``.

    Idempotente y conservador: omite (no pisa) si el ``site_id`` o la
    ``base_url`` ya existen. Devuelve ``{"registrados": [site_id...],
    "omitidos": [(site_id, motivo)...], "tableros": n}``.
    """

    def log(texto: str) -> None:
        if on_msg:
            try:
                on_msg(texto)
            except Exception:  # el emisor nunca debe romper el registro
                pass

    tableros = cargar_directorio(plataformas)
    registrados: list[str] = []
    omitidos: list[tuple[str, str]] = []

    try:
        existentes = repository.list_sites()
    except sqlite3.Error:
        existentes = []
    ids_usados = {str(sitio["site_id"]) for sitio in existentes}
    urls_usadas = {
        str(sitio.get("base_url") or "").strip().rstrip("/").casefold()
        for sitio in existentes
    }

    for tablero in tableros:
        platform = tablero["platform"]
        nombre_plataforma = PLATAFORMAS[platform][0]
        site_id_base = f"{platform}-{_slug(tablero['company'])}"
        site_id = site_id_base
        sufijo = 2
        while site_id in ids_usados:
            site_id = f"{site_id_base}-{sufijo}"
            sufijo += 1

        url_clave = tablero["base_url"].strip().rstrip("/").casefold()
        if url_clave in urls_usadas:
            omitidos.append((site_id, "base_url ya registrada"))
            continue

        site_name = f"{tablero['company']} ({nombre_plataforma})"
        if dry_run:
            registrados.append(site_id)
            ids_usados.add(site_id)
            urls_usadas.add(url_clave)
            log(f"[dry-run] registraria: {site_id} -> {tablero['base_url']}")
            continue

        try:
            if repository.get_platform(platform) is None:
                pname, ptype, plang = PLATAFORMAS[platform]
                repository.register_platform(platform, pname, ptype, plang)
                log(f"Plataforma registrada: {platform}")
            repository.register_site(
                site_id,
                platform,
                site_name,
                tablero["base_url"],
                company_name=tablero["company"],
                country="CR",
                run_groups=_GRUPO_DIRECTOS,
                site_config=_config_sitio(platform),
                enabled=enabled,
            )
        except (sqlite3.Error, ValueError) as exc:
            omitidos.append((site_id, str(exc)))
            continue

        registrados.append(site_id)
        ids_usados.add(site_id)
        urls_usadas.add(url_clave)
        log(f"Sitio registrado: {site_id} -> {tablero['base_url']}")

    stats = {
        "tableros": len(tableros),
        "registrados": registrados,
        "omitidos": omitidos,
        "dry_run": dry_run,
    }
    log(
        f"Directorio ATS: {len(registrados)} registrado(s), "
        f"{len(omitidos)} omitido(s) de {len(tableros)} tablero(s)"
        + (" [dry-run]" if dry_run else "")
    )
    return stats
