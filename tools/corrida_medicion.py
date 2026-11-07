"""Corre el pipeline REAL sobre el corpus que YA esta en la BD (sin scrape).

Es la forma de MEDIR el efecto de una etapa (pase IA, curacion, re-barrido)
sin que entre nada nuevo: el corpus se queda como esta y solo se mide lo que
cambia en el matching. El orquestador es el MISMO que usan la CLI
(``run_full_flow.py``) y la UI v2 (boton "Procesar"), asi que lo que se mide
aquí es exactamente lo que medirian ellas.

Sin argumentos corre: ``analisis -> ia -> reanalisis -> backfill -> paso5 ->
evidencia``. Con ``--sin-ia`` quita la etapa de IA (la que tarda ~10 min con
el modelo local).

AVISO: escribe en la BD (Paso 5 = corrida NUEVA en ``job_match``). HAZ UN
RESPALDO antes (``-m jobpulse_v15 backup --output data\\backups\\X.db``).

Uso:
    .\\.venv\\Scripts\\python.exe -X utf8 tools\\corrida_medicion.py [--sin-ia]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from jobpulse_v15 import pipeline  # noqa: E402
from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402

ETAPAS = ("analisis", "ia", "reanalisis", "backfill", "paso5", "evidencia")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sin-ia", action="store_true",
                    help="omite la etapa de IA (la lenta)")
    ap.add_argument("--db", default=None, help="ruta de la BD (por defecto: la real)")
    args = ap.parse_args()

    bd = Path(args.db) if args.db else Database().path
    etapas = tuple(e for e in ETAPAS if e != "ia") if args.sin_ia else ETAPAS

    def log(texto: str) -> None:
        print("%s | %s" % (time.strftime("%H:%M:%S"), texto), flush=True)

    db = Database(bd)
    repo = Repository(db)
    log("=== INICIO corrida (corpus actual: %s) ===" % bd)
    resultado = pipeline.ejecutar(
        repo, etapas=etapas, db_path=bd, progreso=log
    )
    log("=== FIN ===")
    log("corrida_pipeline = %s" % resultado.get("corrida_pipeline"))
    log("corrida_paso5    = %s" % resultado.get("corrida"))
    log("ok               = %s" % resultado.get("ok"))
    log("errores          = %s" % resultado.get("errores"))
    log("resumen: %s" % pipeline.resumen_linea(resultado))
    return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
