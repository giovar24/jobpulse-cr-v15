# -*- coding: utf-8 -*-
"""Checkpoint de objetivos: estado medible del plan de mejores puestos.

SOLO LECTURA (abre la BD con mode=ro, no aplica migraciones). Mide el
estado base que usan los objetivos secundarios del plan
(`docs/PLAN_MEJORES_PUESTOS.md`) para que una sesión nueva sepa dónde
retomar.

Uso: python tools/checkpoint_objetivos.py [--db RUTA]
"""
import argparse
import sqlite3
import sys
from pathlib import Path

BD_DEFECTO = Path(__file__).resolve().parent.parent / "data" / "jobpulse_v15.db"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(BD_DEFECTO), help="Ruta de la BD")
    args = parser.parse_args()

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)

    def q(sql, *params):
        return con.execute(sql, params).fetchall()

    print("== Paso 5 (corrida valida) ==")
    print("corrida:", q("SELECT DISTINCT corrida_id FROM job_match WHERE valida=1"))
    for fila in q("SELECT estado, COUNT(*) FROM job_match WHERE valida=1 "
                  "GROUP BY estado ORDER BY 2 DESC"):
        print("   ", fila[0], "=", fila[1])

    print("== Perfil (facts por categoria: total / sin codigo_canonico) ==")
    for fila in q("SELECT category, COUNT(*), SUM(codigo_canonico IS NULL) "
                  "FROM candidate_profile_facts GROUP BY category ORDER BY category"):
        print("    ", fila[0], "=", fila[1], "sin_codigo =", fila[2])
    print("   areas:", q("SELECT COUNT(*) FROM candidate_profile_facts "
                         "WHERE category='area'")[0][0],
          "| licencias:", q("SELECT COUNT(*) FROM candidate_profile_facts "
                            "WHERE category='license'")[0][0])

    print("== Cobertura de skills (evaluables del corpus vs perfil) ==")
    perfil = {r[0] for r in q(
        "SELECT codigo_canonico FROM candidate_profile_facts "
        "WHERE category='skill' AND codigo_canonico IS NOT NULL")}
    corpus = [r for r in q(
        "SELECT r.codigo_canonico, COUNT(DISTINCT a.job_id) "
        "FROM job_requirements r JOIN job_analysis a ON a.analysis_id=r.analysis_id "
        "WHERE a.is_current=1 AND r.category='skill' "
        "AND r.requirement_level != 'preferred' AND r.codigo_canonico IS NOT NULL "
        "GROUP BY r.codigo_canonico")]
    ausentes = sorted(((c, n) for c, n in corpus if c not in perfil),
                      key=lambda x: -x[1])
    print("   evaluables:", len(corpus), "| en perfil:", len(perfil & {c for c, _ in corpus}),
          "| ausentes:", len(ausentes))
    print("   top 10 ausentes:", ", ".join(f"{c}({n})" for c, n in ausentes[:10]))

    print("== Corpus ==")
    print("   jobs:", q("SELECT COUNT(*) FROM jobs")[0][0])
    print("   vencidos:", q("SELECT COUNT(*) FROM jobs WHERE expires_at IS NOT NULL "
                            "AND date(expires_at) < date(?)", "now")[0][0])
    print("   sin ciudad:", q("SELECT COUNT(*) FROM jobs WHERE city IS NULL "
                              "OR TRIM(COALESCE(city,'')) = ''")[0][0])
    print("   loc sin normalizar:", q(
        "SELECT COUNT(*) FROM jobs WHERE TRIM(COALESCE(location_raw,'')) <> '' "
        "AND TRIM(COALESCE(city,'')) = '' AND TRIM(COALESCE(region,'')) = ''")[0][0])
    print("   postulaciones:", q("SELECT COUNT(*) FROM postulacion")[0][0])
    print("   cola concepto_no_normalizado:", q(
        "SELECT COUNT(*) FROM concepto_no_normalizado")[0][0])

    print("== Salud ==")
    print("   sites needs_review:", q("SELECT COUNT(*) FROM source_sites "
                                      "WHERE review_required=1")[0][0])
    con.close()
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
