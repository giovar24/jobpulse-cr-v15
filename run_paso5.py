# -*- coding: utf-8 -*-
"""Ejecuta el Paso 5 (matching) sobre la base de datos.

Cada corrida escribe filas NUEVAS en ``job_match`` y deja las anteriores con
``valida = 0`` (nunca se actualiza una corrida ya emitida).

Uso:
    .\\.venv\\Scripts\\python.exe -X utf8 run_paso5.py            # corrida nueva
    .\\.venv\\Scripts\\python.exe -X utf8 run_paso5.py --dry      # sin escribir
    .\\.venv\\Scripts\\python.exe -X utf8 run_paso5.py --corrida 20261029_171039
"""
import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from jobpulse_v15 import areas
from jobpulse_v15 import matching
from jobpulse_v15.db import Database


def main() -> int:
    parser = argparse.ArgumentParser(description="Paso 5: matching de requisitos vs perfil.")
    parser.add_argument("--dry", action="store_true",
                        help="Evalua sin escribir nada en la base de datos.")
    parser.add_argument("--corrida", help="Identificador de corrida (por defecto: timestamp).")
    parser.add_argument(
        "--evaluar-todo",
        action="store_true",
        help=(
            "Ignora el filtro por area de empleo y evalua TODAS las vacantes "
            "(por defecto solo se evaluan las de las areas marcadas en el perfil)."
        ),
    )
    args = parser.parse_args()

    db = Database()
    connection = sqlite3.connect(db.path)
    connection.row_factory = sqlite3.Row
    try:
        areas_perfil = sorted(areas.areas_del_perfil(connection))
        if args.dry:
            evaluador = matching.EvaluadorPaso5(
                connection, aplicar_filtro_areas=not args.evaluar_todo
            )
            resultados = [evaluador.evaluar_job(j) for j in evaluador.jobs_con_analisis]
            corrida = args.corrida or "(dry run: no se escribe)"
        else:
            corrida, resultados = matching.ejecutar_paso5(
                connection,
                args.corrida,
                aplicar_filtro_areas=not args.evaluar_todo,
            )
    finally:
        connection.close()

    print("corrida_id = %s" % corrida)
    print("vacantes evaluadas = %d" % len(resultados))
    if args.evaluar_todo:
        print("filtro por area = DESACTIVADO (evaluar todo)")
    elif areas_perfil:
        print("filtro por area = activo (%s)" % ", ".join(areas_perfil))
    else:
        print("filtro por area = sin areas marcadas en el perfil (se evalua todo)")
    print()
    print("=== estado x motivo ===")
    for (estado, motivo), n in sorted(Counter((r.estado, r.motivo) for r in resultados).items()):
        print("  %-22s | %-32s | %d" % (estado, motivo, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
