# -*- coding: utf-8 -*-
"""Verifica POR CONSULTA que el documento de evidencia contiene, con TEXTO
LITERAL, cada vacante de la corrida vigente.

Para cada vacante `descartada` (y cada `educacion_no_confirmada`) comprueba:

1. que el `job_id` aparezca en ``docs/PASO5_EVIDENCIA_2026-10-29.md``;
2. que la FRASE LITERAL que confirma el titulo aparezca en el documento;
3. que esa frase sea un substring LITERAL del texto de la oferta en la BD
   (``requirements_raw`` + ``description_raw``) -> no es un resumen.

Ademas comprueba que las 13 vacantes promovidas por la corrida anterior
siguen documentadas con frase literal.

Uso: .\\.venv\\Scripts\\python.exe -X utf8 verificar_evidencia.py [doc]
Salida: 0 si todo cuadra, 1 si hay discrepancias.
"""
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))
from jobpulse_v15 import matching

def _doc_por_defecto() -> Path:
    """Documento de evidencia MAS RECIENTE (si no, el del 29-10)."""
    candidatos = sorted(
        (REPO / "docs").glob("PASO5_EVIDENCIA_*.md"),
        key=lambda ruta: ruta.name,
    )
    return candidatos[-1] if candidatos else REPO / "docs" / "PASO5_EVIDENCIA_2026-10-29.md"


DOC = Path(sys.argv[1] if len(sys.argv) > 1 else _doc_por_defecto())
DB = REPO / "data" / "jobpulse_v15.db"

# Las 13 que la corrida 20261029_183231 promovio a 'descartada' (el usuario
# pidio confirmarlas por consulta con frase literal, no resumidas).
PROMOVIDAS_13 = [
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

doc = DOC.read_text(encoding="utf-8")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
vigente = conn.execute(
    "SELECT corrida_id FROM job_match WHERE valida = 1 ORDER BY corrida_id DESC LIMIT 1"
).fetchone()["corrida_id"]

fallos: list[str] = []
ok = 0


def texto_de(job_id: str) -> str:
    fila = conn.execute(
        "SELECT requirements_raw, description_raw FROM jobs WHERE job_id = ?", (job_id,)
    ).fetchone()
    return "\n".join(x for x in (fila["requirements_raw"], fila["description_raw"]) if x)


def comprobar(job_id: str, estado_esperado: str | None = None) -> bool:
    global ok
    fila = conn.execute(
        "SELECT estado, motivo FROM job_match WHERE corrida_id=? AND job_id=?",
        (vigente, job_id)).fetchone()
    if fila is None:
        fallos.append("%s: no esta en la corrida vigente" % job_id)
        return False
    if estado_esperado and fila["estado"] != estado_esperado:
        fallos.append("%s: estado %s (se esperaba %s)" % (job_id, fila["estado"], estado_esperado))
        return False
    texto = texto_de(job_id)
    conf = matching.confirmar_requisito_universitario(texto)
    if job_id not in doc:
        fallos.append("%s: el job_id no aparece en el documento" % job_id)
        return False
    frase = (conf.segmento or "").strip()
    if not frase:
        # Sin frase (p. ej. el texto no menciona el titulo): el documento
        # registra la deteccion textual; no hay cita literal que verificar.
        if conf.motivo not in doc:
            fallos.append("%s: la deteccion textual %r no aparece en el documento"
                          % (job_id, conf.motivo))
            return False
        ok += 1
        return True
    # La frase puede venir truncada con '...' (ventana de 400 chars): el
    # interior SI tiene que ser literal del texto de la BD.
    interior = frase
    if interior.startswith("..."):
        interior = interior[3:]
    if interior.endswith("..."):
        interior = interior[:-3]
    if " ".join(frase.split()) not in " ".join(doc.split()):
        fallos.append("%s: la frase literal no aparece en el documento" % job_id)
        return False
    if " ".join(interior.split()) not in " ".join(texto.split()):
        fallos.append("%s: la frase NO es literal del texto de la BD" % job_id)
        return False
    ok += 1
    return True


print("documento = %s" % DOC)
print("corrida vigente = %s" % vigente)
print()
print("=== A) todas las 'descartada' de la corrida vigente ===")
descartadas = [r["job_id"] for r in conn.execute(
    "SELECT job_id FROM job_match WHERE corrida_id=? AND estado='descartada' ORDER BY job_id",
    (vigente,))]
for job_id in descartadas:
    comprobar(job_id, "descartada")
print("  verificadas con frase literal: %d / %d" % (ok, len(descartadas)))

print()
noconf = [r["job_id"] for r in conn.execute(
    "SELECT job_id FROM job_match WHERE corrida_id=? AND motivo='educacion_no_confirmada' "
    "ORDER BY job_id", (vigente,))]
print("=== B) las %d 'revisar_a_mano / educacion_no_confirmada' ===" % len(noconf))
antes = ok
for job_id in noconf:
    comprobar(job_id)
print("  verificadas con frase literal: %d / %d" % (ok - antes, len(noconf)))

print()
print("=== C) las 13 promovidas por la corrida 20261029_183231 ===")
antes = ok
for job_id in PROMOVIDAS_13:
    comprobar(job_id)
print("  documentadas con frase literal: %d / %d" % (ok - antes, len(PROMOVIDAS_13)))
for job_id in PROMOVIDAS_13:
    fila = conn.execute(
        "SELECT estado, motivo FROM job_match WHERE corrida_id=? AND job_id=?",
        (vigente, job_id)).fetchone()
    conf = matching.confirmar_requisito_universitario(texto_de(job_id))
    print("   %-64s %-16s %-38s" % (job_id[:64], fila["estado"], fila["motivo"]))
    print("        FRASE: %s" % (conf.segmento or "")[:180])

print()
if fallos:
    print("=== FALLOS: %d ===" % len(fallos))
    for f in fallos:
        print("   !! %s" % f)
    conn.close()
    sys.exit(1)
print("=== TODO CUADRA: %d verificaciones con frase LITERAL ===" % ok)
conn.close()
