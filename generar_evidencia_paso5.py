# -*- coding: utf-8 -*-
"""Genera ``docs/PASO5_EVIDENCIA_2026-10-29.md`` desde la BD.

Todo el texto citado es LITERAL de ``jobs.requirements_raw`` +
``jobs.description_raw``. El documento incluye:

1. el criterio aplicado (incluida la semantica de ``education_status``),
2. trazabilidad de corridas (``job_match.corrida_id`` + ``valida``),
3. conteo por estado y motivo de la corrida vigente,
4. cada vacante DESCARTADA con sus requisitos education, la frase literal y
   el contexto +-200 chars,
5. cada vacante ``revisar_a_mano / educacion_no_confirmada`` con el motivo
   textual por el que NO se descarta,
6. la MEDICION AMPLIADA de ``educacion_no_cumple`` (43 casos revisados a
   mano: estrato A = las 13 promovidas, estrato B = 30 sistematicas).

Uso: .\\.venv\\Scripts\\python.exe -X utf8 generar_evidencia_paso5.py [salida]
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from jobpulse_v15 import matching

DB = Path(__file__).resolve().parent / "data" / "jobpulse_v15.db"
SALIDA = Path(
    sys.argv[1] if len(sys.argv) > 1
    else Path(__file__).resolve().parent / "docs" / "PASO5_EVIDENCIA_2026-10-29.md"
)

# ---------------------------------------------------------------------------
# Medicion ampliada del grupo 'educacion_no_cumple' (corrida 20261029_171039).
# Veredicto manual: BLOQUEO = el TEXTO exige un titulo universitario.
# ---------------------------------------------------------------------------
MEDICION = [
    # (estrato, job_id, veredicto manual, por que)
    ("A1", "cinde-4901", "BLOQUEO", "ESSENCIAL QUALIFICATIONS + Bachelor's degree"),
    ("A2", "workday-Accounts-Payable-Representative_J-020440", "NO BLOQUEO",
     "via alternativa: 'alternatively, 3+ years of relevant professional experience'"),
    ("A3", "workday-Business-Analyst--Contract-Pricing-and-Accuracy_R265403",
     "BLOQUEO", "QUALIFICATIONS AND SKILLS + Bachelor's degree"),
    ("A4", "workday-Continuous-Improvement-Intern_J-020427", "BLOQUEO",
     "estudiante activo: 'Currently pursuing a Bachelor's'"),
    ("A5", "workday-Contract-Administrator--Internship-_1213007", "BLOQUEO",
     "estudiante activo: 'University students actively enrolled'"),
    ("A6", "workday-Contracts-Negotiator_JR-0110562", "BLOQUEO",
     "Basic Qualifications + Bachelor's Degree or above"),
    ("A7", "workday-Director--Corporate-Accounting_JR-0111126", "BLOQUEO",
     "Required Qualifications: Bachelor's degree ... required"),
    ("A8", "workday-Product-Portfolio-Intern_J-020242", "BLOQUEO",
     "estudiante activo: 'Must be enrolled as a full-time student'"),
    ("A9", "workday-Senior-Analyst--Finance--Internal-Auditor-_Req-51202-1",
     "BLOQUEO", "What you'll need (Required): Bachelor's Degree ... is required"),
    ("A10", "workday-Senior-Director--Quality-Engineering_Req-50066", "BLOQUEO",
     "What you'll need (Required): Bachelor's Degree"),
    ("A11", "workday-Service-Delivery-Manager_R77891-2", "BLOQUEO",
     "Qualifications Required Qualifications Bachelor's degree"),
    ("A12", "workday-Sr-Technical-Architect_WD30279546", "BLOQUEO",
     "Qualifications + Bachelor's degree"),
    ("A13", "workday-Tax-Audit-Senior-Specialist_888004-1", "BLOQUEO",
     "To succeed in this role, you will need the following qualifications:"),
    ("B1", "cinde-4887", "BLOQUEO",
     "estudiante activo: 'Bachillerato universitario incompleto'"),
    ("B2", "cinde-4892", "BLOQUEO",
     "Job Requirements: Active university student + Currently pursuing"),
    ("B3", "cinde-4898", "BLOQUEO", "Formacion: Licenciatura"),
    ("B4", "workable-valatam-A30B8CD1CD", "NO BLOQUEO",
     "'Bachelor's or Associate's degree preferred'"),
    ("B5", "workday-Analista-de-CPFR_887589", "BLOQUEO",
     "Licenciatura o bachillerato universitario (ambos son=title universit.)"),
    ("B6", "workday-Applications-Support-Sr-Analyst_26963530", "NO BLOQUEO",
     "or equivalent experience"),
    ("B7", "workday-Audience-Management_26999789", "NO BLOQUEO",
     "or equivalent experience"),
    ("B8", "workday-Commercial-Support-Specialist_202609-124777", "NO BLOQUEO",
     "'Bachelor's or Master's degree preferred'"),
    ("B9", "workday-Content-Review-Operations-Specialist_202610-127168", "NO BLOQUEO",
     "or equivalent experience"),
    ("B10", "workday-Data-Governance-Foundation-Lead-Analyst_26983548", "BLOQUEO",
     "Education: Bachelor's/University degree (el 'preferred' es del Master's)"),
    ("B11", "workday-Datacenter-Engineer--L3-ERT_1212933-2", "NO BLOQUEO",
     "or equivalent (sin calificar) -> conservador"),
    ("B12", "workday-Digital-Campaign-Delivery-Associate_202609-122817", "BLOQUEO",
     "Further requirements + Bachelor's degree"),
    ("B13", "workday-Director--Manufacturing-Engineering_REQ-2026-18566", "BLOQUEO",
     "Education & Experience + discipline required"),
    ("B14", "workday-Document-Control-Intern_1210991", "BLOQUEO",
     "estudiante activo: 'pursuing diplomas or degrees'"),
    ("B15", "workday-Escalation-Engineer_1212930-2", "BLOQUEO",
     "What you need to bring: + Bachelor's degree"),
    ("B16", "workday-HR-Generalist-Senior---Global-Discipline-Delivery_261004191",
     "NO BLOQUEO", "or equivalent experience"),
    ("B17", "workday-Ingeniero-Principal-de-OpEx_20188241", "NO BLOQUEO",
     "preferred Bachelor's degree / or equivalent work experience"),
    ("B18", "workday-Intern---Bachelors-Tech_1214077", "BLOQUEO",
     "estudiante activo: 'actively enrolled ... pursuing a Bachelor's degree'"),
    ("B19", "workday-Lead-Mobile-Application-Engineer--NET-MAUI-_R18405", "NO BLOQUEO",
     "or equivalent practical experience"),
    ("B20", "workday-Network-Support-Engineer_1211197", "NO BLOQUEO",
     "or equivalent"),
    ("B21", "workday-Principal-Engineer--Quality_Req-51750", "NO BLOQUEO",
     "or equivalent"),
    ("B22", "workday-Programmatic-Media-Associate---Citi-Commerce_261002988", "NO BLOQUEO",
     "or equivalent experience"),
    ("B23", "workday-Regulatory-Specialist-Diagnostics_202610-126607", "NO BLOQUEO",
     "or equivalent experience"),
    ("B24", "workday-Sales-Commercial-Manager_R-257732", "BLOQUEO",
     "Role Requirements + Bachelor's degree"),
    ("B25", "workday-Senior-Data-Scientist---ML-Engineering---MLOps_202609-123431",
     "NO BLOQUEO", "'Who You Are' es ambiguo -> se deja en revision"),
    ("B26", "workday-Software-Engineering-Systems--Intern_1210981", "BLOQUEO",
     "estudiante activo: 'Education & Experience: Currently pursuing'"),
    ("B27", "workday-Sr-Customer-Service-Representative_R-01366409", "NO BLOQUEO",
     "'preferred but not essential'"),
    ("B28", "workday-Strategy---Business-Operations-Head---CAMCAR_R-255612", "BLOQUEO",
     "Role Requirements Education + Bachelor's Degree"),
    ("B29", "workday-Switching-Technical-Support-Engineer-Intern---Switching-Support---EX-Products_1214133",
     "BLOQUEO", "estudiante activo: 'Education and Experience Currently pursuing'"),
    ("B30", "workday-Technical-Project-Manager---HiredScore_JR-0108592-1", "NO BLOQUEO",
     "Preferred Qualifications + Bachelor's degree"),
]

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
L.append("  above\", \"Requisitos\", \"Job Requirements:\", \"Role Requirements\",")
L.append("  \"Further requirements\", \"What you need to bring\", \"Education &")
L.append("  Experience\", \"Formación:\") bloquea aunque el extractor lo marque")
L.append("  `ambiguous`/`inferred`. Si el texto solo lo prefiere (\"Preferred\") NO")
L.append("  bloquea.")
L.append("- **Negación** → no se descarta (\"No university degree required.\").")
L.append("- **Alternativa** → no se descarta (\"or equivalent experience\", \"Associate's")
L.append("  or bachelor's degree\", \"or advanced university studies\", \"alternatively,")
L.append("  3+ years of relevant professional experience\").")
L.append("- **Excepción**: \"or equivalent field of study / discipline / degree\" NO es")
L.append("  una vía alternativa: sigue exigiendo un título universitario.")
L.append("- **Alcance por grupo**: la negación, el suavizador y la obligatoriedad se")
L.append("  aplican al **grupo** de títulos unidos por enumeración, no a la cláusula")
L.append("  completa. Así \"Bachelor's/University degree, Master's degree preferred\"")
L.append("  EXIGE el bachelor's (la coma corta el alcance del \"preferred\") pero")
L.append("  \"Bachelor's or Master's degree preferred\" NO exige ninguno de los dos.")
L.append("- **Estudiante activo** (\"currently pursuing\", \"must be enrolled\", \"active")
L.append("  university student\") es un criterio DISTINTO del título completado →")
L.append("  motivo `titulo_universitario_en_curso_requerido`.")
L.append("- **Semántica de la AUSENCIA del fact `pursuing`** (decidida 2026-10-29):")
L.append("  - el perfil registra hechos educativos y NINGUNO dice `pursuing` → se")
L.append("    sabe que la persona NO está registrada como estudiante activo →")
L.append("    **no cumple** → la vacante se descarta con el motivo")
L.append("    `titulo_universitario_en_curso_requerido`;")
L.append("  - el perfil NO registra NINGÚN hecho educativo → la dimensión educativa")
L.append("    **no es verificable** → nunca se descarta por falta de información: la")
L.append("    vacante va a `revisar_a_mano` con el motivo")
L.append("    `educacion_no_verificable`.")
L.append("")
L.append("### 1.1. Mecánicas GENERALES (decididas 2026-10-30)")
L.append("")
L.append("Las reglas son **generales**: el nivel lo declara el TEXTO de la oferta y")
L.append("el perfil se compara contra ese nivel. Nada depende de quién sea la")
L.append("persona: si cambia el perfil (sus hechos educativos), cambian los")
L.append("resultados sin tocar el código.")
L.append("")
L.append("- **M1 — El nivel lo declara el TEXTO, no el código canónico.** La escalera")
L.append("  es general (tipo ISCED): 1 secundaria · 2 superior de ciclo corto ·")
L.append("  3 universitario · 4 posgrado. El ancla es la evidencia literal del")
L.append("  requisito (`job_requirements.evidence`) y gana la frase más larga que")
L.append("  cubre al término: \"Two year college degree\" → 2 (aunque dentro diga")
L.append("  \"college degree\"), \"Bachelor's degree\" → 3, \"Master's degree\" → 4,")
L.append("  \"Associate's degree\" → 2, \"High School Diploma\" → 1. Un aviso del")
L.append("  extranjero se lee con SU vocabulario (no hay equivalencias por país).")
L.append("- **M2 — Una vía alternativa ACADÉMICA está o no DISPONIBLE** para el")
L.append("  perfil: se compara el nivel que declara la vía con el nivel de estudios")
L.append("  del perfil. \"or advanced university studies\" → posgrado (4);")
L.append("  \"or advanced/university coursework\" → universitario (3);")
L.append("  \"or technical degree\" / \"or associate's degree\" → ciclo corto (2).")
L.append("  Si hay una vía disponible → no bloquea; si TODAS las vías son de nivel")
L.append("  superior al del perfil → la vía no rescata y el título principal sigue")
L.append("  exigiéndose → `descartada`. Las vías por **experiencia** (\"or")
L.append("  equivalent experience\") NO son evaluables → nunca confirman un")
L.append("  descarte (conservador).")
L.append("- **M3 — Estudios universitarios PARCIALES** (\"80% completeness of a")
L.append("  bachelor's degree program\") = nivel 3 **sin título**: lo cumplen el")
L.append("  título universitario o los estudios universitarios en curso. Un")
L.append("  porcentaje de completitud no confiere título (ISCED 2011:")
L.append("  \"partial level completion\" es subcategoría de nivel, no cualificación).")
L.append("- **M4 — Sin lógica por país:** el perfil y las vacantes se comparan en la")
L.append("  misma escalera; el nivel vive en `candidate_profile_facts` + `concepto`")
L.append("  (datos), nunca en el código.")
L.append("")
L.append("**Fuentes de las 3 decisiones de negocio** (generales, no de Costa Rica):")
L.append("")
L.append("1. `\"or advanced university studies\"` (posgrado) solo desbloquea a quien")
L.append("   tiene estudios universitarios: ISCED 2011/OECD — los programas de")
L.append("   posgrado *require at least two years at ISCED level 6 prior to")
L.append("   entrance (although most require a four-year Bachelor's degree)*; la")
L.append("   UCR/SEP exige títulos previos para admitir en posgrado.")
L.append("2. `\"two year college degree\"` / `\"associate degree\"` = nivel 2: ISCED")
L.append("   2011/OECD — *Programmes classified at ISCED level 5 may be referred to")
L.append("   in many ways: higher technical education, community college education,")
L.append("   technician or advanced/higher vocational training, **associate degree**,")
L.append("   bac+2*; el bachelor es el nivel 6.")
L.append("3. `\"X % de un bachelor's degree program\"` = estudios parciales: ISCED")
L.append("   2011 — *individual credits awarded for successful completion of")
L.append("   individual courses are not considered as qualifications*.")
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
            if r["evidence"]:
                L.append("    - evidencia literal del requisito: > %s"
                         % str(r["evidence"]).replace("\n", " "))
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
L.append("## 5. Las %d `revisar_a_mano / educacion_no_confirmada` — por qué el MOTOR no las descarta"
         % len(noconf))
L.append("")
L.append("Son requisitos universitarios **obligatorios** que el TEXTO no confirma")
L.append("(negación o alternativa). Van a revisión manual y a la HOJA DE REVISIÓN")
L.append("pendiente (`docs/PASO5_REVISION_PENDIENTES.md`): el estado es el del")
L.append("**motor**; el veredicto humano queda ABIERTO hasta que una segunda")
L.append("persona firme en esa hoja.")
L.append("")
for i, f in enumerate(noconf, 1):
    texto = texto_de(f["job_id"])
    conf = matching.confirmar_requisito_universitario(texto)
    L.append("### %d. `%s` — %s" % (i, f["job_id"], f["title"]))
    L.append("")
    L.append("- detección textual: `%s` (término: `%r`)" % (conf.motivo, conf.termino))
    reqs = requisitos_de(f["job_id"])
    if reqs:
        L.append("- requisitos `education` extraídos:")
        for r in reqs:
            L.append("  - `value_text=%r` · `requirement_level=%r` · "
                     "`education_status=%r`"
                     % (r["value_text"], r["requirement_level"], r["education_status"]))
            if r["evidence"]:
                L.append("    - evidencia literal del requisito: > %s"
                         % str(r["evidence"]).replace("\n", " "))
    if conf.segmento:
        L.append("")
        L.append("> %s" % conf.segmento.replace("\n", " "))
        ctx = contexto(texto, conf.termino)
        if ctx:
            L.append(">")
            L.append("> contexto: %s" % ctx)
    elif reqs:
        # Sin término universitario en el texto: la evidencia literal es la
        # cita del propio requisito (p. ej. 'Two year college degree or
        # equivalent experience'), que es un nivel NO universitario.
        L.append("")
        L.append("> (el texto NO menciona un título universitario; la cita del")
        L.append("> requisito extraído es la que lo demuestra)")
    L.append("")

# --------------------------------------------------- medicion no_cumple
L.append("## 6. Medición AMPLIADA de `educacion_no_cumple` (43 casos)")
L.append("")
L.append("La muestra pequeña inicial (5 de 10) no era suficiente para decidir la")
L.append("regla. Se amplió a **43 casos** del grupo `educacion_no_cumple` de la")
L.append("corrida `20261029_171039` (106 vacantes en total):")
L.append("")
L.append("- **Estrato A (13)**: las 13 que la regla \"el texto decide\" promovió a")
L.append("  `descartada` — se revisan **todas**.")
L.append("- **Estrato B (30)**: 30 sistemáticas de las 93 restantes (una de cada")
L.append("  tres, ordenadas por `job_id`).")
L.append("")
L.append("Cada caso se revisó a mano contra la frase literal del aviso.")
L.append("`Estado final` es el de la corrida vigente `%s`." % vigente)
L.append("")
L.append("| # | job_id | veredicto manual | por qué | estado final | motivo final |")
L.append("|---|---|---|---|---|---|")
aciertos = 0
bloqueos = 0
for etiqueta, job_id, veredicto, porque in MEDICION:
    fila = conn.execute(
        "SELECT estado, motivo FROM job_match WHERE corrida_id=? AND job_id=?",
        (vigente, job_id)).fetchone()
    estado_final = fila["estado"] if fila else "?"
    motivo_final = fila["motivo"] if fila else "?"
    if veredicto == "BLOQUEO":
        bloqueos += 1
        ok = estado_final == "descartada"
    else:
        ok = estado_final != "descartada"
    if ok:
        aciertos += 1
    L.append("| %s | `%s` | %s | %s | %s | `%s` |"
             % (etiqueta, job_id, veredicto, porque, estado_final, motivo_final))
L.append("")
L.append("**Resultado: %d de 43 coinciden con el veredicto manual.**" % aciertos)
L.append("")
L.append("- Estrato A: 12 de 13 eran bloqueos reales; **1 falso descarte**")
L.append("  (`workday-Accounts-Payable-Representative_J-020440`: \"… and 1+ year of")
L.append("  relevant experience; **alternatively, 3+ years of relevant professional")
L.append("  experience**\") → corregido por la regla.")
L.append("- Estrato B: 14 de 30 eran bloqueos reales que el motor NO detectaba")
L.append("  (falsos negativos) → promovidos con frase literal.")
L.append("- Proporción de bloqueos reales en la muestra: **%d de 43 (%.0f%%)**; la")
L.append("  muestra inicial daba 5 de 10 (50%%). La proporción **se mantiene o")
L.append("  sube** → la regla NO estaba sobreajustada.")
L.append("- La regla nueva acierta en **%d de 43** casos: donde el texto obliga")
L.append("  descarta y donde el texto no obliga deja la vacante para revisión.")
L.append("")
L.append("### 6.1. Frase literal de cada caso")
L.append("")
for etiqueta, job_id, veredicto, porque in MEDICION:
    texto = texto_de(job_id)
    conf = matching.confirmar_requisito_universitario(texto)
    L.append("- **%s `%s`** — %s" % (etiqueta, job_id, porque))
    if conf.segmento:
        L.append("  > %s" % conf.segmento.replace("\n", " "))
    else:
        citas = [str(r["evidence"]).replace("\n", " ")
                 for r in requisitos_de(job_id) if r["evidence"]]
        if citas:
            L.append("  > %s" % citas[0])
        else:
            L.append("  > (sin frase)")
L.append("")

# --------------------------------------------------------------- delta
anterior = conn.execute(
    "SELECT corrida_id FROM job_match WHERE corrida_id <> ? "
    "ORDER BY corrida_id DESC LIMIT 1", (vigente,)).fetchone()
if anterior:
    prev = anterior["corrida_id"]
    antes = {
        r["job_id"]: (r["estado"], r["motivo"])
        for r in conn.execute(
            "SELECT job_id, estado, motivo FROM job_match WHERE corrida_id=?", (prev,))
    }
    despues = {
        r["job_id"]: (r["estado"], r["motivo"])
        for r in conn.execute(
            "SELECT job_id, estado, motivo FROM job_match WHERE corrida_id=?", (vigente,))
    }
    cambios = [
        (jid, antes[jid], despues[jid])
        for jid in sorted(set(antes) & set(despues))
        if antes[jid] != despues[jid]
    ]
    L.append("## 7. DELTA vs. la corrida anterior `%s` (%d avisos cambian)" % (prev, len(cambios)))
    L.append("")
    L.append("Cada cambio se midió ANTES de escribir la corrida nueva (evaluación en")
    L.append("seco contra la BD) y aquí queda documentado con la frase literal del")
    L.append("aviso.")
    L.append("")
    L.append("| # | job_id | antes | ahora | por qué |")
    L.append("|---|---|---|---|---|")
    for i, (jid, a, d) in enumerate(cambios, 1):
        porque = {
            ("revisar_a_mano", "descartada"): "vía académica sin nivel alcanzable",
            ("revisar_a_mano", "calificada"): "el texto declara un nivel que el perfil sí alcanza",
        }.get((a[0], d[0]), "motivo corregido: el texto sí obliga (lo que faltaba era la vía)")
        L.append("| %d | `%s` | `%s` / `%s` | `%s` / `%s` | %s |"
                 % (i, jid, a[0], a[1], d[0], d[1], porque))
    L.append("")
    L.append("### 7.1. Frase literal de cada cambio")
    L.append("")
    for i, (jid, a, d) in enumerate(cambios, 1):
        texto = texto_de(jid)
        L.append("- **%d. `%s`** — `%s/%s` → `%s/%s`" % (i, jid, a[0], a[1], d[0], d[1]))
        citas = []
        for cl in matching._clausulas(texto):
            if any(p.search(cl[0]) for p, _ in matching._FRASES_NIVEL):
                citas.append(cl[0])
                break
        if not citas:
            citas = [str(r["evidence"]) for r in requisitos_de(jid) if r["evidence"]]
        for cita in citas[:1]:
            L.append("  > %s" % " ".join(str(cita).split())[:400])
    L.append("")

SALIDA.write_text("\n".join(L), encoding="utf-8")
print("escrito %s (%d lineas) | corrida=%s | descartada=%d | no_confirmada=%d"
      % (SALIDA, len(L), vigente, len(descartadas), len(noconf)))
conn.close()
