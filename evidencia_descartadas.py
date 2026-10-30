# -*- coding: utf-8 -*-
"""Evidencia literal del paso 5 (archivo UTF-8, sin mojibake).

Por cada vacante DESCARTADA de la corrida indicada:
  - los requisitos education que bloquean (value_text, requirement_level,
    education_status),
  - la FRASE EXACTA que confirma el titulo universitario,
  - el CONTEXTO +-200 chars alrededor del termino,
  - la clasificacion textual: confirmado / negacion / alternativa,
    obligatorio, en_curso (estudiante activo), suave (preferred).

Uso: evidencia_descartadas.py [corrida_id] [archivo_salida]
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from jobpulse_v15 import matching

corrida = sys.argv[1] if len(sys.argv) > 1 else None
salida = Path(sys.argv[2] if len(sys.argv) > 2 else "out_evidencia.txt")

conn = sqlite3.connect("data/jobpulse_v15.db")
conn.row_factory = sqlite3.Row

if corrida is None:
    corrida = conn.execute(
        "SELECT corrida_id FROM job_match WHERE valida = 1 ORDER BY corrida_id DESC LIMIT 1"
    ).fetchone()["corrida_id"]

lineas: list[str] = []
lineas.append("corrida = %s" % corrida)
lineas.append("=" * 100)

jobs = [r["job_id"] for r in conn.execute(
    """SELECT job_id FROM job_match WHERE corrida_id = ? AND estado = 'descartada'
       ORDER BY job_id""",
    (corrida,),
)]
lineas.append("vacantes descartada = %d" % len(jobs))
lineas.append("=" * 100)

for i, job_id in enumerate(jobs, 1):
    job = conn.execute(
        "SELECT title, requirements_raw, description_raw FROM jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    texto = "\n".join(x for x in (job["requirements_raw"], job["description_raw"]) if x)
    conf = matching.confirmar_requisito_universitario(texto)

    estado = conn.execute(
        "SELECT estado, motivo FROM job_match WHERE corrida_id = ? AND job_id = ?",
        (corrida, job_id),
    ).fetchone()

    requisitos = conn.execute(
        """SELECT value_code, value_text, requirement_level, codigo_canonico,
                  education_status, evidence
           FROM job_requirements r JOIN job_analysis a ON a.analysis_id = r.analysis_id
           WHERE a.is_current = 1 AND a.job_id = ? AND r.category = 'education'
           ORDER BY requirement_level, value_text""",
        (job_id,),
    ).fetchall()

    lineas.append("")
    lineas.append("[%d] %s" % (i, job_id))
    lineas.append("    titulo: %s" % job["title"])
    lineas.append("    estado=%r motivo=%r" % (estado["estado"], estado["motivo"]))
    lineas.append("    requisitos education (level, education_status):")
    for r in requisitos:
        lineas.append("      - value_text=%r | level=%r | education_status=%r | canon=%r" % (
            r["value_text"], r["requirement_level"], r["education_status"],
            r["codigo_canonico"]))
    lineas.append(
        "    deteccion: motivo=%r termino=%r | obligatorio=%s en_curso=%s suave=%s"
        % (conf.motivo, conf.termino, conf.obligatorio, conf.en_curso, conf.suave))
    if conf.segmento:
        lineas.append("    FRASE EXACTA: %s" % conf.segmento)
        low = texto.lower()
        pos = low.find(conf.termino.lower()) if conf.termino else -1
        if pos >= 0:
            ini = max(0, pos - 200)
            fin = min(len(texto), pos + len(conf.termino) + 200)
            lineas.append("    CONTEXTO(+-200): ...%s..." % " ".join(texto[ini:fin].split()))

salida.write_text("\n".join(lineas), encoding="utf-8")
print("corrida = %s | descartada = %d | archivo = %s | lineas = %d"
      % (corrida, len(jobs), salida, len(lineas)))
conn.close()
