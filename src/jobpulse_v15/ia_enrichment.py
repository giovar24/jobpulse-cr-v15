# -*- coding: utf-8 -*-
"""
jobpulse_v15.ia_enrichment — Enriquecimiento de jobs usando IA externa.

Enriquece SOLO campos críticos faltantes usando prompts simples y secuenciales:
- CRÍTICOS: city, region, work_mode, date_published
- SECUNDARIOS (opcionales): employment_type, salary, skills, languages

Uso:
    from jobpulse_v15.ia_enrichment import run_ia_enrichment
    import asyncio
    result = asyncio.run(run_ia_enrichment(limit=50))
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from jobpulse_v15.salario import contexto_salario, declara_salario
from jobpulse_v15.ubicaciones_cr import ciudad_es_valida, es_provincia_valida

# Import IA client
try:
    from jobpulse_v15.ia_api import (
        IAClient,
        IAError,
        IAModeloError,
        IACuotaError,
        PROVEEDOR_NOMBRES,
        opt_int,
    )
    IA_AVAILABLE = True
except ImportError:
    IA_AVAILABLE = False
    IAClient = None
    IAError = Exception
    IAModeloError = Exception
    IACuotaError = Exception
    PROVEEDOR_NOMBRES = {}
    opt_int = None  # type: ignore[assignment]

logger = logging.getLogger("jobpulse.ia_enrich")


# ─── Schemas simples por campo ───

LOCATION_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": ["string", "null"]},
        "region": {"type": ["string", "null"]}
    },
    "required": ["city", "region"],
    "additionalProperties": False
}

WORK_MODE_SCHEMA = {
    "type": "object",
    "properties": {
        "work_mode": {"type": "string", "enum": ["remote", "hybrid", "onsite", "unknown"]}
    },
    "required": ["work_mode"],
    "additionalProperties": False
}

DATE_SCHEMA = {
    "type": "object",
    "properties": {
        "date_published": {"type": ["string", "null"]}
    },
    "required": ["date_published"],
    "additionalProperties": False
}

EMPLOYMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "employment_type": {"type": ["string", "null"], "enum": ["Full-time", "Part-time", "Contract", "Internship", None]}
    },
    "required": ["employment_type"],
    "additionalProperties": False
}

SALARY_SCHEMA = {
    "type": "object",
    "properties": {
        "salary_min": {"type": ["number", "null"]},
        "salary_max": {"type": ["number", "null"]},
        "salary_currency": {"type": ["string", "null"]},
        "salary_period": {"type": ["string", "null"]}
    },
    "required": ["salary_min", "salary_max", "salary_currency", "salary_period"],
    "additionalProperties": False
}

SKILLS_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["skills"],
    "additionalProperties": False
}

LANGUAGES_SCHEMA = {
    "type": "object",
    "properties": {
        "languages": {"type": "object", "additionalProperties": {"type": "string"}}
    },
    "required": ["languages"],
    "additionalProperties": False
}


# ─── Prompts simples y enfocados ───

LOCATION_PROMPT = """Eres experto en ubicaciones de Costa Rica.
IMPORTANTE: city = CANTÓN (ej: Escazú, Belén, San Carlos), region = PROVINCIA (ej: San José, Heredia, Alajuela). NO intercambiar.

Formatos comunes:
- "Provincia / Cantón / Distrito" → city=Cantón, region=Provincia
- "Empresa, Cantón Provincia" → city=Cantón, region=Provincia (filtrar nombre empresa)
- "Cantón, Provincia" → city=Cantón, region=Provincia
- "Solo Provincia" → city=null, region=Provincia
- "Remote" / "Virtual" → city=null, region=null

Ejemplos:
- "San José / Escazú / Escazú" → {"city": "Escazú", "region": "San José"}
- "HCLTech, Evolution Free Zone" → {"city": "Evolution Free Zone", "region": "Heredia"}
- "HCLTech, Belén Heredia" → {"city": "Belén", "region": "Heredia"}
- "Guanacaste" → {"city": null, "region": "Guanacaste"}
- "Remote" → {"city": null, "region": null}

Responde SOLO JSON: {"city": "...", "region": "..."}"""

WORK_MODE_PROMPT = """Detecta modalidad de trabajo EXPLÍCITA en el texto.
- "remote" / "100% remoto" / "teletrabajo" -> remote
- "híbrido" / "hybrid" / "mixto" / "semipresencial" -> hybrid  
- "presencial" / "onsite" / "oficina" / "en sitio" -> onsite
- Si no está explícito -> unknown

Responde SOLO JSON: {"work_mode": "..."}"""

# ─── Modalidad declarada de forma literal (regla determinista, sin IA) ───
#
# Antes del prompt se prueba una lista corta y conservadora de marcas
# textuales que declaran la modalidad SIN ambigüedad. Dos motivos:
#
# 1. El prompt recibe la descripción truncada a 2000 chars
#    (``enrich_job_fields``), y las etiquetas ``#LI-Onsite`` / ``#LI-Hybrid``
#    de Workday suelen estar al final del aviso: el modelo no llega a verlas.
# 2. El prompt exige modalidad EXPLÍCITA, y con razón: "on-site fitness
#    center", "hybrid identity (Azure AD)" o "hybrid project environments"
#    NO son modalidad. Aquí solo entran patrones que sí lo son.
#
# El orden importa: gana el primero que aparezca en la tupla, así que las
# etiquetas ``#LI-`` (declaración del reclutador) van antes que las frases.
_PATRONES_WORK_MODE: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    # Etiquetas de LinkedIn/Workday que el reclutador escribe en el aviso.
    # Admiten tildes y plurales: "#LI-Híbrido" es la misma declaración que
    # "#LI-Hybrid" (Kimberly-Clark escribe la etiqueta en español).
    ("remote", re.compile(r"#\s*(?:LI|RPOCR)\s*[-_]?\s*(?:LI\s*[-_]?\s*)?remot[eo]a?\b", re.I)),
    ("hybrid", re.compile(r"#\s*(?:LI|RPOCR)\s*[-_]?\s*(?:LI\s*[-_]?\s*)?h(?:y|[ií])brid[oa]?\b", re.I)),
    ("onsite", re.compile(r"#\s*(?:LI|RPOCR)\s*[-_]?\s*(?:LI\s*[-_]?\s*)?on[-\s]?site\b", re.I)),
    # "Working Conditions: Remote / Work-from-home" (TD SYNNEX y similares):
    # el campo de condiciones de trabajo DECLARA la modalidad del puesto.
    ("remote", re.compile(
        r"working\s+conditions\s*:?\s*(?:\(\s*)?"
        r"(?:remote\b|work[-\s]?from[-\s]?home\b|work\s+from\s+home\b)",
        re.I,
    )),
    ("remote", re.compile(
        r"condiciones\s+de\s+trabajo\s*:?\s*(?:\(\s*)?"
        r"(?:remot[eo]a?\b|teletrabajo\b)",
        re.I,
    )),
    # "Working Conditions: Professional environment (Hybrid)."
    ("hybrid", re.compile(
        r"working\s+conditions\s*:?\s*[^\n]{0,60}?\bh(?:y|[ií])brid[oa]?\b",
        re.I,
    )),
    ("hybrid", re.compile(
        r"condiciones\s+de\s+trabajo\s*:?\s*[^\n]{0,60}?\bh(?:y|[ií])brid[oa]?\b",
        re.I,
    )),
    # "Hybrid Work: Candidates will be expected to work from the office at
    # least 50% of the time." (la modalidad, con su regla, escrita).
    ("hybrid", re.compile(r"hybrid\s+work\s*:", re.I)),
    # "This is a remote role based out of Costa Rica." (el puesto, no el
    # servicio: "Video Remote Interpreter" NO entra aquí).
    ("remote", re.compile(
        r"(?:this|it)\s+is\s+a\s+remote\s+(?:role|position|job)\b", re.I)),
    # "Multiple office days with some remote flexibility." (presencia en
    # oficina + remoto = híbrido). "required office days every week" NO
    # entra: es 100% presencial. "remote flexibility" suelto tampoco: puede
    # ser un beneficio ("...pay structure and remote flexibility") de un
    # puesto 100% remoto.
    ("hybrid", re.compile(
        r"(?:multiple|several)\s+office\s+days\b[^.\n]{0,60}\bremote\b",
        re.I,
    )),
    # Frases que describen la modalidad del PUESTO (no del edificio ni del
    # proyecto). "híbrido" suelto no vale: "modelo híbrido" sí.
    ("hybrid", re.compile(
        r"hybrid\s+(?:work\s+)?(?:arrangement|work\s+environment|position|role|schedule)"
        r"|modelo\s+h[ií]brido|esquema\s+h[ií]brido|modalidad\s+h[ií]brida",
        re.I,
    )),
    ("remote", re.compile(
        r"100\s*%\s*(?:remote|remot[oa])|fully\s+remote|totalmente\s+remot[oa]"
        r"|100\s*%\s*teletrabajo",
        re.I,
    )),
    ("onsite", re.compile(
        r"100\s*%\s*(?:on[-\s]?site|presencial)|100\s*%\s*en\s+(?:la\s+)?oficina",
        re.I,
    )),
)


def work_mode_por_patrones(*textos: Optional[str]) -> Optional[str]:
    """Devuelve ``remote``/``hybrid``/``onsite`` si el texto lo declara literal.

    Recibe uno o más textos (descripción, requisitos…) y devuelve ``None``
    cuando no hay una marca inequívoca: en ese caso decide la IA. Pensada
    para ejecutarse sobre el texto COMPLETO, no sobre el recorte de 2000
    chars que ve el modelo.
    """
    for texto in textos:
        if not texto:
            continue
        for modalidad, patron in _PATRONES_WORK_MODE:
            if patron.search(texto):
                return modalidad
    return None


DATE_PROMPT = """Extrae fecha de publicación EXPLÍCITA (ISO YYYY-MM-DD).
Formatos válidos: "2024-10-15", "15 octubre 2024", "15 de octubre de 2024".
NO uses fechas relativas ("hace 3 días", "2 weeks ago").
Si no hay fecha explícita -> null.

Responde SOLO JSON: {"date_published": "..."}"""

EMPLOYMENT_PROMPT = """Extrae tipo de empleo SOLO si está EXPLÍCITO:
- "Full-time" / "tiempo completo" -> Full-time
- "Part-time" / "medio tiempo" -> Part-time
- "Contract" / "contrato" / "freelance" -> Contract
- "Internship" / "pasantía" / "practicante" -> Internship
Si no está explícito -> null.

Responde SOLO JSON: {"employment_type": "..."}"""

SALARY_PROMPT = """Extrae el SALARIO DEL PUESTO SOLO si está EXPLÍCITO con números.
- "Estimated base salary: $19,984,600 CRC annually" -> min/max + CRC + annual.
- "Hourly Rate: $10 to $23 USD per hour" -> min/max + USD + hourly.
- "Salary: ₡ 625000" -> 625000 + CRC + monthly (el símbolo ₡ es colón).
- Si la cifra trae "$" Y además un código de moneda (CRC/USD), manda el
  CÓDIGO: "$19,984,600 CRC" es CRC, no USD.
- Si solo hay un valor -> min = max.
- IGNORA cifras de ingresos, funding, ventas, clientes o tamaño de la empresa.
- IGNORA "paid time off", "paid shifts" y otros pagos que NO son salario.
Responde: min, max, currency (CRC/USD), period (monthly/annual/hourly).
Si no hay salario explícito -> todos null.

Responde SOLO JSON: {"salary_min": ..., "salary_max": ..., "salary_currency": "...", "salary_period": "..."}"""

SKILLS_PROMPT = """Extrae SOLO las skills TECNICAS que aparecen LITERALMENTE en el texto.
Reglas estrictas:
- NO inventes skills que no esten escritas en el texto.
- NO incluyas soft skills ni conceptos genericos.
- MAXIMO 10 skills, las mas importantes.
- Si no hay skills tecnicas claras -> lista vacia.
Responde SOLO JSON: {"skills": ["...", "..."]}"""

LANGUAGES_PROMPT = """Extrae idiomas CON NIVEL CEFR explícito (A1, A2, B1, B2, C1, C2, nativo).
Ejemplo: "Inglés B2", "English C1", "Español nativo".
Formato: {"ingles": "B2", "frances": "A2"}.
Si no hay nivel explícito -> no incluir.

Responde SOLO JSON: {"languages": {...}}"""


async def _extract_field(
    client: IAClient,
    system_prompt: str,
    user_text: str,
    schema: Dict,
    field_name: str,
    max_tokens: int = 300
) -> Optional[Dict]:
    """Extrae un campo individual con reintentos (3 intentos, backoff)."""
    ultimo_error = None
    for attempt in range(3):
        try:
            resp = await client.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                schema=schema,
                temperature=0.1,
                max_tokens=max_tokens
            )
            return resp
        except Exception as e:
            ultimo_error = e
            if attempt < 2:
                await asyncio.sleep(1.0 * (attempt + 1))  # 1s, 2s
    logger.warning(f"IA extract {field_name} fallo tras 3 intentos: {ultimo_error}")
    return None


async def enrich_job_fields(job: Dict[str, Any], client: IAClient) -> Dict[str, Any]:
    """Enriquece un job campo por campo (secuencial simple)."""
    filled = {}
    user_parts = []
    
    # Construir texto base una sola vez
    if job.get("title"):
        user_parts.append(f"TÍTULO: {job['title']}")
    if job.get("company"):
        user_parts.append(f"EMPRESA: {job['company']}")
    if job.get("location_raw"):
        user_parts.append(f"UBICACIÓN_RAW: {job['location_raw']}")
    if job.get("description_raw"):
        user_parts.append(f"DESCRIPCIÓN: {job['description_raw'][:2000]}")
    if job.get("requirements_raw"):
        user_parts.append(f"REQUISITOS: {job['requirements_raw'][:1500]}")
    if job.get("salary_raw"):
        user_parts.append(f"SALARIO: {job['salary_raw']}")
    
    full_text = "\n\n".join(user_parts)
    location_raw = job.get("location_raw", "")
    
    # 1. LOCATION (crítico)
    if job.get("city") is None and location_raw:
        location_text = f"Ubicación: {location_raw}"
        result = await _extract_field(client, LOCATION_PROMPT, location_text, LOCATION_SCHEMA, "location")
        if result and result.get("city") is not None:
            # La IA tambien mete basura: una planta ("Dry Plant"), una sede
            # ("BSC") o el nombre de la empresa no son ciudades. Pasa por la
            # misma puerta que el catalogo (bug corregido el 2026-11-01: 5
            # avisos con city="BSC" y 1 con "Dry Plant" venian de aqui).
            if ciudad_es_valida(
                result["city"], result.get("region"), job.get("company")
            ):
                filled["city"] = result["city"]
        if result and result.get("region") is not None:
            if es_provincia_valida(result["region"]):
                filled["region"] = result["region"]
    
    # 2. WORK_MODE (crítico)
    # Primero la regla determinista sobre el texto COMPLETO (la etiqueta
    # #LI-* suele ir al final, fuera del recorte de 2000 chars). Solo si no
    # hay marca literal se consulta al modelo.
    if job.get("work_mode") in (None, "", "unknown"):
        declarado = work_mode_por_patrones(
            job.get("description_raw"),
            job.get("requirements_raw"),
            job.get("title"),
        )
        if declarado:
            filled["work_mode"] = declarado
        else:
            result = await _extract_field(client, WORK_MODE_PROMPT, full_text, WORK_MODE_SCHEMA, "work_mode")
            if result and result.get("work_mode") != "unknown":
                filled["work_mode"] = result["work_mode"]
    
    # 3. DATE_PUBLISHED (crítico)
    if job.get("date_published") in (None, ""):
        result = await _extract_field(client, DATE_PROMPT, full_text, DATE_SCHEMA, "date_published")
        if result and result.get("date_published"):
            filled["date_published"] = result["date_published"]
    
    # 4. SECUNDARIOS (solo si el job no los tiene)
    
    # Employment type
    if not job.get("employment_type"):
        result = await _extract_field(client, EMPLOYMENT_PROMPT, full_text, EMPLOYMENT_SCHEMA, "employment_type", 150)
        if result and result.get("employment_type"):
            filled["employment_type"] = result["employment_type"]
    
    # Salary
    # La puerta NO es `salary_raw`: las APIs de empleo casi nunca lo traen
    # (0 de 354 avisos en la corrida por la UI del 2026-11-01) y los avisos
    # que SI declaran la compensacion la esconden en la descripcion
    # ("Estimated base salary: $19,984,600 CRC annually"). La señal es una
    # MARCA de salario + una MONEDA en el texto (jobpulse_v15.salario), que
    # es la MISMA regla que usa el contador de huecos (ia_estado).
    if job.get("salary_min") is None and (
        job.get("salary_raw")
        or declara_salario(
            job.get("description_raw"), job.get("requirements_raw")
        )
    ):
        # Al modelo se le manda el FRAGMENTO alrededor de la marca: la
        # seccion de compensacion suele ir al final del aviso, fuera de los
        # 2000 primeros caracteres que ve el recorte por defecto.
        contexto = contexto_salario(
            job.get("description_raw"), job.get("requirements_raw")
        )
        result = await _extract_field(
            client, SALARY_PROMPT, contexto or full_text, SALARY_SCHEMA, "salary", 200
        )
        if result and result.get("salary_min") is not None:
            filled["salary_min"] = result["salary_min"]
            filled["salary_max"] = result["salary_max"]
            filled["salary_currency"] = result["salary_currency"]
            filled["salary_period"] = result["salary_period"]
    
    # Skills
    # Skills 600 tokens: la lista puede ser larga y un JSON truncado
    # aborta el parseo (antes 300 truncaba y se perdian skills).
    if not job.get("skills") and (job.get("description_raw") or job.get("requirements_raw")):
        result = await _extract_field(client, SKILLS_PROMPT, full_text, SKILLS_SCHEMA, "skills", 600)
        if result and result.get("skills"):
            filled["skills"] = result["skills"]
    
    # Languages
    if not job.get("languages"):
        result = await _extract_field(client, LANGUAGES_PROMPT, full_text, LANGUAGES_SCHEMA, "languages", 200)
        if result and result.get("languages"):
            filled["languages"] = result["languages"]
    
    return filled


async def enrich_job(job: Dict[str, Any], client: IAClient) -> Optional[Dict[str, Any]]:
    """Enriquece un job campo por campo."""
    try:
        filled = await enrich_job_fields(job, client)
        return filled  # Return even empty dict for partial enrichment
    except Exception as e:
        logger.debug(f"IA enrich failed {job.get('job_id')}: {e}")
        return None


def needs_critical_enrichment(job: Dict[str, Any]) -> bool:
    """Verifica si el job necesita enriquecimiento CRÍTICO."""
    return (
        (job.get("city") is None and job.get("location_raw")) or
        job.get("work_mode") in (None, "", "unknown") or
        job.get("date_published") in (None, "")
    )


def needs_secondary_enrichment(job: Dict[str, Any]) -> bool:
    """Verifica si el job necesita campos SECUNDARIOS (solo pase completo)."""
    return (
        not job.get("employment_type") or
        (
            job.get("salary_min") is None
            and bool(
                job.get("salary_raw")
                or declara_salario(
                    job.get("description_raw"), job.get("requirements_raw")
                )
            )
        ) or
        not job.get("skills") or
        not job.get("languages")
    )


async def verificar_servidor_ia(client: IAClient) -> Optional[str]:
    """Preflight: verifica que el backend IA responde antes del pase.

    Devuelve None si responde, o un mensaje de error si no. Evita lanzar
    el pase completo cuando el backend esta apagado (mil fallas en fila).

    El mensaje distingue LOCAL (llama.cpp/LM Studio/Ollama local: hay que
    arrancar el proceso) de EXTERNO (Ollama Cloud, OpenRouter, Gemini…: hay
    que revisar la URL, el modelo y la API key).
    """
    try:
        await client.chat_json(
            messages=[
                {"role": "system", "content": "Responde SOLO JSON."},
                {"role": "user", "content": 'Responde: {"ok": true}'},
            ],
            schema={
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
                "additionalProperties": False,
            },
            temperature=0.0,
            max_tokens=20,
        )
        return None
    except Exception as e:
        base = getattr(client, "base_url", "?")
        modelo = getattr(client, "modelo", "?")
        if getattr(client, "es_local", False):
            return (
                f"El servidor IA local no responde en {base} "
                f"(modelo {modelo}): {e}. "
                "Arranca llama-server y reintenta."
            )
        return (
            f"El proveedor IA externo no responde en {base} "
            f"(modelo {modelo}): {e}. "
            "Verifica IA_BASE_URL / IA_MODEL y la API key del proveedor."
        )


def aviso_privacidad(client: Any) -> Optional[str]:
    """Texto de aviso cuando la IA NO es local (o ``None`` si es local).

    Con IA local (llama.cpp, LM Studio, Ollama local) el texto de los avisos
    NO sale de la máquina. Con un proveedor externo (Ollama Cloud, OpenRouter,
    Gemini, NVIDIA…) el texto viaja al servicio: hay que avisar ANTES de
    enviarlo, no después.
    """
    if client is None:
        return None
    if getattr(client, "es_local", False):
        return None
    proveedor = getattr(client, "proveedor", "") or "externo"
    nombre = PROVEEDOR_NOMBRES.get(proveedor, proveedor)
    base = getattr(client, "base_url", "?")
    return (
        f"IA externa ({nombre} — {base}): el TEXTO de los avisos "
        "(descripción, requisitos y datos del perfil) se enviará a ese "
        "servicio y sale de esta máquina. JobPulse no guarda el texto del "
        "mensaje, pero el proveedor sí recibe el prompt."
    )


def tope_vacantes(explicito: Optional[int] = None) -> Optional[int]:
    """Tope de avisos a enriquecer por corrida — OPT-IN y AJUSTABLE.

    ``None`` = SIN TOPE (se procesa todo lo pendiente). El valor sale de
    ``IA_MAX_VACANTES`` (``.env`` o la tarjeta "IA externa" de la UI v2);
    el usuario lo sube o lo baja cuando quiera. Un entero explícito
    (argumento) siempre gana; ``0`` o negativo = sin tope.
    """
    if explicito is not None:
        return explicito if explicito > 0 else None
    if opt_int is None:
        return None
    return opt_int(None, os.getenv("IA_MAX_VACANTES"))


def get_ia_client() -> Optional[IAClient]:
    """Crea cliente IA si está configurado.

    Carga ``.env`` aquí (y no solo en ``pase_completo``/``run_ia_enrichment``)
    porque el pre-chequeo de la UI llama a esta función ANTES de entrar al pase:
    sin esto, el proceso UI (que no hace ``load_dotenv`` al arrancar) veía
    ``os.getenv('IA_*')`` vacío y mostraba "IA no configurada" aunque el
    ``.env`` estuviera bien (bug 2026-10-28)."""
    from dotenv import load_dotenv
    load_dotenv()
    if not IA_AVAILABLE:
        return None
    try:
        return IAClient()
    except Exception as e:
        logger.warning(f"IA no configurada: {e}")
        return None


# Escaparate de guardado: campo IA -> (columna jobs, valor a escribir).
# skills/languages se serializan a JSON; el resto es texto/numero directo.
MAPEO_SAVE = {
    "city": ("city", lambda j: j.get("city")),
    "region": ("region", lambda j: j.get("region")),
    "work_mode": ("work_mode", lambda j: j.get("work_mode")),
    "date_published": ("date_published", lambda j: j.get("date_published")),
    "employment_type": ("employment_type", lambda j: j.get("employment_type")),
    "salary_min": ("salary_min", lambda j: j.get("salary_min")),
    "salary_max": ("salary_max", lambda j: j.get("salary_max")),
    "salary_currency": ("salary_currency", lambda j: j.get("salary_currency")),
    "salary_period": ("salary_period", lambda j: j.get("salary_period")),
    "skills": ("skills", lambda j: json.dumps(j.get("skills") or [], ensure_ascii=False)),
    "languages": ("languages", lambda j: json.dumps(j.get("languages") or {}, ensure_ascii=False)),
}


async def run_ia_enrichment(
    db_path: str = "data/jobpulse_v15.db",
    limit: int = 50,
    only_critical: bool = True,
    max_vacantes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Pipeline principal: carga jobs sin campos críticos, enriquece campo por campo, guarda.

    ``max_vacantes`` (o ``IA_MAX_VACANTES``) limita cuántos avisos se toman
    en esta llamada; es OPT-IN: sin valor no hay tope.
    """
    from dotenv import load_dotenv
    load_dotenv()  # asegura IA_* disponibles tambien desde UI/scripts

    if not IA_AVAILABLE:
        return {"error": "IA client no disponible (import failed)"}

    ia_client = get_ia_client()
    if not ia_client:
        return {"error": "IA no configurada (ver .env: IA_PROVEEDOR, IA_BASE_URL, IA_MODEL, IA_API_KEY)"}

    # Tope de avisos (opt-in, ajustable desde .env / UI).
    tope = tope_vacantes(max_vacantes)
    if tope is not None and tope < limit:
        limit = tope

    # Preflight: si el backend esta apagado, abortar de inmediato y no
    # generar una avalancha de fallos job por job.
    error_preflight = await verificar_servidor_ia(ia_client)
    if error_preflight:
        return {"error": error_preflight}
    
    from jobpulse_v15.db import Database
    from jobpulse_v15.repository import Repository
    
    db = Database(db_path)
    db.initialize()
    repo = Repository(db)
    
    # Cargar jobs que necesitan enriquecimiento
    with db.connection() as conn:
        conn.row_factory = __import__('sqlite3').Row
        cur = conn.cursor()
        
        if only_critical:
            cur.execute("""
                SELECT job_id FROM jobs
                WHERE (city IS NULL AND location_raw IS NOT NULL AND location_raw != '')
                   OR work_mode IS NULL OR work_mode = 'unknown' OR work_mode = ''
                   OR date_published IS NULL OR date_published = ''
                LIMIT ?
            """, (limit,))
        else:
            cur.execute("SELECT job_id FROM jobs LIMIT ?", (limit,))
        
        job_ids = [row[0] for row in cur.fetchall()]
    
    if not job_ids:
        return {"stats": {"total": 0, "seleccionados": 0, "enriched": 0, "skipped": 0, "failed": 0}, "message": "No hay jobs para enriquecer"}
    
    # Cargar jobs completos
    jobs = []
    for jid in job_ids:
        job = repo.get_job(jid)
        if not job:
            continue
        if only_critical:
            if needs_critical_enrichment(job):
                jobs.append(job)
        elif needs_critical_enrichment(job) or needs_secondary_enrichment(job):
            # Pase completo: tambien jobs que solo faltan secundarios.
            jobs.append(job)
    
    if not jobs:
        return {"stats": {"total": len(job_ids), "seleccionados": len(job_ids), "enriched": 0, "skipped": len(job_ids), "failed": 0}, "message": "Todos los jobs ya tienen campos críticos"}

    # Enriquecer en lotes
    stats = {"total": len(jobs), "seleccionados": len(job_ids), "enriched": 0, "skipped": 0, "failed": 0, "fields_filled": {"city": 0, "region": 0, "work_mode": 0, "date_published": 0, "employment_type": 0, "salary": 0, "skills": 0, "languages": 0}}
    
    batch_size = 3  # Lotes pequeños para modelo pequeño
    updated_jobs = []
    
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i+batch_size]
        logger.info(f"IA lote {i // batch_size + 1}/{-(-len(jobs) // batch_size)}: {len(batch)} jobs")
        
        # Procesar en paralelo dentro del lote
        tasks = [enrich_job(job, ia_client) for job in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for job, filled in zip(batch, results):
            if isinstance(filled, Exception) or not filled:
                stats["failed"] += 1
                continue

            # Merge: solo llenar lo que falte y anotar SOLO los campos
            # realmente cambiados (lo que governa el UPDATE posterior).
            tocado = []
            for field, value in filled.items():
                if field not in MAPEO_SAVE or value in (None, "", [], {}):
                    continue
                if field == "work_mode":
                    vacio = job.get(field) in (None, "", "unknown")
                elif field in ("salary_min", "salary_max", "salary_currency", "salary_period"):
                    vacio = job.get(field) is None
                else:
                    vacio = job.get(field) in (None, "", [], {})
                if not vacio:
                    continue
                job[field] = value
                tocado.append(field)
            if not tocado:
                stats["skipped"] += 1  # la IA no devolvio nada nuevo
                continue
            job["_ia_fields_filled"] = tocado
            stats["enriched"] += 1
            for field in tocado:
                if field.startswith("salary"):
                    continue  # el grupo se cuenta 1 vez por job
                if field in stats["fields_filled"]:
                    stats["fields_filled"][field] += 1
            if any(f.startswith("salary") for f in tocado):
                stats["fields_filled"]["salary"] += 1
            updated_jobs.append(job)

    # Guardar en BD: SOLO las columnas tocadas (nunca sobreescribir
    # skills/languages con 'null' por campos que no se consultaron).
    db_updated = 0
    from jobpulse_v15.db import Database
    db = Database(db_path)
    for job in updated_jobs:
        tocado = job.get("_ia_fields_filled") or []
        columnas = [MAPEO_SAVE[f][0] for f in tocado]
        valores = [MAPEO_SAVE[f][1](job) for f in tocado]
        with db.connection() as conn:
            conn.execute(
                f"UPDATE jobs SET {', '.join(c + ' = ?' for c in columnas)}"
                " WHERE job_id = ?",
                (*valores, job["job_id"]),
            )
            if conn.total_changes > 0:
                db_updated += 1
    
    stats["db_updated"] = db_updated
    return {"stats": stats, "message": f"Enriquecidos {stats['enriched']}/{stats['total']}, BD actualizados: {db_updated}"}


async def pase_completo(
    solo_criticos: bool = False,
    on_event=None,
    max_vacantes: Optional[int] = None,
    db_path: str = "data/jobpulse_v15.db",
) -> Dict[str, Any]:
    """Orquestación completa del enriquecimiento (compartida CLI/UI, O7.3).

    1) Pase CRÍTICO (city/region/work_mode/date_published) en ciclos hasta que
    deje de avanzar (los 'unknown' irresolubles no se reintentan eternamente).
    2) Pase COMPLETO (secundarios incluidos: employment_type, salary, skills,
    languages) para los jobs que les falte algo.

    ``on_event(texto)`` recibe el avance ciclo por ciclo (para logs o UI).
    ``max_vacantes`` (o ``IA_MAX_VACANTES``) es el tope de avisos de la
    corrida: OPT-IN y AJUSTABLE — sin valor no hay tope (se procesa todo lo
    pendiente). Devuelve ``{"ciclos": [stats...], "completo": stats | None}`` o
    ``{"error": ...}`` (con lo acumulado hasta el fallo, si hubo).
    """
    def _reporta(texto: str) -> None:
        if on_event:
            try:
                on_event(texto)
            except Exception:  # la UI/log nunca debe romper el pase
                pass

    from dotenv import load_dotenv
    load_dotenv()  # el proceso UI no carga .env; mismo patrón que run_ia_enrichment

    cliente = get_ia_client()
    if not cliente:
        return {"error": "IA no configurada (ver .env: IA_PROVEEDOR, IA_BASE_URL, IA_MODEL)"}
    es_local = bool(getattr(cliente, "es_local", False))
    _reporta(
        f"{'Servidor' if es_local else 'Proveedor'} IA: "
        f"{getattr(cliente, 'base_url', '?')} | "
        f"modelo: {getattr(cliente, 'modelo', '?')}"
    )
    aviso = aviso_privacidad(cliente)
    if aviso:
        _reporta(f"⚠️ {aviso}")
    tope = tope_vacantes(max_vacantes)
    if tope is None:
        _reporta("Tope de avisos: SIN TOPE (se procesa todo lo pendiente).")
    else:
        _reporta(
            f"Tope de avisos por corrida: {tope} (opt-in; se ajusta con "
            "IA_MAX_VACANTES en .env o en Configuración → IA externa)."
        )
    error = await verificar_servidor_ia(cliente)
    if error:
        return {"error": error}
    _reporta("Preflight OK: el backend responde.")

    resumen: Dict[str, Any] = {"ciclos": [], "completo": None}
    if tope is not None:
        resumen["tope_vacantes"] = tope
    restante = tope
    ciclo = 0
    while True:
        ciclo += 1
        limite = 500 if restante is None else min(500, restante)
        if limite <= 0:
            _reporta("Tope de avisos alcanzado: se detiene el pase crítico.")
            break
        r = await run_ia_enrichment(limit=limite, only_critical=True,
                                    db_path=db_path)
        if "error" in r:
            return {"error": f"CRÍTICO ciclo {ciclo}: {r['error']}", **resumen}
        s = r["stats"]
        resumen["ciclos"].append(s)
        _reporta(
            f"CRÍTICO ciclo {ciclo}: total={s['total']} enriched={s['enriched']} "
            f"failed={s['failed']} skipped={s['skipped']} "
            f"fills={json.dumps(s.get('fields_filled', {}), ensure_ascii=False)}"
        )
        if restante is not None:
            restante = max(
                0, restante - int(s.get("seleccionados", s.get("total", 0)) or 0)
            )
        if s["total"] == 0 or s["enriched"] == 0:
            break
        if ciclo >= 5:  # guardia de seguridad
            break

    if not solo_criticos:
        limite = 2000 if restante is None else min(2000, restante)
        r = await run_ia_enrichment(limit=limite, only_critical=False,
                                    db_path=db_path)
        if "error" in r:
            return {"error": f"COMPLETO: {r['error']}", **resumen}
        s = r["stats"]
        resumen["completo"] = s
        _reporta(
            f"COMPLETO: total={s['total']} enriched={s['enriched']} "
            f"failed={s['failed']} skipped={s['skipped']} "
            f"fills={json.dumps(s.get('fields_filled', {}), ensure_ascii=False)}"
        )
    return resumen


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    
    result = asyncio.run(run_ia_enrichment(limit=5))
    print(json.dumps(result, indent=2, ensure_ascii=False))