# -*- coding: utf-8 -*-
"""Resumen del analisis de bloqueo educativo de la corrida vigente.

Tres cortes:

A) Las vacantes DESCARTADAS y por que motivo (titulo completado vs. estudiante
   activo).
B) Las vacantes con requisito universitario ``requirement_level='required'``:
   que dice el TEXTO (confirmado / alternativa / negacion / sin termino).
C) Las vacantes donde el TEXTO obliga pero el extractor NO marco 'required'
   (la regla nueva las promotes a 'descartada').

Uso: .\\.venv\\Scripts\\python.exe -X utf8 resumen_bloqueo.py [salida]
"""
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from jobpulse_v15 import matching

SALIDA = Path(sys.argv[1] if len(sys.argv) > 1 else "out_bloqueo.txt")

conn = sqlite3.connect("data/jobpulse_v15.db")
conn.row_factory = sqlite3.Row

corrida = conn.execute(
    "SELECT corrida_id FROM job_match WHERE valida = 1 ORDER BY corrida_id DESC LIMIT 1"
).fetchone()["corrida_id"]

L: list[str] = []
L.append("corrida vigente = %s" % corrida)
L.append("=" * 100)

# --------------------------------------------------------------- A) descartadas
L.append("A) DESCARTADAS: estado y motivo en la BD")
L.append("-" * 100)
conteo = Counter()
for r in conn.execute(
    """SELECT m.job_id, m.motivo, j.title FROM job_match m JOIN jobs j ON j.job_id=m.job_id
       WHERE m.corrida_id=? AND m.estado='descartada' ORDER BY m.job_id""", (corrida,)):
    conteo[r["motivo"]] += 1
    L.append("   %-64s %-40s %s" % (r["job_id"][:64], r["motivo"], r["title"][:40]))
L.append("   TOTAL descartada = %d" % sum(conteo.values()))
for motivo, n in sorted(conteo.items()):
    L.append("      %-40s %d" % (motivo, n))
L.append("")

# ------------------------------------------------- B) required segun extractor
L.append("B) Requisito universitario con requirement_level='required' (52):")
L.append("   que dice el TEXTO")
L.append("-" * 100)
conteo_b = Counter()
for r in conn.execute(
    """SELECT DISTINCT a.job_id, j.title, j.requirements_raw, j.description_raw
       FROM job_requirements r JOIN job_analysis a ON a.analysis_id = r.analysis_id
       JOIN jobs j ON j.job_id = a.job_id
       WHERE a.is_current = 1 AND r.category='education'
         AND r.requirement_level='required'
         AND r.codigo_canonico IN ('educacion-universitaria','educacion-posgrado')
       ORDER BY a.job_id"""
):
    texto = "\n".join(x for x in (r["requirements_raw"], r["description_raw"]) if x)
    conf = matching.confirmar_requisito_universitario(texto)
    estado = conn.execute(
        "SELECT estado, motivo FROM job_match WHERE corrida_id=? AND job_id=?",
        (corrida, r["job_id"])).fetchone()
    conteo_b[(estado["estado"], conf.motivo)] += 1
    L.append("   %-64s %-18s %-14s %s"
             % (r["job_id"][:64], estado["estado"], conf.motivo, r["title"][:36]))
    if conf.segmento:
        L.append("        frase: %s" % conf.segmento[:240])
L.append("   TOTAL = %d" % sum(conteo_b.values()))
for clave, n in sorted(conteo_b.items()):
    L.append("      %-20s %-14s %d" % (clave[0], clave[1], n))
L.append("")

# --------------------------------- C) texto obliga pero el extractor no marco
L.append("C) El TEXTO obliga pero requirement_level != 'required' (regla nueva):")
L.append("-" * 100)
n_c = 0
for r in conn.execute(
    """SELECT m.job_id, m.motivo, j.title, j.requirements_raw, j.description_raw
       FROM job_match m JOIN jobs j ON j.job_id=m.job_id
       WHERE m.corrida_id=? AND m.estado='descartada'
         AND NOT EXISTS (SELECT 1 FROM job_requirements q
                         JOIN job_analysis a ON a.analysis_id=q.analysis_id
                         WHERE a.is_current=1 AND a.job_id=m.job_id
                           AND q.category='education' AND q.requirement_level='required')
       ORDER BY m.job_id""", (corrida,)
):
    texto = "\n".join(x for x in (r["requirements_raw"], r["description_raw"]) if x)
    conf = matching.confirmar_requisito_universitario(texto)
    n_c += 1
    L.append("   %-64s %-40s" % (r["job_id"][:64], r["motivo"]))
    L.append("        texto: obligatorio=%s en_curso=%s | %s"
             % (conf.obligatorio, conf.en_curso, conf.segmento or "-"))
L.append("   TOTAL = %d" % n_c)

SALIDA.write_text("\n".join(L), encoding="utf-8")
print("corrida=%s | archivo=%s | descartada=%d | required_no_texto=%d"
      % (corrida, SALIDA, sum(conteo.values()), n_c))
conn.close()
