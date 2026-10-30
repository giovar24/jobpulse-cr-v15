# -*- coding: utf-8 -*-
"""Genera ``docs/PASO5_REVISION_PENDIENTES.md``: hoja de revision para una
SEGUNDA persona.

REGLAS DEL DOCUMENTO (acordadas 2026-10-29):

1. NO registra veredictos ni conclusión alguna: solo TEXTOS LITERALES de la BD.
2. El conjunto lo compone la corrida vigente (los ``revisar_a_mano /
   educacion_no_confirmada``), pero el veredicto lo firma alguien que NO haya
   escrito la regla (la revisión previa la hizo el autor -> descartada por
   sesgo).
3. Cada caso trae TODAS las menciones educativas del texto con contexto
   +-350 chars, y la evidencia literal del requisito extraído.

Uso: .\\.venv\\Scripts\\python.exe -X utf8 generar_revision_pendientes.py
"""
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))
from jobpulse_v15 import matching  # solo segmentar; NO clasifica

DOC = REPO / "docs" / "PASO5_REVISION_PENDIENTES.md"
DB = REPO / "data" / "jobpulse_v15.db"

# Terminos educativos para extraer TODAS las menciones (sin clasificar).
VENTANA = 350
TERMINOS = re.compile(
    r"bachelor|master|licenciatura|licenciad[oa]|university|college"
    r"|associate|t[íi]tulo\s+universitario|estudios\s+universitarios"
    r"|bachillerat?o?\b|diploma\b|degree\b|grado\b",
    re.IGNORECASE,
)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
vigente = conn.execute(
    "SELECT corrida_id FROM job_match WHERE valida=1 ORDER BY corrida_id DESC LIMIT 1"
).fetchone()["corrida_id"]

casos = [r["job_id"] for r in conn.execute(
    "SELECT job_id FROM job_match WHERE corrida_id=? AND motivo='educacion_no_confirmada' "
    "ORDER BY job_id", (vigente,))]

L: list[str] = []
L.append("# Paso 5 — HOJA DE REVISIÓN PENDIENTE (corrida `%s`)" % vigente)
L.append("")
L.append("> Documento GENERADO por `generar_revision_pendientes.py` — contiene")
L.append("> **solo textos literales de la BD, sin ningún veredicto**.")
L.append("> Estado de estos casos: **ABIERTOS / NO REVISADOS**.")
L.append("")
L.append("## Para quién es este documento")
L.append("")
L.append("La revisión previa de estos casos la hizo **el autor de la regla**, por eso")
L.append("su veredicto (\"ninguna bloquea\") se **descarta**: no es una segunda opinión.")
L.append("Antes de registrar cualquier decisión en la tabla de decisiones del Paso 7")
L.append("(`job_match_decision`), alguien distinto del autor debe leer cada caso aquí")
L.append("con el texto completo y firmar un veredicto propio.")
L.append("")
L.append("## Decisiones de negocio que la revisión necesita (FALTA DECIDIR)")
L.append("")
L.append("Estas preguntas NO están decididas; el veredicto de los casos afectados")
L.append("depende de ellas y hay que decidirlas **con una fuente**, no por impulso:")
L.append("")
L.append("1. **\"or advanced university studies\"** (aparece en")
L.append("   `workday-Accounting-Analyst---Temporary_J-020392`): ¿los estudios")
L.append("   universitarios avanzados SIN título completado cuentan como educación")
L.append("   universitaria para este perfil? Es una alternativa ACADÉMICA, no")
L.append("   experiencia laboral.")
L.append("2. **\"two year college degree\" / \"associate degree\"** (aparece en")
L.append("   `workday-Associate--Repair-III_R-118081`): el código trata 2 años como NO")
L.append("   universitario. ¿Es correcto en CR? Un **técnico superior universitario**")
L.append("   sí es educación terciaria/universitaria — hay que decidirlo con fuente")
L.append("   (p. ej. títulos registrados en CONESUP).")
L.append("3. **\"80% completeness of a bachelor's degree program\"** (aparece en los dos")
L.append("   `workday-Production-Supervisor-I_*`): ¿un bachillerato PARCIAL (80 % de")
L.append("   la carrera) cuenta como requisito universitario cumplido? A día de hoy")
L.append("   el módulo NO define qué pasa con estudios parciales.")
L.append("")
L.append("## Casos a revisar (%d)" % len(casos))
L.append("")
L.append("Columnas de la tabla de firmas: `veredicto` (bloqueo real / no bloqueo /")
L.append("dudoso), `criterio que lo justifica`, `revisor`, `fecha`.")
L.append("")
for i, job_id in enumerate(casos, 1):
    fila = conn.execute(
        "SELECT title, requirements_raw, description_raw FROM jobs WHERE job_id=?",
        (job_id,)).fetchone()
    texto = "\n".join(x for x in (fila["requirements_raw"], fila["description_raw"]) if x)
    L.append("### %d. `%s` — %s" % (i, job_id, fila["title"]))
    L.append("")
    L.append("| veredicto | criterio | revisor | fecha |")
    L.append("|---|---|---|---|")
    L.append("|   |   |   |   |")
    L.append("")
    # TODAS las menciones educativas con contexto +-350 (sin clasificar).
    vistas: list[tuple[int, int]] = []
    for m in TERMINOS.finditer(texto):
        ini, fin = max(0, m.start() - VENTANA), min(len(texto), m.end() + VENTANA)
        # fusionar ventanas que se solapan
        if vistas and ini <= vistas[-1][1]:
            vistas[-1] = (vistas[-1][0], fin)
        else:
            vistas.append((ini, fin))
    for k, (ini, fin) in enumerate(vistas, 1):
        L.append("**Texto %d (verbatim):**" % k)
        L.append("")
        L.append("> %s" % " ".join(texto[ini:fin].split()))
        L.append("")
    # evidencia literal del requisito extraido (hecho, no conclusion)
    evs = conn.execute(
        """SELECT r.value_text, r.requirement_level, r.evidence
           FROM job_requirements r JOIN job_analysis a ON a.analysis_id = r.analysis_id
           WHERE a.is_current = 1 AND a.job_id = ? AND r.category = 'education'
           ORDER BY r.value_text""", (job_id,)).fetchall()
    if evs:
        L.append("**Requisito(s) `education` extraído(s) por el extractor** — la")
        L.append("citas son literales del texto de la oferta:")
        L.append("")
        for e in evs:
            L.append("- `value_text=%r` · `requirement_level=%r` · evidencia: > %s"
                     % (e["value_text"], e["requirement_level"],
                        str(e["evidence"]).replace("\n", " ")))
        L.append("")
    L.append("---")
    L.append("")

DOC.write_text("\n".join(L), encoding="utf-8")
print("escrito %s (%d lineas) | corrida=%s | casos=%d" % (DOC, len(L), vigente, len(casos)))
conn.close()
