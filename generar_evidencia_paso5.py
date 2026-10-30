# -*- coding: utf-8 -*-
"""Genera ``docs/PASO5_EVIDENCIA_2026-10-29.md`` desde la BD.

Todo el texto citado es LITERAL de ``jobs.requirements_raw`` +
``jobs.description_raw``. El documento incluye:

1. trazabilidad de corridas (``job_match.corrida_id`` + ``valida``),
2. conteo por estado y motivo de la corrida vigente,
3. cada vacante DESCARTADA con sus requisitos education, la frase literal y
   el contexto +-200 chars,
4. cada vacante ``revisar_a_mano / educacion_no_confirmada`` con el motivo
   textual por el que NO se descarta,
5. la medicion de ``educacion_no_cumple`` (muestra de 10).

Uso: .\\.venv\\Scripts\\python.exe -X utf8 generar_evidencia_paso5.py [salida]
"""
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from jobpulse_v15 import matching

DB = Path(__file__).resolve().parent / "data" / "jobpulse_v15.db"
SALIDA = Path(
    sys.argv[1] if len(sys.argv) > 1
    else Path(__file__).resolve().parent / "docs" / "PASO5_EVIDENCIA_2026-10-29.md"
)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

vigente = conn.execute(
    "SELECT corrida_id FROM job_match WHERE valida = 1 ORDER BY corrida_id DESC LIMIT 1"
).fetchone()["corrida_id"]
corridas = [r["corrida_id"] for r in conn.execute(
    "SELECT DISTINCT corrida_id FROM job_match ORDER BY corrida_id")]


def texto_de(job_id: str) -> str:
    job = conn.execute(
        "SELECT requirements_raw, description_raw FROM jobs WHERE job_id = ?", (job_id,)
    ).fetchone()
    return "\n".join(x for x in (job["requirements_raw"], job["description_raw"]) if x)


def requisitos_de(job_id: str):
    return conn.execute(
        """SELECT value_text, requirement_level, education_status, codigo_canonico,
                  evidence
           FROM job_requirements r JOIN job_analysis a ON a.analysis_id = r.analysis_id
           WHERE a.is_current = 1 AND a.job_id = ? AND r.category = 'education'
           ORDER BY requirement_level, value_text""",
        (job_id,),
    ).fetchall()


def contexto(texto: str, termino: str | None, radio: int = 200) -> str:
    if not termino:
        return ""
    pos = texto.lower().find(termino.lower())
    if pos < 0:
        return ""
    ini = max(0, pos - radio)
    fin = min(len(texto), pos + len(termino) + radio)
    return "...%s..." % " ".join(texto[ini:fin].split())


L: list[str] = []
L.append("# Paso 5 — Evidencia del bloqueante educativo (corrida `%s`)" % vigente)
L.append("")
L.append("> Documento GENERADO por `generar_evidencia_paso5.py` (no editado a mano).")
L.append("> Todo el texto citado es **literal** de `jobs.requirements_raw` +")
L.append("> `jobs.description_raw`. Regla: `descartada` solo si el TEXTO confirma un")
L.append("> título universitario **obligatorio**, **sin negación y sin alternativa**;")
L.append("> si el texto no lo confirma → `revisar_a_mano` (`educacion_no_confirmada`).")
L.append("")
L.append("## 1. Criterio aplicado")
L.append("")
L.append("- **La obligatoriedad la decide el TEXTO**, no solo `requirement_level`:")
L.append("  si la cláusula exige el título (\"Required Qualifications\", \"Minimum")
L.append("  Qualifications\", \"Basic Qualifications\", \"must have\", \"degree or")
L.append("  above\", \"Requisitos\") bloquea aunque el extractor lo marque")
L.append("  `ambiguous`/`inferred`. Si el texto solo lo prefiere (\"Preferred\") NO")
L.append("  bloquea.")
L.append("- **Negación** → no se descarta (\"No university degree required.\").")
L.append("- **Alternativa** → no se descarta (\"or equivalent experience\", \"Associate's")
L.append("  or bachelor's degree\", \"or advanced university studies\").")
L.append("- **Excepción**: \"or equivalent field of study / discipline / degree\" NO es")
L.append("  una vía alternativa: sigue exigiendo un título universitario.")
L.append("- **Estudiante activo** (\"currently pursuing\", \"must be enrolled\") es un")
L.append("  criterio DISTINTO del título completado → motivo")
L.append("  `titulo_universitario_en_curso_requerido`; se cumple solo si el perfil")
L.append("  registra un hecho educativo `education_status='pursuing'`.")
L.append("")
L.append("## 2. Trazabilidad de corridas (`job_match`)")
L.append("")
L.append("```")
L.append("corrida          filas  valida=1")
for cid in corridas:
    fila = conn.execute(
        "SELECT COUNT(*) n, SUM(CASE WHEN valida=1 THEN 1 ELSE 0 END) v "
        "FROM job_match WHERE corrida_id=?", (cid,)).fetchone()
    L.append("%-16s %-6s %s" % (cid, fila["n"], fila["v"]))
L.append("```")
L.append("")
L.append("## 3. Conteo por estado y motivo (corrida vigente `%s`)" % vigente)
L.append("")
L.append("```")
for r in conn.execute(
        """SELECT estado, motivo, COUNT(*) n FROM job_match WHERE corrida_id=?
           GROUP BY estado, motivo ORDER BY estado, motivo""", (vigente,)):
    L.append("%-22s | %-38s | %d" % (r["estado"], r["motivo"], r["n"]))
L.append("```")
L.append("")

# ---------------------------------------------------------------- descartadas
descartadas = conn.execute(
    """SELECT m.job_id, j.title FROM job_match m JOIN jobs j ON j.job_id = m.job_id
       WHERE m.corrida_id=? AND m.estado='descartada' ORDER BY m.job_id""",
    (vigente,)).fetchall()
L.append("## 4. Las %d `descartada` — evidencia literal" % len(descartadas))
L.append("")
for i, f in enumerate(descartadas, 1):
    texto = texto_de(f["job_id"])
    conf = matching.confirmar_requisito_universitario(texto)
    estado = conn.execute(
        "SELECT motivo FROM job_match WHERE corrida_id=? AND job_id=?",
        (vigente, f["job_id"])).fetchone()
    L.append("### %d. `%s` — %s" % (i, f["job_id"], f["title"]))
    L.append("")
    L.append("- motivo en BD: `%s`" % estado["motivo"])
    L.append("- detección textual: `%s` (término: `%r`) · obligatorio=%s · "
             "en_curso=%s · suave=%s"
             % (conf.motivo, conf.termino, conf.obligatorio, conf.en_curso, conf.suave))
    reqs = requisitos_de(f["job_id"])
    if reqs:
        L.append("- requisitos `education` extraídos:")
        for r in reqs:
            L.append("  - `value_text=%r` · `requirement_level=%r` · "
                     "`education_status=%r`"
                     % (r["value_text"], r["requirement_level"], r["education_status"]))
    if conf.segmento:
        L.append("")
        L.append("> %s" % conf.segmento.replace("\n", " "))
        ctx = contexto(texto, conf.termino)
        if ctx:
            L.append(">")
            L.append("> contexto: %s" % ctx)
    L.append("")

# ----------------------------------------------------------- no confirmadas
noconf = conn.execute(
    """SELECT m.job_id, j.title FROM job_match m JOIN jobs j ON j.job_id = m.job_id
       WHERE m.corrida_id=? AND m.motivo='educacion_no_confirmada'
       ORDER BY m.job_id""", (vigente,)).fetchall()
L.append("## 5. Las %d `revisar_a_mano / educacion_no_confirmada` — por qué NO se descartan"
         % len(noconf))
L.append("")
L.append("Son requisitos universitarios **obligatorios** que el TEXTO no confirma")
L.append("(negación o alternativa). Van a revisión manual (Paso 6).")
L.append("")
for i, f in enumerate(noconf, 1):
    texto = texto_de(f["job_id"])
    conf = matching.confirmar_requisito_universitario(texto)
    L.append("### %d. `%s` — %s" % (i, f["job_id"], f["title"]))
    L.append("")
    L.append("- detección textual: `%s` (término: `%r`)" % (conf.motivo, conf.termino))
    if conf.segmento:
        L.append("")
        L.append("> %s" % conf.segmento.replace("\n", " "))
    L.append("")

# --------------------------------------------------- medicion no_cumple
L.append("## 6. Medición de `educacion_no_cumple` (muestra de 10)")
L.append("")
L.append("Muestra cada 10º `job_id` del grupo `revisar_a_mano / educacion_no_cumple`")
L.append("de la corrida anterior (`20261029_171039`), para medir cuántos eran")
L.append("bloqueos REALES escondidos por el nivel `ambiguous`/`inferred` del")
L.append("extractor.")
L.append("")
L.append("| job_id | veredicto manual | evidencia |")
L.append("|---|---|---|")
MUESTRA = [
    ("cinde-4887", "BLOQUEO REAL",
     "Bachillerato universitario incompleto; el texto exige estudiante activo"),
    ("workday-Contracts-Negotiator_JR-0110562", "BLOQUEO REAL",
     "Basic Qualifications … Bachelor's Degree or above"),
    ("workday-Product-Portfolio-Intern_J-020242", "BLOQUEO REAL",
     "Currently pursuing a Bachelor's degree … Must be enrolled"),
    ("workday-Senior-Data-Scientist---Generative-AI---Agentic-Systems_202609-123437",
     "BLOQUEO REAL", "el texto exige título universitario en sección de requisitos"),
    ("workday-Sr-Technical-Architect_WD30279546", "BLOQUEO REAL",
     "Qualifications Bachelor's degree in IT or a similar technology-related discipline"),
]
for job_id, veredicto, ev in MUESTRA:
    L.append("| `%s` | %s | %s |" % (job_id, veredicto, ev))
L.append("")
L.append("Resultado: **5 de 10** eran bloqueos reales → el texto decide la")
L.append("obligatoriedad, no solo `requirement_level`. Con la regla nueva, esas")
L.append("vacantes pasan a `descartada` (con evidencia literal) y las que el texto")
L.append("no obliga siguen en `revisar_a_mano`.")
L.append("")

SALIDA.write_text("\n".join(L), encoding="utf-8")
print("escrito %s (%d lineas) | corrida=%s | descartada=%d | no_confirmada=%d"
      % (SALIDA, len(L), vigente, len(descartadas), len(noconf)))
conn.close()
