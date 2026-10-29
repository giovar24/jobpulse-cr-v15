#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ejecuta el flujo completo (scrape -> analizar -> IA -> comparar perfil)
y envía notificación al terminar.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import threading
import json
from pathlib import Path

from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository
from jobpulse_v15.ia_servidor import asegurar_servidor, servidor_arriba


def notify(title: str, message: str) -> None:
    """Envía notificación del sistema (Windows)."""
    try:
        # Windows 10/11 toast notification via PowerShell
        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
        $text = $xml.GetElementsByTagName("text")
        $text[0].AppendChild($xml.CreateTextNode("{title}")) | Out-Null
        $text[1].AppendChild($xml.CreateTextNode("{message}")) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("JobPulse").Show($toast)
        '''
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], 
                       capture_output=True, timeout=10)
    except Exception as e:
        print(f"Notification failed: {e}", file=sys.stderr)
        # Fallback: console beep
        print("\a", end="", flush=True)


async def run_scrape_async(sites: list[str], pages: int = 1) -> dict:
    """Ejecuta el scrape de los sitios indicados (async)."""
    from jobpulse_v15.ingestion import IngestionService
    from jobpulse_v15.ane import AneFetcher
    from jobpulse_v15.cinde import CindeFetcher
    from jobpulse_v15.procomer import ProcomerFetcher
    from jobpulse_v15.indeed import IndeedFetcher
    from jobpulse_v15.linkedin import LinkedInFetcher
    from jobpulse_v15.workday import WorkdayFetcher
    from jobpulse_v15.greenhouse import GreenhouseFetcher
    from jobpulse_v15.ashby import AshbyFetcher
    from jobpulse_v15.lever import LeverFetcher
    from jobpulse_v15.recruitee import RecruiteeFetcher
    from jobpulse_v15.workable import WorkableFetcher
    from jobpulse_v15.successfactors import SuccessFactorsFetcher
    from jobpulse_v15.harvie import HarvieFetcher
    from jobpulse_v15.elempleo import ElempleoFetcher

    FETCHER_MAP = {
        "ane": AneFetcher,
        "cinde": CindeFetcher,
        "procomer": ProcomerFetcher,
        "indeed": IndeedFetcher,
        "linkedin": LinkedInFetcher,
        "workday": WorkdayFetcher,
        "greenhouse": GreenhouseFetcher,
        "ashby": AshbyFetcher,
        "lever": LeverFetcher,
        "recruitee": RecruiteeFetcher,
        "workable": WorkableFetcher,
        "successfactors": SuccessFactorsFetcher,
        "harvie": HarvieFetcher,
        "elempleo": ElempleoFetcher,
    }

    # Platforms that need browser (CDP port)
    BROWSER_PLATFORMS = {"ane", "indeed", "linkedin", "harvie", "elempleo"}

    db = Database()
    repo = Repository(db)
    service = IngestionService(repo)

    results = {"total_found": 0, "total_new": 0, "errors": 0, "by_site": {}}

    for site_id in sites:
        site = repo.get_site(site_id)
        if not site:
            results["by_site"][site_id] = {"error": "Sitio no existe"}
            results["errors"] += 1
            continue
        if not site.get("enabled"):
            results["by_site"][site_id] = {"status": "pausado"}
            continue

        platform = site["platform_id"]
        fetcher_cls = FETCHER_MAP.get(platform)
        if not fetcher_cls:
            results["by_site"][site_id] = {"error": f"No hay fetcher para {platform}"}
            results["errors"] += 1
            continue

        fetcher = fetcher_cls()
        cfg = site.get("site_config") or {}
        pg = cfg.get("pages", 1) if platform == "workday" else 1

        print(f"\n=== {site_id} ({platform}) ===")
        try:
            if platform in BROWSER_PLATFORMS:
                # Browser fetchers need port and are async
                if platform == "ane":
                    offers = await fetcher.fetch(site, pages=pg, port=9222)
                elif platform in ("indeed", "linkedin"):
                    offers = await fetcher.fetch(site, pages=pg, port=9222)
                elif platform in ("harvie", "elempleo"):
                    offers = await fetcher.fetch(site, port=9222)
                else:
                    offers = await fetcher.fetch(site, port=9222)
                result = service.fetch_and_import(site_id, lambda: offers, run_kind=platform)
            elif platform == "workday":
                offers = fetcher.fetch(site, pages=pg)
                result = service.fetch_and_import(site_id, lambda: offers, run_kind=platform)
            else:
                offers = fetcher.fetch(site)
                result = service.fetch_and_import(site_id, lambda: offers, run_kind=platform)

            results["by_site"][site_id] = result
            results["total_found"] += result.get("jobs_found", 0)
            results["total_new"] += result.get("jobs_new", 0)
            print(f"  OK: {result.get('jobs_new', 0)} nuevas, {result.get('jobs_duplicate', 0)} duplicados")
        except Exception as e:
            results["by_site"][site_id] = {"error": str(e)}
            results["errors"] += 1
            print(f"  ERROR: {e}")

    return results


def run_scrape(sites: list[str], pages: int = 1) -> dict:
    """Wrapper síncrono para run_scrape_async."""
    import asyncio
    return asyncio.run(run_scrape_async(sites, pages))


def run_analysis() -> int:
    """Ejecuta análisis por reglas en todos los pendientes."""
    from jobpulse_v15.ingestion import IngestionService
    db = Database()
    repo = Repository(db)
    service = IngestionService(repo)

    pendientes = repo.search_jobs(review_reason="analysis_missing", limit=10000)
    print(f"\n=== ANÁLISIS POR REGLAS: {len(pendientes)} pendientes ===")

    ok = 0
    for job in pendientes:
        try:
            service.analyze_job(str(job["job_id"]))
            ok += 1
        except Exception as e:
            print(f"  Error analizando {job['job_id']}: {e}")

    print(f"Analizadas: {ok}, fallos: {len(pendientes) - ok}")
    return ok


def run_ia_enrichment(on_log=None) -> dict:
    """Ejecuta enriquecimiento IA y evalúa el resultado contra la BD.

    Devuelve el veredicto de ``ia_estado.evaluar_ia`` (``estado``/``ok``/
    ``motivo``/``avance``) más ``stats_ia``. La BD manda: aunque
    ``pase_completo`` devuelva stats optimistas, si la BD no avanzó es
    ``atascado`` (fallo).
    """
    import asyncio
    from jobpulse_v15 import ia_enrichment as iae
    from jobpulse_v15.ia_estado import (
        snapshot_enriquecimiento, evaluar_ia, resumen_linea,
    )
    from jobpulse_v15.ia_servidor import asegurar_servidor, servidor_arriba

    if not iae.get_ia_client():
        return {
            "estado": "fallido", "ok": False,
            "motivo": "IA no configurada (.env)",
            "avance": {"campos_llenados": 0},
            "stats_ia": {},
        }

    servidor = None
    if not servidor_arriba():
        print("Arrancando servidor IA...")
        servidor = asegurar_servidor()
    else:
        print("Servidor IA ya activo")

    antes = snapshot_enriquecimiento()
    print(
        f"Snapshot antes: jobs={antes.get('total', 0)} "
        f"críticos_pend={antes.get('criticos_pendientes_rec', 0)} "
        f"secundarios_pend={antes.get('secundarios_pendientes_rec', 0)}"
    )

    try:
        r = asyncio.run(iae.pase_completo(on_event=on_log))
    finally:
        if servidor:
            print("Deteniendo servidor IA...")
            servidor.detener()

    # Pausa breve: los últimos INSERTs pueden viajar al final del pase.
    time.sleep(2)
    despues = snapshot_enriquecimiento()
    veredicto = evaluar_ia(antes, despues, r)
    print(resumen_linea(veredicto))
    return veredicto


def run_full_flow(sites: list[str], pages: int = 1, notify_end: bool = True) -> bool:
    """Ejecuta el flujo completo: scrape -> analizar -> IA -> comparar perfil.

    Devuelve ``True`` si todo salió bien; ``False`` si hubo errores de scrape
    o el enriquecimiento IA no progresó (``atascado``/``fallido``).
    """
    print("=" * 60)
    print("FLUJO COMPLETO: scrape -> analizar -> IA -> comparar perfil")
    print("=" * 60)

    # 1. Scrape
    print("\n>>> PASO 1: SCRAPE")
    scrape_results = run_scrape(sites)

    # 2. Análisis por reglas
    print("\n>>> PASO 2: ANÁLISIS POR REGLAS")
    run_analysis()

    # 3. Enriquecimiento IA (con evaluación éxito/fallo)
    print("\n>>> PASO 3: ENRIQUECIMIENTO IA")
    ia_result = run_ia_enrichment(on_log=lambda t: print(f"  IA: {t}"))
    ia_ok = bool(ia_result.get("ok"))
    print(f"Veredicto IA: {ia_result.get('estado')} — {ia_result.get('motivo')}")

    # 4. Comparar perfil (requiere UI, solo reportar)
    print("\n>>> PASO 4: COMPARAR PERFIL")
    print("Para ver resultados filtrados por perfil, abre la UI y usa 'Buscar' con filtro de compatibilidad.")

    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    print(f"Sitios procesados: {len(sites)}")
    print(f"Ofertas encontradas: {scrape_results['total_found']}")
    print(f"Ofertas nuevas: {scrape_results['total_new']}")
    print(f"Errores scrape: {scrape_results['errors']}")
    av = ia_result.get("avance", {})
    print(f"IA: {ia_result.get('estado')} | campos llenados: {av.get('campos_llenados', 0)}")
    print(f"    {ia_result.get('motivo')}")
    exito = ia_ok and scrape_results["errors"] == 0
    print(f"RESULTADO: {'✅ ÉXITO' if exito else '❌ CON PROBLEMAS'}")

    if notify_end:
        if exito:
            title = "JobPulse: Flujo completado ✅"
        else:
            title = "JobPulse: Flujo con problemas ⚠️"
        msg = (
            f"Nuevas: {scrape_results['total_new']} | "
            f"Errores: {scrape_results['errors']} | "
            f"IA: {ia_result.get('estado')}"
        )
        notify(title, msg)

    return exito


def main() -> int:
    parser = argparse.ArgumentParser(description="Flujo completo JobPulse con notificación")
    parser.add_argument("sites", nargs="*", help="Site IDs a procesar (default: todos activos)")
    parser.add_argument("--pages", type=int, default=1, help="Páginas para Workday")
    parser.add_argument("--no-notify", action="store_true", help="No enviar notificación al final")
    parser.add_argument("--only-scrape", action="store_true", help="Solo scrape (sin IA/análisis)")
    args = parser.parse_args()

    if args.sites:
        sites = args.sites
    else:
        from jobpulse_v15.repository import Repository
        from jobpulse_v15.db import Database
        db = Database()
        repo = Repository(db)
        sites = [s["site_id"] for s in repo.list_sites(enabled_only=True)]

    if args.only_scrape:
        run_scrape(sites, pages=args.pages)
        return 0
    exito = run_full_flow(sites, pages=args.pages, notify_end=not args.no_notify)
    return 0 if exito else 1


if __name__ == "__main__":
    sys.exit(main())