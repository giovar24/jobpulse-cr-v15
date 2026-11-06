# -*- coding: utf-8 -*-
"""Evidencia del Paso 5 (GENERAR + VERIFICAR) — implementacion UNICA.

Antes esta logica vivia en dos scripts de la raiz
(``generar_evidencia_paso5.py`` y ``verificar_evidencia.py``), solo
ejecutables por CLI y por subprocess. Aqui queda como MODULO para que:

* la CLI siga igual (los scripts quedan como envoltorios finos),
* la UI pueda llamarla **sin subprocess** y mostrar
  "evidencia: al dia / desactualizada" despues de cada corrida del Paso 5.

Reglas del documento (no se tocan):

1. el texto citado es **literal** de ``jobs.requirements_raw`` +
   ``jobs.description_raw``;
2. el nombre del documento lo decide la corrida VIGENTE
   (``docs/PASO5_EVIDENCIA_<fecha>.md``), no una fecha fija: una corrida nueva
   no pisa el documento de otro dia;
3. ``descartada`` solo si el TEXTO confirma un titulo universitario
   obligatorio, sin negacion y sin alternativa; si no ->
   ``revisar_a_mano / educacion_no_confirmada`` (lo firma una 2a persona).
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Callable

from jobpulse_v15 import matching

# ---------------------------------------------------------------------------
# Medicion ampliada del grupo 'educacion_no_cumple' (corrida 20261029_171039).
# Veredicto manual: BLOQUEO = el TEXTO exige un titulo universitario.
# Muestra historica: se conserva aunque algunos avisos ya no esten en la BD.
# ---------------------------------------------------------------------------
MEDICION: list[tuple[str, str, str, str]] = [
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

#: Las 13 que la corrida 20261029_183231 promovio a 'descartada' (el usuario
#: pidio confirmarlas por consulta con frase literal, no resumidas).
PROMOVIDAS_13: list[str] = [
    "cinde-4901",
    "workday-Accounts-Payable-Representative_J-020440",
    "workday-Business-Analyst--Contract-Pricing-and-Accuracy_R265403",
    "workday-Continuous-Improvement-Intern_J-020427",
    "workday-Contract-Administrator--Internship-_1213007",
    "workday-Contracts-Negotiator_JR-0110562",
    "workday-Director--Corporate-Accounting_JR-0111126",
    "workday-Product-Portfolio-Intern_J-020242",
    "workday-Senior-Analyst--Finance--Internal-Auditor-_Req-51202-1",
    "workday-Senior-Director--Quality-Engineering_Req-50066",
    "workday-Service-Delivery-Manager_R77891-2",
    "workday-Sr-Technical-Architect_WD30279546",
    "workday-Tax-Audit-Senior-Specialist_888004-1",
]

PATRON_CORRIDA_EN_DOC = re.compile(r"corrida `(\d{8}_\d{6})`")


def fecha_de_corrida(corrida_id: str) -> str:
    """``20261030_174949`` -> ``2026-10-30`` (para el nombre del documento)."""
    match = re.match(r"^(\d{4})(\d{2})(\d{2})_", str(corrida_id or ""))
    if not match:
        return "sin-fecha"
    return "%s-%s-%s" % match.groups()


def docs_dir_para(db_path: str | Path) -> Path:
    """Carpeta ``docs`` del repo al que pertenece la base (``<repo>/data/x.db``).

    Si la base no vive en un ``<repo>/data/`` (ruta rara o una copia en
    ``%TEMP%``), cae a ``docs`` relativo al directorio de trabajo.
    """
    candidato = Path(db_path).resolve().parent.parent / "docs"
    if candidato.is_dir():
        return candidato
    return Path("docs")


def corrida_vigente(connection: sqlite3.Connection) -> str | None:
    """Corrida vigente en ``job_match`` (``valida = 1``), o ``None``."""
    fila = connection.execute(
        "SELECT corrida_id FROM job_match WHERE valida = 1 "
        "ORDER BY corrida_id DESC LIMIT 1"
    ).fetchone()
    return fila["corrida_id"] if fila else None


def _abrir(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


# ---------------------------------------------------------------------------
# GENERAR
# ---------------------------------------------------------------------------
def _texto_de(connection: sqlite3.Connection, job_id: str) -> str:
    job = connection.execute(
        "SELECT requirements_raw, description_raw FROM jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    if job is None:
        # El aviso ya no esta en la BD (purgado en una limpieza): las
        # secciones dinamicas (4/5) nunca lo piden porque hacen JOIN con
        # jobs; solo la muestra historica de la seccion 6 puede referenciarlo.
        return ""
    return "\n".join(
        x for x in (job["requirements_raw"], job["description_raw"]) if x
    )


def _existe_en_bd(connection: sqlite3.Connection, job_id: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)
    ).fetchone() is not None


def _requisitos_de(connection: sqlite3.Connection, job_id: str):
    return connection.execute(
        """SELECT value_text, requirement_level, education_status, codigo_canonico,
                  evidence
           FROM job_requirements r JOIN job_analysis a ON a.analysis_id = r.analysis_id
           WHERE a.is_current = 1 AND a.job_id = ? AND r.category = 'education'
           ORDER BY requirement_level, value_text""",
        (job_id,),
    ).fetchall()


def _contexto(texto: str, termino: str | None, radio: int = 200) -> str:
    if not termino:
        return ""
    pos = texto.lower().find(termino.lower())
    if pos < 0:
        return ""
    ini = max(0, pos - radio)
    fin = min(len(texto), pos + len(termino) + radio)
    return "...%s..." % " ".join(texto[ini:fin].split())


def _encabezado_y_criterio(
    L: list[str],
    connection: sqlite3.Connection,
    corrida: str,
    corridas: list[str],
) -> None:
    """Secciones 1-3 del documento (criterio, trazabilidad y conteo)."""
    L.append("# Paso 5 — Evidencia del bloqueante educativo (corrida `%s`)" % corrida)
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
        fila = connection.execute(
            "SELECT COUNT(*) n, SUM(CASE WHEN valida=1 THEN 1 ELSE 0 END) v "
            "FROM job_match WHERE corrida_id=?",
            (cid,),
        ).fetchone()
        L.append("%-16s %-6s %s" % (cid, fila["n"], fila["v"]))
    L.append("```")
    L.append("")
    L.append("## 3. Conteo por estado y motivo (corrida vigente `%s`)" % corrida)
    L.append("")
    L.append("```")
    for r in connection.execute(
        """SELECT estado, motivo, COUNT(*) n FROM job_match WHERE corrida_id=?
           GROUP BY estado, motivo ORDER BY estado, motivo""",
        (corrida,),
    ):
        L.append("%-22s | %-38s | %d" % (r["estado"], r["motivo"], r["n"]))
    L.append("```")
    L.append("")


def _seccion_descartadas(L: list[str], connection: sqlite3.Connection, corrida: str) -> int:
    """Seccion 4: cada `descartada` con su evidencia literal. Devuelve el total."""
    descartadas = connection.execute(
        """SELECT m.job_id, j.title FROM job_match m JOIN jobs j ON j.job_id = m.job_id
           WHERE m.corrida_id=? AND m.estado='descartada' ORDER BY m.job_id""",
        (corrida,),
    ).fetchall()
    L.append("## 4. Las %d `descartada` — evidencia literal" % len(descartadas))
    L.append("")
    for i, f in enumerate(descartadas, 1):
        texto = _texto_de(connection, f["job_id"])
        conf = matching.confirmar_requisito_universitario(texto)
        estado = connection.execute(
            "SELECT motivo FROM job_match WHERE corrida_id=? AND job_id=?",
            (corrida, f["job_id"]),
        ).fetchone()
        L.append("### %d. `%s` — %s" % (i, f["job_id"], f["title"]))
        L.append("")
        L.append("- motivo en BD: `%s`" % estado["motivo"])
        L.append("- detección textual: `%s` (término: `%r`) · obligatorio=%s · "
                 "en_curso=%s · suave=%s"
                 % (conf.motivo, conf.termino, conf.obligatorio, conf.en_curso, conf.suave))
        reqs = _requisitos_de(connection, f["job_id"])
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
            ctx = _contexto(texto, conf.termino)
            if ctx:
                L.append(">")
                L.append("> contexto: %s" % ctx)
        L.append("")
    return len(descartadas)


def _seccion_no_confirmadas(L: list[str], connection: sqlite3.Connection, corrida: str) -> int:
    """Seccion 5: `educacion_no_confirmada` y por que no se descartan."""
    noconf = connection.execute(
        """SELECT m.job_id, j.title FROM job_match m JOIN jobs j ON j.job_id = m.job_id
           WHERE m.corrida_id=? AND m.motivo='educacion_no_confirmada'
           ORDER BY m.job_id""",
        (corrida,),
    ).fetchall()
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
        texto = _texto_de(connection, f["job_id"])
        conf = matching.confirmar_requisito_universitario(texto)
        L.append("### %d. `%s` — %s" % (i, f["job_id"], f["title"]))
        L.append("")
        L.append("- detección textual: `%s` (término: `%r`)" % (conf.motivo, conf.termino))
        reqs = _requisitos_de(connection, f["job_id"])
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
            ctx = _contexto(texto, conf.termino)
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
    return len(noconf)


def _seccion_medicion(L: list[str], connection: sqlite3.Connection, corrida: str) -> None:
    """Seccion 6: la medicion ampliada de 43 casos (muestra historica)."""
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
    L.append("`Estado final` es el de la corrida vigente `%s`." % corrida)
    L.append("")
    L.append("| # | job_id | veredicto manual | por qué | estado final | motivo final |")
    L.append("|---|---|---|---|---|---|")
    aciertos = 0
    purgados = 0
    for etiqueta, job_id, veredicto, porque in MEDICION:
        fila = connection.execute(
            "SELECT estado, motivo FROM job_match WHERE corrida_id=? AND job_id=?",
            (corrida, job_id),
        ).fetchone()
        if not _existe_en_bd(connection, job_id):
            # Purgado en una limpieza posterior a la corrida medida: la muestra
            # historica lo conserva, pero ya no es verificable contra la BD.
            purgados += 1
            estado_final = motivo_final = "purgado"
        else:
            estado_final = fila["estado"] if fila else "?"
            motivo_final = fila["motivo"] if fila else "?"
        if estado_final == "purgado":
            L.append("| %s | `%s` | %s | %s | %s | %s |"
                     % (etiqueta, job_id, veredicto, porque, estado_final, motivo_final))
            continue
        if veredicto == "BLOQUEO":
            ok_caso = estado_final == "descartada"
        else:
            ok_caso = estado_final != "descartada"
        if ok_caso:
            aciertos += 1
        L.append("| %s | `%s` | %s | %s | %s | `%s` |"
                 % (etiqueta, job_id, veredicto, porque, estado_final, motivo_final))
    verificables = len(MEDICION) - purgados
    L.append("")
    if purgados:
        L.append("> %d de los %d avisos de la muestra ya NO están en la BD actual"
                 " (purgados por una limpieza posterior): se listan con"
                 " `purgado` y no entran en el cómputo." % (purgados, len(MEDICION)))
        L.append("")
    L.append("**Resultado: %d de %d verificables coinciden con el veredicto manual.**"
             % (aciertos, verificables))
    L.append("")
    L.append("- Estrato A: 12 de 13 eran bloqueos reales; **1 falso descarte**")
    L.append("  (`workday-Accounts-Payable-Representative_J-020440`: \"… and 1+ year of")
    L.append("  relevant experience; **alternatively, 3+ years of relevant professional")
    L.append("  experience**\") → corregido por la regla.")
    bloqueos_historicos = sum(1 for _, _, veredicto, _ in MEDICION if veredicto == "BLOQUEO")
    L.append("- Estrato B: 14 de 30 eran bloqueos reales que el motor NO detectaba")
    L.append("  (falsos negativos) → promovidos con frase literal.")
    L.append("- Proporción de bloqueos reales en la muestra: **%d de %d (%.0f%%)**; la"
             % (bloqueos_historicos, len(MEDICION),
                100 * bloqueos_historicos / len(MEDICION)))
    L.append("  muestra inicial daba 5 de 10 (50%%). La proporción **se mantiene o")
    L.append("  sube** → la regla NO estaba sobreajustada.")
    L.append("- La regla nueva acierta en **%d de %d** casos verificables: donde el"
             % (aciertos, verificables))
    L.append("  texto obliga descarta y donde el texto no obliga deja la vacante para")
    L.append("  revisión.")
    L.append("")
    L.append("### 6.1. Frase literal de cada caso")
    L.append("")
    for etiqueta, job_id, veredicto, porque in MEDICION:
        if not _existe_en_bd(connection, job_id):
            L.append("- **%s `%s`** — %s" % (etiqueta, job_id, porque))
            L.append("  > (purgado en la limpieza 2026-10-31: sin frase verificable)")
            continue
        texto = _texto_de(connection, job_id)
        conf = matching.confirmar_requisito_universitario(texto)
        L.append("- **%s `%s`** — %s" % (etiqueta, job_id, porque))
        if conf.segmento:
            L.append("  > %s" % conf.segmento.replace("\n", " "))
        else:
            citas = [str(r["evidence"]).replace("\n", " ")
                     for r in _requisitos_de(connection, job_id) if r["evidence"]]
            if citas:
                L.append("  > %s" % citas[0])
            else:
                L.append("  > (sin frase)")
    L.append("")


def _seccion_delta(L: list[str], connection: sqlite3.Connection, corrida: str) -> None:
    """Seccion 7: delta contra la corrida anterior."""
    anterior = connection.execute(
        "SELECT corrida_id FROM job_match WHERE corrida_id <> ? "
        "ORDER BY corrida_id DESC LIMIT 1",
        (corrida,),
    ).fetchone()
    if not anterior:
        return
    prev = anterior["corrida_id"]
    antes = {
        r["job_id"]: (r["estado"], r["motivo"])
        for r in connection.execute(
            "SELECT job_id, estado, motivo FROM job_match WHERE corrida_id=?", (prev,))
    }
    despues = {
        r["job_id"]: (r["estado"], r["motivo"])
        for r in connection.execute(
            "SELECT job_id, estado, motivo FROM job_match WHERE corrida_id=?", (corrida,))
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
        texto = _texto_de(connection, jid)
        L.append("- **%d. `%s`** — `%s/%s` → `%s/%s`" % (i, jid, a[0], a[1], d[0], d[1]))
        citas = []
        for cl in matching._clausulas(texto):
            if any(p.search(cl[0]) for p, _ in matching._FRASES_NIVEL):
                citas.append(cl[0])
                break
        if not citas:
            citas = [str(r["evidence"]) for r in _requisitos_de(connection, jid) if r["evidence"]]
        for cita in citas[:1]:
            L.append("  > %s" % " ".join(str(cita).split())[:400])
    L.append("")


def generar_evidencia(
    db_path: str | Path = "data/jobpulse_v15.db",
    docs_dir: str | Path = "docs",
    salida: str | Path | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Genera el documento de evidencia de la corrida VIGENTE del Paso 5.

    ``salida`` es opcional: por defecto se escribe
    ``docs/PASO5_EVIDENCIA_<fecha de la corrida>.md`` (el nombre lo decide la
    corrida vigente, no una fecha fija).

    Devuelve ``{"ruta", "corrida", "descartadas", "no_confirmadas", "lineas"}``.
    """
    connection = _abrir(db_path)
    try:
        corrida = corrida_vigente(connection)
        if corrida is None:
            raise ValueError("No hay corrida del Paso 5 (job_match.valida = 1).")
        docs = Path(docs_dir)
        destino = Path(salida) if salida else docs / (
            "PASO5_EVIDENCIA_%s.md" % fecha_de_corrida(corrida)
        )
        corridas = [r["corrida_id"] for r in connection.execute(
            "SELECT DISTINCT corrida_id FROM job_match ORDER BY corrida_id")]
        L: list[str] = []
        _encabezado_y_criterio(L, connection, corrida, corridas)
        n_descartadas = _seccion_descartadas(L, connection, corrida)
        n_noconf = _seccion_no_confirmadas(L, connection, corrida)
        _seccion_medicion(L, connection, corrida)
        _seccion_delta(L, connection, corrida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text("\n".join(L), encoding="utf-8")
        log(
            "escrito %s (%d lineas) | corrida=%s | descartada=%d | no_confirmada=%d"
            % (destino, len(L), corrida, n_descartadas, n_noconf)
        )
        return {
            "ruta": destino,
            "corrida": corrida,
            "descartadas": n_descartadas,
            "no_confirmadas": n_noconf,
            "lineas": len(L),
        }
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# VERIFICAR
# ---------------------------------------------------------------------------
def corrida_de_doc(ruta: str | Path) -> str | None:
    """Corrida que documenta un archivo de evidencia (primera linea)."""
    try:
        with Path(ruta).open(encoding="utf-8") as fh:
            primera = fh.readline()
    except OSError:
        return None
    match = PATRON_CORRIDA_EN_DOC.search(primera)
    return match.group(1) if match else None


def doc_por_defecto(
    db_path: str | Path = "data/jobpulse_v15.db",
    docs_dir: str | Path = "docs",
) -> Path:
    """Documento de evidencia de la CORRIDA VIGENTE (si no, el mas reciente).

    Elegir por NOMBRE de archivo fallaba: una corrida nueva del mismo dia
    dejaba un documento viejo con el nombre mas alto y la verificacion daba
    falsos fallos.
    """
    docs = Path(docs_dir)
    candidatos = sorted(docs.glob("PASO5_EVIDENCIA_*.md"), key=lambda ruta: ruta.name)
    if not candidatos:
        return docs / "PASO5_EVIDENCIA_2026-10-29.md"
    try:
        connection = _abrir(db_path)
        try:
            vigente = corrida_vigente(connection)
        finally:
            connection.close()
    except sqlite3.Error:
        vigente = None
    if vigente:
        for ruta in reversed(candidatos):
            if corrida_de_doc(ruta) == vigente:
                return ruta
    return candidatos[-1]


def verificar_evidencia(
    db_path: str | Path = "data/jobpulse_v15.db",
    docs_dir: str | Path = "docs",
    doc: str | Path | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Verifica POR CONSULTA que el documento cita texto LITERAL de la BD.

    Para cada ``descartada`` (y cada ``educacion_no_confirmada``) comprueba que
    el ``job_id`` aparezca en el documento, que la FRASE LITERAL que confirma el
    titulo aparezca en el documento y que esa frase sea un substring LITERAL del
    texto de la oferta. Tambien comprueba las 13 promovidas historicas.

    Devuelve ``{"ok", "documento", "corrida", "verificaciones", "fallos",
    "secciones"}``. ``ok`` es False si hay discrepancias (el script sale con 1).
    """
    ruta = Path(doc) if doc else doc_por_defecto(db_path, docs_dir)
    connection = _abrir(db_path)
    try:
        vigente = corrida_vigente(connection)
        if vigente is None:
            return {
                "ok": False,
                "documento": ruta,
                "corrida": None,
                "verificaciones": 0,
                "fallos": ["no hay corrida vigente en job_match.valida = 1"],
                "secciones": {},
            }
        try:
            texto_doc = ruta.read_text(encoding="utf-8")
        except OSError as exc:
            return {
                "ok": False,
                "documento": ruta,
                "corrida": vigente,
                "verificaciones": 0,
                "fallos": ["no se pudo leer el documento: %s" % exc],
                "secciones": {},
            }

        fallos: list[str] = []
        contador = {"ok": 0}

        def _texto_de(job_id: str) -> str:
            fila = connection.execute(
                "SELECT requirements_raw, description_raw FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if fila is None:
                return ""
            return "\n".join(
                x for x in (fila["requirements_raw"], fila["description_raw"]) if x
            )

        def comprobar(job_id: str, estado_esperado: str | None = None) -> bool:
            if not _existe_en_bd(connection, job_id):
                # Purgado en una limpieza posterior: no es un fallo del
                # documento, simplemente ya no es verificable.
                log("   ~(purgado, omitido) %s" % job_id)
                return True
            fila = connection.execute(
                "SELECT estado, motivo FROM job_match WHERE corrida_id=? AND job_id=?",
                (vigente, job_id),
            ).fetchone()
            if fila is None:
                fallos.append("%s: no esta en la corrida vigente" % job_id)
                return False
            if estado_esperado and fila["estado"] != estado_esperado:
                fallos.append(
                    "%s: estado %s (se esperaba %s)"
                    % (job_id, fila["estado"], estado_esperado)
                )
                return False
            texto = _texto_de(job_id)
            conf = matching.confirmar_requisito_universitario(texto)
            if job_id not in texto_doc:
                fallos.append("%s: el job_id no aparece en el documento" % job_id)
                return False
            frase = (conf.segmento or "").strip()
            if not frase:
                # Sin frase (p. ej. el texto no menciona el titulo): el
                # documento registra la deteccion textual; no hay cita que
                # verificar.
                if conf.motivo not in texto_doc:
                    fallos.append(
                        "%s: la deteccion textual %r no aparece en el documento"
                        % (job_id, conf.motivo)
                    )
                    return False
                contador["ok"] += 1
                return True
            # La frase puede venir truncada con '...' (ventana de 400 chars):
            # el interior SI tiene que ser literal del texto de la BD.
            interior = frase
            if interior.startswith("..."):
                interior = interior[3:]
            if interior.endswith("..."):
                interior = interior[:-3]
            if " ".join(frase.split()) not in " ".join(texto_doc.split()):
                fallos.append("%s: la frase literal no aparece en el documento" % job_id)
                return False
            if " ".join(interior.split()) not in " ".join(texto.split()):
                fallos.append("%s: la frase NO es literal del texto de la BD" % job_id)
                return False
            contador["ok"] += 1
            return True

        log("documento = %s" % ruta)
        log("corrida vigente = %s" % vigente)
        log("")
        log("=== A) todas las 'descartada' de la corrida vigente ===")
        descartadas = [r["job_id"] for r in connection.execute(
            "SELECT job_id FROM job_match WHERE corrida_id=? AND estado='descartada' "
            "ORDER BY job_id", (vigente,))]
        for job_id in descartadas:
            comprobar(job_id, "descartada")
        ok_a = contador["ok"]
        log("  verificadas con frase literal: %d / %d" % (ok_a, len(descartadas)))

        log("")
        noconf = [r["job_id"] for r in connection.execute(
            "SELECT job_id FROM job_match WHERE corrida_id=? "
            "AND motivo='educacion_no_confirmada' ORDER BY job_id", (vigente,))]
        log("=== B) las %d 'revisar_a_mano / educacion_no_confirmada' ===" % len(noconf))
        for job_id in noconf:
            comprobar(job_id)
        ok_b = contador["ok"] - ok_a
        log("  verificadas con frase literal: %d / %d" % (ok_b, len(noconf)))

        log("")
        log("=== C) las 13 promovidas por la corrida 20261029_183231 ===")
        for job_id in PROMOVIDAS_13:
            comprobar(job_id)
        ok_c = contador["ok"] - ok_a - ok_b
        log("  documentadas con frase literal: %d / %d" % (ok_c, len(PROMOVIDAS_13)))
        for job_id in PROMOVIDAS_13:
            if not _existe_en_bd(connection, job_id):
                log("   %-64s (purgado)" % job_id[:64])
                continue
            fila = connection.execute(
                "SELECT estado, motivo FROM job_match WHERE corrida_id=? AND job_id=?",
                (vigente, job_id),
            ).fetchone()
            conf = matching.confirmar_requisito_universitario(_texto_de(job_id))
            log("   %-64s %-16s %-38s" % (job_id[:64], fila["estado"], fila["motivo"]))
            log("        FRASE: %s" % (conf.segmento or "")[:180])

        log("")
        if fallos:
            log("=== FALLOS: %d ===" % len(fallos))
            for f in fallos:
                log("   !! %s" % f)
        else:
            log("=== TODO CUADRA: %d verificaciones con frase LITERAL ===" % contador["ok"])
        return {
            "ok": not fallos,
            "documento": ruta,
            "corrida": vigente,
            "verificaciones": contador["ok"],
            "fallos": fallos,
            "secciones": {
                "descartadas": (ok_a, len(descartadas)),
                "no_confirmadas": (ok_b, len(noconf)),
                "promovidas_13": (ok_c, len(PROMOVIDAS_13)),
            },
        }
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# INDICADOR (UI / CLI): ¿la evidencia esta al dia?
# ---------------------------------------------------------------------------
def estado_evidencia(
    db_path: str | Path = "data/jobpulse_v15.db",
    docs_dir: str | Path = "docs",
    verificar: bool = False,
) -> dict[str, Any]:
    """¿La evidencia de la corrida vigente existe y cuadra? (sin subprocess).

    Devuelve ``{"corrida", "documento", "al_dia", "motivo"}`` y, si
    ``verificar=True``, tambien ``"verificaciones"`` y ``"fallos"``.
    """
    ruta = doc_por_defecto(db_path, docs_dir)
    try:
        connection = _abrir(db_path)
        try:
            vigente = corrida_vigente(connection)
        finally:
            connection.close()
    except sqlite3.Error:
        vigente = None
    if vigente is None:
        return {
            "corrida": None,
            "documento": None,
            "al_dia": False,
            "motivo": "no hay corrida vigente del Paso 5",
        }
    if not ruta.is_file():
        return {
            "corrida": vigente,
            "documento": None,
            "al_dia": False,
            "motivo": "no existe documento de evidencia",
        }
    if corrida_de_doc(ruta) != vigente:
        return {
            "corrida": vigente,
            "documento": ruta,
            "al_dia": False,
            "motivo": "el documento no corresponde a la corrida vigente",
        }
    if not verificar:
        return {
            "corrida": vigente,
            "documento": ruta,
            "al_dia": True,
            "motivo": "el documento es de la corrida vigente",
        }
    resultado = verificar_evidencia(db_path, docs_dir, ruta, log=lambda _t: None)
    return {
        "corrida": vigente,
        "documento": ruta,
        "al_dia": bool(resultado["ok"]),
        "motivo": (
            "%d verificaciones con frase literal" % resultado["verificaciones"]
            if resultado["ok"]
            else "%d discrepancia(s)" % len(resultado["fallos"])
        ),
        "verificaciones": resultado["verificaciones"],
        "fallos": resultado["fallos"],
    }
