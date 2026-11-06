#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Flujo completo: scrape → análisis → IA → re-análisis → backfill → Paso 5 →
evidencia, con notificación al terminar.

ENVOLTORIO del orquestador ÚNICO ``jobpulse_v15.pipeline`` (O12 · Ola 2.1):
la lógica de cada etapa vive **una sola vez** (la misma que usan la UI v2 y
los demás llamadores), así que este script ya no puede divergir de la UI.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from jobpulse_v15 import pipeline  # noqa: E402
from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402

ETAPAS_FLUJO_COMPLETO = (
    "scrape",
    "analisis",
    "ia",
    "reanalisis",
    "backfill",
    "paso5",
    "evidencia",
)


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


def run_scrape(sites: list[str], pages: int = 1) -> dict:
    """Solo el barrido (compatibilidad con los llamadores viejos)."""
    db = Database()
    resultado = pipeline.ejecutar(
        Repository(db),
        etapas=("scrape",),
        sites=sites,
        pages=pages,
        db_path=db.path,
        progreso=print,
    )
    return {
        "total_found": resultado["etapas"].get("scrape", {}).get("jobs_found", 0),
        "total_new": resultado["etapas"].get("scrape", {}).get("jobs_new", 0),
        "errors": resultado["etapas"].get("scrape", {}).get("errores", 0),
        "by_site": resultado["etapas"].get("scrape", {}).get("por_sitio", []),
        "ok": resultado["ok"],
    }


def run_analysis() -> int:
    """Análisis por reglas de todos los pendientes (compatibilidad)."""
    db = Database()
    resultado = pipeline.ejecutar(
        Repository(db), etapas=("analisis",), db_path=db.path, progreso=print
    )
    return int(resultado["etapas"].get("analisis", {}).get("analizados", 0))


def run_ia_enrichment(on_log=None) -> dict:
    """Pase IA completo (compatibilidad). Devuelve el veredicto del pipeline."""
    db = Database()
    resultado = pipeline.ejecutar(
        Repository(db),
        etapas=("ia",),
        db_path=db.path,
        progreso=on_log or print,
    )
    etapa = resultado["etapas"].get("ia", {})
    return {
        "ok": bool(etapa.get("ok")),
        "estado": etapa.get("estado"),
        "motivo": etapa.get("motivo"),
        "avance": etapa.get("avance", {}),
        "stats_ia": etapa.get("stats_ia", {}),
    }


def run_full_flow(
    sites: list[str],
    pages: int = 1,
    notify_end: bool = True,
    evaluar_todo: bool = False,
) -> bool:
    """Ejecuta el flujo completo y devuelve ``True`` si todo salió bien."""
    db = Database()
    print("=" * 60)
    print("FLUJO COMPLETO (orquestador único jobpulse_v15.pipeline)")
    print("=" * 60)

    resultado = pipeline.ejecutar(
        Repository(db),
        etapas=ETAPAS_FLUJO_COMPLETO,
        sites=sites,
        pages=pages,
        evaluar_todo=evaluar_todo,
        db_path=db.path,
        progreso=print,
    )
    print("\n" + "=" * 60)
    print(pipeline.resumen_linea(resultado))
    for error in resultado["errores"]:
        print("  !! %s" % error)
    exito = bool(resultado["ok"])
    print("RESULTADO: %s" % ("✅ ÉXITO" if exito else "❌ CON PROBLEMAS"))

    scrape = resultado["etapas"].get("scrape", {})
    ia = resultado["etapas"].get("ia", {})
    if notify_end:
        titulo = "JobPulse: Flujo completado ✅" if exito else "JobPulse: Flujo con problemas ⚠️"
        notify(
            titulo,
            "Nuevas: %s | Errores: %s | IA: %s"
            % (scrape.get("jobs_new", 0), scrape.get("errores", 0), ia.get("estado")),
        )
    return exito


def main() -> int:
    parser = argparse.ArgumentParser(description="Flujo completo JobPulse con notificación")
    parser.add_argument("sites", nargs="*", help="Site IDs a procesar (default: todos activos)")
    parser.add_argument("--pages", type=int, default=1, help="Páginas por sitio (default del sitio manda)")
    parser.add_argument("--no-notify", action="store_true", help="No enviar notificación al final")
    parser.add_argument("--only-scrape", action="store_true", help="Solo scrape (sin análisis/IA)")
    parser.add_argument(
        "--evaluar-todo",
        action="store_true",
        help="Paso 5 sin filtro por área (evalúa todas las vacantes)",
    )
    args = parser.parse_args()

    if args.sites:
        sites = args.sites
    else:
        db = Database()
        sites = [s["site_id"] for s in Repository(db).list_sites(enabled_only=True)]

    if args.only_scrape:
        resultado = run_scrape(sites, pages=args.pages)
        return 0 if resultado["ok"] else 1
    exito = run_full_flow(
        sites,
        pages=args.pages,
        notify_end=not args.no_notify,
        evaluar_todo=args.evaluar_todo,
    )
    return 0 if exito else 1


if __name__ == "__main__":
    sys.exit(main())
