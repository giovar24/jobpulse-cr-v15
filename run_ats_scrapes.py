#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Scraping masivo de todos los tableros ATS del directorio CR.

Uso:
    python run_ats_scrapes.py [--platform PLATFORM] [--site SITE_ID] [--dry-run]
    python run_ats_scrapes.py --platform workday --site workday-intel

Plataformas: workday, greenhouse, ashby, lever, workable, successfactors, recruitee
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any, Callable, Mapping, Sequence

from jobpulse_v15.ashby import AshbyFetcher
from jobpulse_v15.db import Database
from jobpulse_v15.greenhouse import GreenhouseFetcher
from jobpulse_v15.harvie import HarvieFetcher
from jobpulse_v15.ingestion import IngestionService, IngestionError
from jobpulse_v15.lever import LeverFetcher
from jobpulse_v15.recruitee import RecruiteeFetcher
from jobpulse_v15.repository import Repository
from jobpulse_v15.successfactors import SuccessFactorsFetcher
from jobpulse_v15.workable import WorkableFetcher
from jobpulse_v15.workday import WorkdayFetcher

FETCHER_MAP = {
    "ashby": AshbyFetcher,
    "greenhouse": GreenhouseFetcher,
    "harvie": HarvieFetcher,
    "lever": LeverFetcher,
    "recruitee": RecruiteeFetcher,
    "successfactors": SuccessFactorsFetcher,
    "workable": WorkableFetcher,
    "workday": WorkdayFetcher,
}

PLATFORM_ORDER = ["workday", "greenhouse", "ashby", "lever", "recruitee", "workable", "successfactors", "harvie"]


def build_fetcher(platform: str):
    cls = FETCHER_MAP[platform]
    return cls()


def run_site(ingestion: IngestionService, site: Mapping[str, Any], fetcher, dry_run: bool = False) -> dict[str, Any]:
    site_id = site["site_id"]
    platform = site["platform_id"]
    cfg = site.get("site_config") or {}
    pages = cfg.get("pages", 1) if platform == "workday" else 1

    print(f"\n=== {site_id} ({platform}) ===", flush=True)

    if not site.get("enabled"):
        return {"site_id": site_id, "status": "skipped", "reason": "pausado"}

    if dry_run:
        return {"site_id": site_id, "status": "dry-run", "reason": "simulado"}

    try:
        if platform == "workday":
            result = ingestion.fetch_and_import(
                site_id,
                lambda: fetcher.fetch(site, pages=pages),
                run_kind=platform,
            )
        else:
            result = ingestion.fetch_and_import(
                site_id,
                lambda: fetcher.fetch(site),
                run_kind=platform,
            )
        return {"site_id": site_id, "status": "ok", "result": result}
    except IngestionError as exc:
        return {"site_id": site_id, "status": "error", "error": str(exc)}
    except Exception as exc:
        return {"site_id": site_id, "status": "error", "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Scraping masivo ATS CR")
    parser.add_argument("--platform", action="append", choices=PLATFORM_ORDER, help="Filtrar por plataforma (repetible)")
    parser.add_argument("--site", action="append", help="Filtrar por site_id exacto (repetible)")
    parser.add_argument("--dry-run", action="store_true", help="Solo simular, no hacer peticiones")
    parser.add_argument("--continue-on-error", action="store_true", help="Continuar si un sitio falla")
    args = parser.parse_args()

    db = Database()
    repo = Repository(db)
    ingestion = IngestionService(repo)

    all_sites = repo.list_sites(enabled_only=False)
    ats_sites = [s for s in all_sites if s["platform_id"] in PLATFORM_ORDER]

    if args.platform:
        ats_sites = [s for s in ats_sites if s["platform_id"] in args.platform]
    if args.site:
        ats_sites = [s for s in ats_sites if s["site_id"] in args.site]

    if not ats_sites:
        print("No hay sitios ATS que coincidan con los filtros.")
        return 0

    print(f"Sitios a procesar: {len(ats_sites)}")
    if args.dry_run:
        print("MODO DRY-RUN: no se harán peticiones HTTP.")

    # Agrupar por plataforma para reutilizar instancias de fetcher
    results = []
    for platform in PLATFORM_ORDER:
        platform_sites = [s for s in ats_sites if s["platform_id"] == platform]
        if not platform_sites:
            continue

        fetcher = build_fetcher(platform)
        print(f"\n{'='*60}")
        print(f"PLATAFORMA: {platform.upper()} ({len(platform_sites)} sitios)")
        print(f"{'='*60}")

        for site in platform_sites:
            res = run_site(ingestion, site, fetcher, dry_run=args.dry_run)
            results.append(res)

            status = res["status"]
            if status == "ok":
                r = res.get("result", {})
                print(f"  ✓ {res['site_id']}: {r.get('jobs_new', 0)} nuevos, {r.get('jobs_duplicate', 0)} duplicados, {r.get('jobs_skipped', 0)} omitidos")
            elif status == "dry-run":
                print(f"  ◯ {res['site_id']}: dry-run")
            elif status == "skipped":
                print(f"  - {res['site_id']}: {res['reason']}")
            else:
                print(f"  ✗ {res['site_id']}: ERROR - {res.get('error', 'desconocido')}")
                if not args.continue_on_error:
                    print("\nAbortando por error (usa --continue-on-error para seguir).")
                    return 1

    # Resumen
    ok = sum(1 for r in results if r["status"] == "ok")
    dry = sum(1 for r in results if r["status"] == "dry-run")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")

    print(f"\n{'='*60}")
    print(f"RESUMEN: {ok} ok, {dry} dry-run, {skipped} saltados, {errors} errores")
    print(f"{'='*60}")

    if errors > 0:
        print("\nSitios con error:")
        for r in results:
            if r["status"] == "error":
                print(f"  {r['site_id']}: {r['error']}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())