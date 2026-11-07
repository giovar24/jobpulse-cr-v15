"""Estado de la EXTRACCION DE CODIGO: que ve de verdad el motor del Paso 5.

Responde la pregunta que se mide al comparar una corrida antes/despues:

* cuantos requisitos VIGENTES hay y cuantos tienen ``codigo_canonico``
  (un requisito SIN codigo lo ignora el motor EN SILENCIO: la vacante se ve
  mas compatible de lo que es);
* cuantos avisos se quedan sin ningun requisito (``sin_requisitos``);
* como esta la cola de la taxonomia (``concepto_no_normalizado``);
* que campos estructurados (los que produce la IA) hay ya;
* como quedo el matching de la corrida vigente.

SOLO LECTURA: abre la BD en modo ``ro`` y NO aplica migraciones. Para medir
una mejora hay que ejecutarlo ANTES y DESPUES de la corrida y comparar los
dos JSON (ver ``comparar_extraccion.py``).

Uso:
    .\\.venv\\Scripts\\python.exe -X utf8 tools\\estado_extraccion.py [etiqueta] [salida.json]
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from jobpulse_v15.db import Database

ETIQUETA = sys.argv[1] if len(sys.argv) > 1 else "estado"
SALIDA = Path(sys.argv[2]) if len(sys.argv) > 2 else None

REQUISITOS_VIGENTES = """
  SELECT r.category, r.origin, r.codigo_canonico, r.value_text
  FROM job_requirements r
  JOIN job_analysis a ON a.analysis_id = r.analysis_id AND a.is_current = 1
"""

# Campos estructurados: como los cuenta el pase de IA.
CAMPOS = {
    "city": "COALESCE(TRIM(city),'')!=''",
    "region": "COALESCE(TRIM(region),'')!=''",
    "work_mode": "work_mode IS NOT NULL AND work_mode NOT IN ('','unknown')",
    "date_published": "COALESCE(TRIM(date_published),'')!=''",
    "employment_type": "COALESCE(TRIM(employment_type),'')!=''",
    "salary_min": "salary_min IS NOT NULL",
    "skills": "COALESCE(TRIM(skills),'') NOT IN ('','[]','{}','null')",
    "languages": "COALESCE(TRIM(languages),'') NOT IN ('','[]','{}','null')",
}


def main() -> int:
    ruta = Database().path
    con = sqlite3.connect("file:%s?mode=ro" % ruta.as_posix(), uri=True)
    con.row_factory = sqlite3.Row

    def uno(sql: str, params: tuple = ()) -> int:
        return con.execute(sql, params).fetchone()[0]

    try:
        total = uno("SELECT COUNT(*) FROM (" + REQUISITOS_VIGENTES + ")")
        con_codigo = uno(
            "SELECT COUNT(*) FROM (" + REQUISITOS_VIGENTES
            + ") WHERE codigo_canonico IS NOT NULL"
        )
        avisos = uno("SELECT COUNT(*) FROM jobs")

        por_categoria = {}
        for fila in con.execute(
            "SELECT category, COUNT(*) n, SUM(CASE WHEN codigo_canonico IS NOT NULL"
            " THEN 1 ELSE 0 END) con_codigo FROM (" + REQUISITOS_VIGENTES
            + ") GROUP BY category ORDER BY n DESC"
        ):
            por_categoria[fila["category"]] = {
                "total": fila["n"],
                "con_codigo": fila["con_codigo"],
                "sin_codigo": fila["n"] - fila["con_codigo"],
            }

        por_origen = {}
        for fila in con.execute(
            "SELECT origin, COUNT(*) n FROM (" + REQUISITOS_VIGENTES
            + ") GROUP BY origin ORDER BY n DESC"
        ):
            por_origen[fila["origin"] or "(null)"] = fila["n"]

        campos = {}
        for campo, expr in CAMPOS.items():
            llenos = uno("SELECT COUNT(*) FROM jobs WHERE " + expr)
            campos[campo] = {
                "llenos": llenos,
                "pendientes": avisos - llenos,
            }

        estados = {
            f["estado"]: f["n"]
            for f in con.execute(
                "SELECT estado, COUNT(*) n FROM job_match WHERE valida=1"
                " GROUP BY estado"
            )
        }

        estado = {
            "etiqueta": ETIQUETA,
            "avisos": avisos,
            "requisitos_vigentes": total,
            "requisitos_con_codigo": con_codigo,
            "requisitos_sin_codigo": total - con_codigo,
            "cobertura_codigo_pct": round(100.0 * con_codigo / total, 2) if total else 0.0,
            "variantes_distintas_con_codigo": uno(
                "SELECT COUNT(DISTINCT LOWER(TRIM(value_text))) FROM ("
                + REQUISITOS_VIGENTES + ") WHERE codigo_canonico IS NOT NULL"
            ),
            "codigos_distintos_usados": uno(
                "SELECT COUNT(DISTINCT codigo_canonico) FROM (" + REQUISITOS_VIGENTES
                + ") WHERE codigo_canonico IS NOT NULL"
            ),
            "conceptos_en_taxonomia": uno("SELECT COUNT(*) FROM concepto"),
            "cola_taxonomia": uno("SELECT COUNT(*) FROM concepto_no_normalizado"),
            "avisos_sin_ningun_requisito": uno(
                "SELECT COUNT(DISTINCT a.job_id) FROM job_analysis a"
                " WHERE a.is_current = 1 AND NOT EXISTS (SELECT 1 FROM job_requirements"
                " r WHERE r.analysis_id = a.analysis_id)"
            ),
            "por_categoria": por_categoria,
            "por_origen": por_origen,
            "campos": campos,
            "match_corrida": uno("SELECT DISTINCT corrida_id FROM job_match WHERE valida=1"),
            "match_estados": estados,
            "educacion_no_confirmada": uno(
                "SELECT COUNT(*) FROM job_match WHERE valida=1"
                " AND motivo='educacion_no_confirmada'"
            ),
        }
    finally:
        con.close()

    texto = json.dumps(estado, ensure_ascii=False, indent=2)
    print(texto)
    if SALIDA:
        SALIDA.write_text(texto, encoding="utf-8")
        print("guardado en", SALIDA)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
