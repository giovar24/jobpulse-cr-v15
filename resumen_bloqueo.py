# -*- coding: utf-8 -*-
"""Resumen del analisis de bloqueo educativo de la corrida vigente.

Para cada vacante con un requisito educativo universitario OBLIGATORIO
(requirement_level='required'), muestra el estado final y el motivo de la
deteccion textual (confirmado / negacion / alternativa / sin_termino).
"""
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from jobpulse_v15 import matching

conn = sqlite3.connect("data/jobpulse_v15.db")
conn.row_factory = sqlite3.Row

corrida = conn.execute(
    "SELECT corrida_id FROM job_match WHERE valida = 1 ORDER BY corrida_id DESC LIMIT 1"
).fetchone()["corrida_id"]

lineas: list[str] = []
lineas.append("corrida vigente = %s" % corrida)
lineas.append("=" * 100)
lineas.append("requisitos educativo universitarios OBLIGATORIOS (required) y su veredicto")
lineas.append("=" * 100)

conteo = Counter()
filas = conn.execute(
    """SELECT DISTINCT j.job_id, j.title, j.requirements_raw, j.description_raw
       FROM job_requirements r
       JOIN job_analysis a ON a.analysis_id = r.analysis_id
       JOIN jobs j ON j.job_id = a.job_id
       WHERE a.is_current = 1 AND r.category = 'education'
         AND r.requirement_level = 'required'
         AND r.codigo_canonico IN ('educacion-universitaria', 'educacion-posgrado')
       ORDER BY j.job_id"""
).fetchall()

for f in filas:
    texto = "\n".join(x for x in (f["requirements_raw"], f["description_raw"]) if x)
    conf = matching.confirmar_requisito_universitario(texto)
    estado = conn.execute(
        "SELECT estado, motivo FROM job_match WHERE corrida_id = ? AND job_id = ?",
        (corrida, f["job_id"]),
    ).fetchone()
    conteo[(estado["estado"], conf.motivo)] += 1
    lineas.append("")
    lineas.append("%s" % f["job_id"])
    lineas.append("    titulo : %s" % f["title"])
    lineas.append("    estado : %-18s motivo_bd : %s" % (estado["estado"], estado["motivo"]))
    lineas.append("    deteccion textual: %s (termino=%r)" % (conf.motivo, conf.termino))
    if conf.segmento:
        lineas.append("    frase  : %s" % conf.segmento[:260])

lineas.append("")
lineas.append("=" * 100)
lineas.append("RESUMEN (estado, deteccion) -> n")
for clave, n in sorted(conteo.items()):
    lineas.append("  %-20s %-14s %d" % (clave[0], clave[1], n))
lineas.append("  TOTAL requisitos university required: %d" % len(filas))

Path("out_bloqueo.txt").write_text("\n".join(lineas), encoding="utf-8")
print("corrida=%s | vacantes con req university required=%d | archivo=out_bloqueo.txt"
      % (corrida, len(filas)))
for clave, n in sorted(conteo.items()):
    print("  %-20s %-14s %d" % (clave[0], clave[1], n))
conn.close()
