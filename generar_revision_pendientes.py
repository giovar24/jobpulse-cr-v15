# -*- coding: utf-8 -*-
"""Genera ``docs/PASO5_REVISION_PENDIENTES.md``: hoja de revision para una
SEGUNDA persona.

REGLAS DEL DOCUMENTO (acordadas 2026-10-29):

1. El TEXTO que se muestra es LITERAL de la BD (sin interpretación).
2. El conjunto lo compone la corrida vigente (los ``revisar_a_mano /
   educacion_no_confirmada``): lo que el motor NO pudo decidir.
3. Cada caso trae TODAS las menciones educativas del texto con contexto
   +-350 chars, y la evidencia literal del requisito extraído.
4. Si el caso ya tiene una FIRMA en la tabla de decisiones del Paso 7
   (``job_match_decision``), la hoja la muestra (veredicto, criterio,
   revisor, fecha): la firma NO se borra, pero el caso sigue ABIERTO si el
   veredicto fue "dudoso" (falta una decisión de negocio).

Uso: .\\.venv\\Scripts\\python.exe -X utf8 generar_revision_pendientes.py
"""
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))
from jobpulse_v15 import decisiones  # texto/ancla de la firma
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

# Firmas registradas (tabla del Paso 7). Si la tabla aun no existe (base
# anterior a la migracion 027), no hay firmas que mostrar.
try:
    firmas = {
        r["job_id"]: dict(r)
        for r in conn.execute(
            """SELECT job_id, dimension, veredicto, criterio, revisor, fecha, text_hash
               FROM job_match_decision WHERE dimension='educacion'"""
        )
    }
except sqlite3.OperationalError:
    firmas = {}

# Texto (y hash) de cada caso abierto: el texto es el que se ancla en la firma.
textos: dict[str, str] = {}
for job_id in casos:
    fila = conn.execute(
        "SELECT requirements_raw, description_raw FROM jobs WHERE job_id=?",
        (job_id,)).fetchone()
    textos[job_id] = decisiones.texto_aviso(
        fila["requirements_raw"], fila["description_raw"]
    )

# Solo cuentan las firmas que aplican al texto ACTUAL del aviso.
firmas_vigentes = {
    job_id: firma
    for job_id, firma in firmas.items()
    if job_id in textos
    and firma["text_hash"] == decisiones.hash_texto(textos[job_id])
}

L: list[str] = []
L.append("# Paso 5 — HOJA DE REVISIÓN PENDIENTE (corrida `%s`)" % vigente)
L.append("")
L.append("> Documento GENERADO por `generar_revision_pendientes.py` — los textos")
L.append("> son **literales de la BD**; el veredicto es el de la **segunda")
L.append("> persona** que firmó la tabla de decisiones del Paso 7")
L.append("> (`job_match_decision`).")
L.append("> Estado de estos casos: **ABIERTOS** (el motor no pudo decidirlos).")
L.append("")
L.append("## Para quién es este documento")
L.append("")
L.append("Esta hoja lista los casos que el MOTOR no pudo decidir (quedan en")
L.append("`revisar_a_mano / educacion_no_confirmada`). La revisión previa de estos")
L.append("casos la hizo **el autor de la regla**, por eso su veredicto (\"ninguna")
L.append("bloquea\") se **descarta**: no es una segunda opinión.")
L.append("")
L.append("Quien firma lo registra en la tabla `job_match_decision` (Paso 7), que")
L.append("queda anclada al **sha256 del texto exacto que leyó**: si el aviso se vuelve")
L.append("a raspar y su texto cambia, la firma deja de aplicar y el caso vuelve a")
L.append("esta hoja. Un veredicto \"dudoso\" NO cierra el caso: sigue abierto hasta")
L.append("que se decida la cuestión de NEGOCIO que lo bloquea (con una fuente).")
L.append("")
L.append("## Estado de la revisión")
L.append("")
firmadas = [j for j in casos if j in firmas_vigentes]
dudosas = [j for j in firmadas if firmas_vigentes[j]["veredicto"] == decisiones.VEREDICTO_DUDOSO]
L.append("| casos abiertos | con firma | firmados \"dudoso\" (siguen abiertos) | sin firma |")
L.append("|---|---|---|---|")
L.append("| %d | %d | %d | %d |"
         % (len(casos), len(firmadas), len(dudosas), len(casos) - len(firmadas)))
L.append("")
if dudosas:
    L.append("### Decisiones de NEGOCIO que siguen pendientes")
    L.append("")
    L.append("Estos casos tienen firma, pero el veredicto es **\"dudoso\"**: dependen")
    L.append("de una decisión de negocio que todavía NO está tomada (hay que")
    L.append("decidirla **con una fuente**, no por impulso).")
    L.append("")
    for job_id in dudosas:
        fila = conn.execute("SELECT title FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        L.append("- `%s` — %s: %s"
                 % (job_id, fila["title"], firmas_vigentes[job_id]["criterio"]))
    L.append("")
L.append("## Casos a revisar (%d)" % len(casos))
L.append("")
L.append("Columnas de la tabla de firmas: `veredicto` (bloqueo real / no bloqueo /")
L.append("dudoso), `criterio que lo justifica`, `revisor`, `fecha`.")
L.append("")
for i, job_id in enumerate(casos, 1):
    fila = conn.execute("SELECT title FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    texto = textos[job_id]
    L.append("### %d. `%s` — %s" % (i, job_id, fila["title"]))
    L.append("")
    L.append("| veredicto | criterio | revisor | fecha |")
    L.append("|---|---|---|---|")
    firma = firmas_vigentes.get(job_id)
    if firma:
        L.append("| %s | %s | %s | %s |"
                 % (firma["veredicto"], firma["criterio"], firma["revisor"], firma["fecha"]))
    else:
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
print("escrito %s (%d lineas) | corrida=%s | casos=%d | firmados=%d"
      % (DOC, len(L), vigente, len(casos), len(firmadas)))
conn.close()
