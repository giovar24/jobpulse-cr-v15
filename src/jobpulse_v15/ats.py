# -*- coding: utf-8 -*-
"""jobpulse_v15.ats — Scoring tipo ATS (Applicant Tracking System).

Implementa evaluacion ponderada estilo ATS reales (Oracle AI Rating, Eightfold,
experimentos LiveCareer/ResumeWorded):

Componentes y pesos default (suman 1.0):
- Hard Skills / Keywords:       40%  (coincidencia de requisitos explicitos)
- Titulo del puesto:            30%  (similitud semantica via embeddings)
- Experiencia (anos vs min):    15%  (cobertura del minimo requerido)
- Educacion (nivel vs req):     7.5% (jerarquia: doctorado > master > bachelor > tecnico > bachiller)
- Idiomas (nivel explicito):    7.5% (coincidencia codigo + nivel >= requerido)

Umbrales de veredicto:
- >= 85  -> "Fuerte" (Strong match)
- 70-84  -> "Ajustable" (Good match, mejorar keywords)
- < 70   -> "Debil" / "Rechazo probable" (Weak match)

El score es 0-100. Componentes ausentes en la vacante se redistribuyen.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

import numpy as np

from jobpulse_v15.search_engine import SemanticSearchEngine

logger = logging.getLogger("jobpulse.ats")


# ----------------------------------------------------------------------
# Pesos default (suman 1.0)
# ----------------------------------------------------------------------
DEFAULT_WEIGHTS = {
    "skills": 0.40,
    "title": 0.30,
    "experience": 0.15,
    "education": 0.075,
    "languages": 0.075,
}

# Veredicto thresholds
VEREDICTO_THRESHOLDS = {
    "fuerte": 85.0,
    "ajustable": 70.0,
    # <70 = debil
}

# Jerarquia educacion (mayor = mejor)
EDUCATION_HIERARCHY = {
    "doctorado": 6,
    "phd": 6,
    "doctorate": 6,
    "maestria": 5,
    "master": 5,
    "postgrado": 5,
    "posgrado": 5,
    "licenciatura": 4,
    "bachelor": 4,
    "grado": 4,
    "universitario": 4,
    "tecnologo": 3,
    "tecnico superior": 3,
    "tecnico": 2,
    "tecnico medio": 2,
    "bachillerato": 1,
    "bachiller": 1,
    "high school": 1,
    "secundaria": 0,
}

# Jerarquia idiomas (CEFR + coloquial)
LANGUAGE_HIERARCHY = {
    "nativo": 5,
    "native": 5,
    "c2": 5,
    "c1": 4,
    "avanzado": 4,
    "advanced": 4,
    "fluido": 4,
    "fluent": 4,
    "b2": 3,
    "intermedio alto": 3,
    "upper intermediate": 3,
    "b1": 2,
    "intermedio": 2,
    "intermediate": 2,
    "a2": 1,
    "basico": 1,
    "basic": 1,
    "a1": 1,
    "principiante": 1,
    "beginner": 1,
}


@dataclass
class ATSScore:
    """Resultado del scoring ATS."""
    total: float                    # 0-100
    veredicto: str                  # "fuerte" | "ajustable" | "debil"
    skills_pct: float               # 0-100
    title_pct: float                # 0-100
    experience_pct: float           # 0-100
    education_pct: float            # 0-100
    languages_pct: float            # 0-100
    missing_keywords: List[str]     # keywords de la vacante no cubiertas por el perfil
    details: Dict[str, Any]         # info extra por componente


# ----------------------------------------------------------------------
# Lexico de habilidades tecnicas (hard skills) - ES + EN
# ----------------------------------------------------------------------
SKILL_LEXICON: Set[str] = {
    # Lenguajes
    "python", "java", "javascript", "typescript", "c#", "csharp", "c++", "cpp",
    "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "scala", "r",
    "matlab", "sql", "nosql", "bash", "powershell", "perl", "lua", "dart",
    # Frameworks web
    "react", "reactjs", "angular", "vue", "vuejs", "svelte", "nextjs", "next.js",
    "django", "flask", "fastapi", "spring", "spring boot", "express", "nestjs",
    "laravel", "symfony", "rails", "asp.net", ".net core", "blazor",
    # Cloud / DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "jenkins", "gitlab ci", "github actions", "circleci",
    "argocd", "helm", "prometheus", "grafana", "elk", "datadog", "new relic",
    "ci/cd", "ci cd", "pipeline", "infrastructure as code", "iac",
    # Bases de datos
    "postgresql", "postgres", "mysql", "mariadb", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "oracle", "sql server", "sqlite", "neo4j", "firebase",
    "supabase", "planetscale",
    # Data / ML
    "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow", "pytorch", "keras",
    "xgboost", "lightgbm", "catboost", "huggingface", "transformers", "langchain",
    "spark", "databricks", "snowflake", "bigquery", "redshift", "airflow", "kafka",
    # Testing / QA
    "pytest", "jest", "cypress", "playwright", "selenium", "junit", "testng",
    "postman", "newman", "k6", "locust", "sonarqube",
    # Otros
    "git", "github", "gitlab", "bitbucket", "jira", "confluence", "agile", "scrum",
    "kanban", "jira", "confluence", "linux", "windows", "macos", "unix",
    "api rest", "rest api", "graphql", "grpc", "websockets", "microservicios",
    "microservices", "event driven", "event-driven", "message queue", "rabbitmq",
    "sqoop", "hadoop", "hive", "pig", "tableau", "power bi", "looker", "metabase",
}


def _normalize_skill(s: str) -> str:
    """Normaliza skill para comparacion (lower, sin acentos, alfanumerico + espacios)."""
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9\s\+\#\.]", " ", s).strip()


def _extract_skills_from_text(text: str) -> Set[str]:
    """Extrae skills del lexicon presentes en el texto (word boundary)."""
    if not text:
        return set()
    found = set()
    text_norm = _normalize_skill(text)
    for skill in SKILL_LEXICON:
        skill_norm = _normalize_skill(skill)
        # Word boundary para multi-palabra
        pattern = r"(^|\s)" + re.escape(skill_norm) + r"(\s|$|[.,;:])"
        if re.search(pattern, " " + text_norm + " "):
            found.add(skill)
    return found


# ----------------------------------------------------------------------
# Extraccion de requisitos de la vacante
# ----------------------------------------------------------------------
def job_keywords(job: Dict[str, Any]) -> Set[str]:
    """Hard skills de la oferta = coincidencias del lexicon en titulo+desc+reqs."""
    text = " ".join(filter(None, [
        job.get("title", ""),
        job.get("description_raw", ""),
        job.get("requirements_raw", ""),
    ]))
    return _extract_skills_from_text(text)


def _covered(profile_skills: Set[str], keyword: str) -> bool:
    """Cobertura multipalabra: 'Soporte Tecnico' cubre 'soporte'; 'Help Desk' cubre 'helpdesk'."""
    kw_norm = _normalize_skill(keyword)
    for ps in profile_skills:
        ps_norm = _normalize_skill(ps)
        if kw_norm in ps_norm or ps_norm in kw_norm:
            return True
    return False


def extract_years_required(job: Dict[str, Any]) -> Optional[int]:
    """Extrae anos de experiencia requeridos de la vacante (regex)."""
    text = " ".join(filter(None, [
        job.get("description_raw", ""),
        job.get("requirements_raw", ""),
    ]))
    if not text:
        return None
    # Patrones: "N anos", "N años", "N+ anos", "minimum N years", "N+ years"
    patterns = [
        r"(\d+)\s*\+\s*a[nn]os?",
        r"(\d+)\s*a[nn]os?",
        r"minimum\s+(\d+)\s*years?",
        r"at least\s+(\d+)\s*years?",
        r"(\d+)\s*\+\s*years?",
        r"(\d+)\s*years?\s*(experience|experiencia)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


def extract_education_required(job: Dict[str, Any]) -> Optional[str]:
    """Extrae nivel educativo requerido (normalizado a clave de EDUCATION_HIERARCHY)."""
    text = " ".join(filter(None, [
        job.get("description_raw", ""),
        job.get("requirements_raw", ""),
    ])).lower()
    if not text:
        return None
    # Buscar nivel mas alto mencionado
    found_level = None
    found_val = -1
    for level, val in EDUCATION_HIERARCHY.items():
        # Word boundary aproximado
        if re.search(rf"\b{re.escape(level)}\b", text):
            if val > found_val:
                found_val = val
                found_level = level
    return found_level


def extract_languages_required(job: Dict[str, Any]) -> Dict[str, str]:
    """Extrae idiomas requeridos con nivel: {'ingles': 'b2', 'frances': 'a2'}."""
    text = " ".join(filter(None, [
        job.get("description_raw", ""),
        job.get("requirements_raw", ""),
    ])).lower()
    if not text:
        return {}

    # Patrones: "ingles b2", "english c1", "nivel b2 ingles", "fluido en ingles"
    lang_pattern = re.compile(
        r"\b(ingles|english|espanol|spanish|frances|french|aleman|german|portugues|portuguese|italiano|italian|chino|chinese|japones|japanese)\b"
        r".{0,30}?"
        r"\b(nativo|native|c2|c1|avanzado|advanced|fluido|fluent|b2|intermedio alto|upper intermediate|b1|intermedio|intermediate|a2|basico|basic|a1|principiante|beginner)\b"
    )
    found = {}
    for m in lang_pattern.finditer(text):
        lang_raw = m.group(1)
        level_raw = m.group(2)
        # Normalizar idioma
        lang_map = {
            "ingles": "ingles", "english": "ingles",
            "espanol": "espanol", "spanish": "espanol",
            "frances": "frances", "french": "frances",
            "aleman": "aleman", "german": "aleman",
            "portugues": "portugues", "portuguese": "portugues",
            "italiano": "italiano", "italian": "italiano",
            "chino": "chino", "chinese": "chino",
            "japones": "japones", "japanese": "japones",
        }
        lang = lang_map.get(lang_raw, lang_raw)
        level = level_raw
        if lang not in found or LANGUAGE_HIERARCHY.get(level, 0) > LANGUAGE_HIERARCHY.get(found[lang], 0):
            found[lang] = level
    return found


def title_semantic_match(profile_titles: List[str], job_title: str, engine: SemanticSearchEngine) -> float:
    """Similitud coseno entre titulos del perfil y titulo de la vacante (0-1)."""
    if not profile_titles or not job_title:
        return 0.0
    # Embedding del titulo de la vacante
    job_emb = engine._model.encode([engine._get_doc_prompt() + job_title], convert_to_numpy=True, normalize_embeddings=True)[0]
    # Embeddings de titulos del perfil
    profile_embs = engine._model.encode([engine._get_query_prompt() + t for t in profile_titles], convert_to_numpy=True, normalize_embeddings=True)
    # Max similitud
    sims = profile_embs @ job_emb
    return float(np.max(sims))


def title_semantic_match_simple(profile_titles: List[str], job_title: str) -> float:
    """Fallback simple sin embeddings: overlap de tokens normalizados."""
    if not profile_titles or not job_title:
        return 0.0
    job_tokens = set(_normalize_skill(job_title).split())
    best = 0.0
    for pt in profile_titles:
        pt_tokens = set(_normalize_skill(pt).split())
        if not job_tokens or not pt_tokens:
            continue
        overlap = len(job_tokens & pt_tokens) / len(job_tokens | pt_tokens)
        best = max(best, overlap)
    return best


# ----------------------------------------------------------------------
# Scoring principal
# ----------------------------------------------------------------------
def ats_score(
    profile: Dict[str, Any],
    job: Dict[str, Any],
    engine: Optional[SemanticSearchEngine] = None,
    weights: Optional[Dict[str, float]] = None,
) -> ATSScore:
    """
    Calcula score ATS 0-100 con desglose por componente.

    profile: dict con claves opcionales:
        - skills: List[str]           (hard skills del candidato)
        - titulos: List[str]          (titulos objetivo / historicos)
        - experiencia_anios: int      (anos de experiencia total)
        - educacion_nivel: str        (clave de EDUCATION_HIERARCHY)
        - idiomas: Dict[str, str]     # {'ingles': 'c1', 'frances': 'b2'}
        - pesos_ats: Dict[str, float] # override de DEFAULT_WEIGHTS

    job: dict normalizado de la vacante (title, description_raw, requirements_raw, etc.)

    engine: SemanticSearchEngine para similitud de titulo (opcional; si None usa fallback simple)
    weights: override de pesos (skills, title, experience, education, languages)
    """
    w = weights or profile.get("pesos_ats", DEFAULT_WEIGHTS).copy()
    # Normalizar pesos de componentes presentes
    active = {k: v for k, v in w.items() if v > 0}
    total_w = sum(active.values()) or 1.0
    w = {k: v / total_w for k, v in active.items()}

    # 1. SKILLS (40%)
    job_kws = job_keywords(job)
    profile_skills = set(profile.get("skills", []))
    if job_kws:
        covered = sum(1 for kw in job_kws if _covered(profile_skills, kw))
        skills_pct = 100.0 * covered / len(job_kws)
        missing = [kw for kw in job_kws if not _covered(profile_skills, kw)]
    else:
        skills_pct = 100.0  # sin requisitos tecnicos = full
        missing = []

    # 2. TITLE (30%)
    profile_titles = profile.get("titulos", [])
    job_title = job.get("title", "")
    if engine and profile_titles and job_title:
        title_pct = 100.0 * title_semantic_match(profile_titles, job_title, engine)
    else:
        title_pct = 100.0 * title_semantic_match_simple(profile_titles, job_title)

    # 3. EXPERIENCE (15%)
    req_years = extract_years_required(job)
    cand_years = profile.get("experiencia_anios")
    if req_years is not None and cand_years is not None:
        if cand_years >= req_years:
            experience_pct = 100.0
        else:
            experience_pct = max(0.0, 100.0 * cand_years / req_years)
    elif req_years is None:
        experience_pct = 100.0  # no especifica requisito
    else:
        experience_pct = 50.0   # vacante pide exp pero perfil no la tiene

    # 4. EDUCATION (7.5%)
    req_edu = extract_education_required(job)
    cand_edu = profile.get("educacion_nivel")
    if req_edu and cand_edu:
        req_val = EDUCATION_HIERARCHY.get(req_edu, 0)
        cand_val = EDUCATION_HIERARCHY.get(cand_edu, 0)
        if cand_val >= req_val:
            education_pct = 100.0
        else:
            education_pct = max(0.0, 100.0 * cand_val / max(req_val, 1))
    elif req_edu is None:
        education_pct = 100.0
    else:
        education_pct = 0.0

    # 5. LANGUAGES (7.5%)
    req_langs = extract_languages_required(job)
    cand_langs = profile.get("idiomas", {})
    if req_langs:
        lang_scores = []
        for lang, req_level in req_langs.items():
            cand_level = cand_langs.get(lang, "")
            req_val = LANGUAGE_HIERARCHY.get(req_level, 0)
            cand_val = LANGUAGE_HIERARCHY.get(cand_level, 0)
            if cand_val >= req_val:
                lang_scores.append(100.0)
            else:
                lang_scores.append(max(0.0, 100.0 * cand_val / max(req_val, 1)))
        languages_pct = sum(lang_scores) / len(lang_scores) if lang_scores else 100.0
    else:
        languages_pct = 100.0

    # Total ponderado
    total = (
        w.get("skills", 0) * skills_pct +
        w.get("title", 0) * title_pct +
        w.get("experience", 0) * experience_pct +
        w.get("education", 0) * education_pct +
        w.get("languages", 0) * languages_pct
    )

    # Veredicto
    if total >= VEREDICTO_THRESHOLDS["fuerte"]:
        veredicto = "fuerte"
    elif total >= VEREDICTO_THRESHOLDS["ajustable"]:
        veredicto = "ajustable"
    else:
        veredicto = "debil"

    return ATSScore(
        total=round(total, 1),
        veredicto=veredicto,
        skills_pct=round(skills_pct, 1),
        title_pct=round(title_pct, 1),
        experience_pct=round(experience_pct, 1),
        education_pct=round(education_pct, 1),
        languages_pct=round(languages_pct, 1),
        missing_keywords=sorted(missing),
        details={
            "job_keywords": sorted(job_kws),
            "profile_skills": sorted(profile_skills),
            "req_years": req_years,
            "cand_years": cand_years,
            "req_education": req_edu,
            "cand_education": cand_edu,
            "req_languages": req_langs,
            "cand_languages": cand_langs,
            "weights_used": w,
        }
    )


def rank_with_ats(
    jobs: List[Dict],
    profile: Dict[str, Any],
    engine: Optional[SemanticSearchEngine] = None,
    weights: Optional[Dict[str, float]] = None,
    semantic_weight: float = 0.6,
) -> List[Dict]:
    """
    Reordena jobs combinando score semantico (0-1) + ATS (0-100).

    Combinado = semantic_weight * (semantic_score * 100) + (1 - semantic_weight) * ats_score
    """
    for job in jobs:
        ats = ats_score(profile, job, engine, weights)
        job["ats_score"] = ats.total
        job["ats_veredicto"] = ats.veredicto
        job["ats_missing"] = ats.missing_keywords
        job["ats_skills_pct"] = ats.skills_pct
        job["ats_title_pct"] = ats.title_pct

    # Asumimos que job ya tiene 'semantic_score' (0-1) del search_engine
    for job in jobs:
        sem = job.get("semantic_score", 0.0) or 0.0
        ats = job.get("ats_score", 0.0) or 0.0
        job["combined_score"] = round(semantic_weight * (sem * 100) + (1 - semantic_weight) * ats, 1)

    jobs.sort(key=lambda j: -j.get("combined_score", 0))
    return jobs


# ===========================================================================
# RANKING ATS SOBRE LOS REQUISITOS REALES DEL AVISO (redefine O2/O4)
# ===========================================================================
#
# `ats_score` (arriba) es el scoring de laboratorio: compara contra un
# LEXICO de skills en ingles. Ese lexico no cubre el perfil real del usuario
# (Active Directory, ServiceNow, SCCM, Intune, Citrix...), por lo que el
# ranking que usa la UI v2 entra por otra via: los REQUISITOS REALES extraidos
# de cada aviso (con evidencia) y, cuando el aviso no trae requisitos
# obligatorios, las skills que el extractor leyo de su descripcion
# (`jobs.skills`).
#
# Reglas que este ranking respeta (heredadas del repo):
# * Un componente SIN DATO no penaliza: se excluye del calculo y su peso se
#   redistribuye (nunca "descartar por falta de informacion").
# * "Preferred" NO es requisito: no bloquea ni resta.
# * El idioma del aviso es el requisito de idioma, salvo que el aviso pida
#   idiomas (lo resuelve `Repository._requisitos_con_regla_de_idioma`).
# * El score es un RANKING, no una calificacion: no toca los umbrales
#   congelados del Paso 5 (cobertura 0.60 / puntaje 0.80).

PESOS_RANKING: Dict[str, float] = {
    "semantica": 0.35,
    "skills": 0.45,
    "experiencia": 0.10,
    "educacion": 0.05,
    "idiomas": 0.05,
}

ETIQUETAS_COMPONENTE: Dict[str, str] = {
    "semantica": "Semántica (perfil ↔ aviso)",
    "skills": "Skills",
    "experiencia": "Experiencia",
    "educacion": "Educación",
    "idiomas": "Idiomas",
}

VEREDICTO_SIN_DATOS = "sin_datos"

# Umbrales del RANKING (distintos de los del scoring de laboratorio y de los
# del Paso 5: aqui el score ordena avisos, no califica a nadie). Calibrados
# sobre la distribucion real del corpus (percentiles 70 y 90).
UMBRALES_RANKING: Dict[str, float] = {
    "fuerte": 50.0,
    "ajustable": 42.0,
}

# Niveles educativos que aparecen en el corpus de avisos (codigos canonicos).
# Las claves van YA normalizadas (sin acentos, con espacios).
EDUCATION_HIERARCHY.setdefault("diplomado", 2)
EDUCATION_HIERARCHY.setdefault("university degree", 4)
EDUCATION_HIERARCHY.setdefault("technical degree", 3)
EDUCATION_HIERARCHY.setdefault("secondary", 1)
EDUCATION_HIERARCHY.setdefault("postgraduate", 5)

# Codigos de idioma de los hechos del perfil -> codigos canonicos del aviso.
CODIGO_IDIOMA_PERFIL: Dict[str, str] = {
    "espanol": "es", "spanish": "es", "es": "es", "castellano": "es",
    "ingles": "en", "english": "en", "en": "en",
    "frances": "fr", "french": "fr", "fr": "fr",
    "aleman": "de", "german": "de", "de": "de",
    "portugues": "pt", "portuguese": "pt", "pt": "pt",
    "italiano": "it", "italian": "it", "it": "it",
}

# Nivel del hecho del perfil -> clave de LANGUAGE_HIERARCHY.
NIVEL_IDIOMA_PERFIL: Dict[str, str] = {
    "nativo": "nativo", "native": "nativo",
    "c2": "c2", "c1": "c1",
    "avanzado": "advanced", "advanced": "advanced",
    "fluido": "fluent", "fluent": "fluent",
    "b2": "b2", "intermedio alto": "b2",
    "b1": "b1", "intermedio": "b1", "intermediate": "b1",
    "a2": "a2", "basico": "basic", "basic": "basic",
    "a1": "a1", "principiante": "beginner", "beginner": "beginner",
}

# Palabras que NO distinguen una competencia: fabricantes, genericas y relleno.
STOPWORDS_SKILL = frozenset({
    "microsoft", "google", "office", "amazon", "meta", "microsoft",
    "software", "system", "systems", "sistema", "sistemas",
    "herramientas", "tools", "conocimientos", "conocimiento",
    "knowledge", "experience", "experiencia", "capacidad", "capacidades",
    "skills", "habilidades", "aptitudes", "ability", "abilities",
    "manejo", "uso", "use", "familiaridad", "expertise",
})

# Reemplazos sobre el texto normalizado (el nombre largo manda).
REEMPLAZOS_SKILL = (
    ("amazon web services", "aws"),
    ("amazon aws", "aws"),
    ("microsoft office", "office"),
    ("microsoft azure", "azure"),
    ("microsoft excel", "excel"),
    ("microsoft sql server", "sql server"),
    ("google cloud platform", "gcp"),
    ("google cloud", "gcp"),
)

# ``jobs.skills`` mezcla HERRAMIENTAS (Active Directory, ServiceNow, SQL
# Server) con FRASES DE TAREA ("elaborar cotizaciones", "soporte a equipos
# Dell", "reconciling balance sheet accounts"). Una frase de tarea no es una
# competencia verificable: contarla en el denominador del gap de skills
# penaliza a todos los avisos por igual y esconde los gaps reales.
FRASES_DE_TAREA = re.compile(
    r"\b("
    r"elabor\w*|manejo|manej\w*|gesti[oó]n|administra\w*|soporte a|apoyo a|"
    r"preparaci[oó]n|dise[ñn]o de|realizaci[oó]n|coordinaci[oó]n|"
    r"conciliaci[oó]n|redacci[oó]n|resoluci[oó]n|diagn[oó]stico de|"
    r"soluci[oó]n de|escalamiento|cumplimiento de|control de|monitoreo de|"
    r"seguimiento de|an[aá]lisis de|reporte de|reportes de|"
    r"preparar|prepar\w+|reconcil\w+|manag\w+|administrat\w+|handling|"
    r"processing|scheduling|tracking|reporting|supporting|assisting|"
    r"performing|executing|maintaining|monitoring|escalat\w+|drafting|"
    r"reviewing|auditing"
    r")\b"
)

# A partir de este numero de palabras la etiqueta ya no es una competencia
# ("account and inventory reconciliation activities"): es una frase.
MAX_PALABRAS_SKILL = 3


def es_frase_de_tarea(texto: str) -> bool:
    """True si la etiqueta de skill es una TAREA y no una competencia."""
    limpio = _normalize_skill(str(texto or ""))
    if not limpio:
        return True
    if FRASES_DE_TAREA.search(limpio):
        return True
    if len(limpio.split()) > MAX_PALABRAS_SKILL:
        return True
    return not _tokens_skill(texto)


def skills_utiles(skills: Sequence[str]) -> List[str]:
    """Filtra las skills del aviso: deja las competencias, quita las tareas."""
    utiles: List[str] = []
    for skill in skills or ():
        texto = str(skill or "").strip()
        if not texto or texto in utiles:
            continue
        if es_frase_de_tarea(texto):
            continue
        utiles.append(texto)
    return utiles


def promedios_componentes(
    desgloses: Sequence["DesgloseATS"]
) -> Dict[str, float]:
    """Promedio de cada componente entre los avisos del corpus.

    Sirve para IMPUTAR: un aviso que no tiene el dato (p. ej. no pide años
    de experiencia) toma el promedio del corpus. El score sigue siendo
    comparable entre avisos y la falta de informacion ni premia ni castiga.
    """
    sumas: Dict[str, float] = {}
    conteos: Dict[str, int] = {}
    for desglose in desgloses or ():
        for clave, componente in desglose.componentes.items():
            if componente.pct is None:
                continue
            sumas[clave] = sumas.get(clave, 0.0) + float(componente.pct)
            conteos[clave] = conteos.get(clave, 0) + 1
    return {
        clave: round(sumas[clave] / conteos[clave], 1)
        for clave in sumas
        if conteos.get(clave)
    }


def percentiles(valores: Sequence[float]) -> List[float]:
    """Percentil 0-100 de cada valor dentro del corpus (rank based).

    Los cosenos de embeddings viven comprimidos (0.1-0.6 para 535 avisos):
    como valor absoluto no distinguen nada. El percentil los hace
    comparables y reparte el componente semantico en todo el rango.
    """
    datos = [float(v) for v in valores]
    total = len(datos)
    if total == 0:
        return []
    if total == 1:
        return [100.0]
    orden = sorted(range(total), key=lambda i: datos[i])
    rangos = [0.0] * total
    i = 0
    while i < total:
        j = i
        while j + 1 < total and datos[orden[j + 1]] == datos[orden[i]]:
            j += 1
        # Empate: todos comparten el percentil promedio del tramo.
        promedio = (i + j) / 2.0
        pct = 100.0 * promedio / (total - 1)
        for k in range(i, j + 1):
            rangos[orden[k]] = pct
        i = j + 1
    return rangos


@dataclass
class ComponenteATS:
    """Un componente del score: ``pct`` None = sin dato (no penaliza)."""

    nombre: str
    pct: Optional[float]
    detalle: str = ""


@dataclass
class RankingATS:
    """Resultado del ranking ATS de una vacante contra el perfil."""

    total: Optional[float]
    veredicto: str
    componentes: Dict[str, ComponenteATS]
    skills_cubiertas: List[str]
    skills_faltantes: List[str]
    pesos_usados: Dict[str, float]

    @property
    def sin_datos(self) -> bool:
        return self.total is None


def _tokens_skill(texto: str) -> Set[str]:
    """Tokens significativos de una competencia (sin acentos ni relleno)."""
    if not texto:
        return set()
    normalizado = _normalize_skill(str(texto))
    for viejo, nuevo in REEMPLAZOS_SKILL:
        normalizado = normalizado.replace(viejo, nuevo)
    return {
        token
        for token in normalizado.split()
        if token and token not in STOPWORDS_SKILL
    }


def _cubre(tokens_vacante: Set[str], tokens_perfil: Sequence[Set[str]]) -> bool:
    """True si alguna skill del perfil cubre la del aviso (subconjunto)."""
    if not tokens_vacante:
        return False
    for tokens in tokens_perfil:
        if not tokens:
            continue
        if tokens_vacante <= tokens or tokens <= tokens_vacante:
            return True
    return False




def _coincide_con_perfil(texto: str, tokens_perfil: Sequence[Set[str]]) -> bool:
    """True si la skill del aviso es una de las que declara el perfil."""
    tokens = _tokens_skill(texto)
    if not tokens:
        return False
    for tokens_skill in tokens_perfil:
        if not tokens_skill:
            continue
        if tokens <= tokens_skill or tokens_skill <= tokens:
            return True
    return False


def cobertura_skills(
    skills_vacante: Sequence[str], skills_perfil: Sequence[str]
) -> Tuple[Optional[float], List[str], List[str]]:
    """Coteja las skills del aviso con las del perfil.

    Devuelve ``(pct, cubiertas, faltantes)``. El porcentaje cuenta cada
    CONCEPTO una sola vez: "Microsoft Excel" y "Excel avanzado" son la misma
    competencia (la del perfil), no dos. ``pct`` es None si el aviso no
    declara ninguna skill (componente sin dato: no penaliza).
    """
    tokens_perfil = [(skill, _tokens_skill(skill)) for skill in skills_perfil]
    conceptos: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for skill in skills_vacante:
        texto = str(skill).strip()
        if not texto:
            continue
        tokens = _tokens_skill(texto)
        if not tokens:
            continue
        cubierto_por: Optional[Tuple[str, Set[str]]] = None
        for nombre, tokens_perfil_skill in tokens_perfil:
            if not tokens_perfil_skill:
                continue
            if tokens <= tokens_perfil_skill or tokens_perfil_skill <= tokens:
                cubierto_por = (nombre, tokens_perfil_skill)
                break
        if cubierto_por is not None:
            clave = tuple(sorted(cubierto_por[1]))
            registro = conceptos.setdefault(
                clave, {"cubierta": True, "texto": texto}
            )
            registro["cubierta"] = True
        else:
            clave = tuple(sorted(tokens))
            conceptos.setdefault(clave, {"cubierta": False, "texto": texto})
    if not conceptos:
        return None, [], []
    cubiertas = [dato["texto"] for dato in conceptos.values() if dato["cubierta"]]
    faltantes = [dato["texto"] for dato in conceptos.values() if not dato["cubierta"]]
    pct = 100.0 * len(cubiertas) / len(conceptos)
    return pct, cubiertas, faltantes


def _nivel_educativo(texto: str) -> Optional[int]:
    """Nivel educativo de un texto (jerarquia), o None si no se reconoce."""
    if not texto:
        return None
    normalizado = _normalize_skill(str(texto))
    for clave in sorted(EDUCATION_HIERARCHY, key=len, reverse=True):
        if re.search(rf"\b{re.escape(clave)}\b", normalizado):
            return EDUCATION_HIERARCHY[clave]
    return None


def perfil_ats_desde_facts(
    facts: Sequence[Mapping[str, Any]]
) -> Dict[str, Any]:
    """Convierte los hechos del perfil (``candidate_profile_facts``) al perfil
    que espera el ranking ATS.

    Devuelve ``skills``, ``titulos``, ``temas``, ``idiomas``,
    ``experiencia_anios``, ``educacion_nivel`` (ordinal) y
    ``educacion_en_curso``.
    """
    skills: List[str] = []
    titulos: List[str] = []
    temas: List[str] = []
    idiomas: Dict[str, str] = {}
    anios_total: Optional[float] = None
    anios_suma = 0.0
    educacion_nivel: Optional[int] = None
    educacion_en_curso = False

    for fact in facts or ():
        if not isinstance(fact, Mapping):
            continue
        categoria = str(fact.get("category") or "").strip()
        codigo = str(fact.get("value_code") or "").strip()
        texto = str(fact.get("value_text") or "").strip()
        qualifier = str(fact.get("qualifier") or "").strip()

        if categoria == "skill":
            if texto:
                skills.append(texto)
            elif codigo:
                skills.append(codigo)
        elif categoria == "experience":
            numero = fact.get("numeric_value")
            if numero is not None:
                try:
                    valor = float(numero)
                except (TypeError, ValueError):
                    valor = None
                if valor is not None:
                    if codigo == "total":
                        anios_total = valor
                    else:
                        anios_suma += valor
            if codigo != "total":
                partes = re.split(r"\s[—–-]\s", texto, maxsplit=1)
                if partes and partes[0].strip():
                    titulos.append(partes[0].strip())
        elif categoria == "summary":
            if texto:
                temas.append(texto)
        elif categoria == "language":
            clave = CODIGO_IDIOMA_PERFIL.get(codigo.casefold(), codigo.casefold())
            if not clave:
                continue
            nivel = NIVEL_IDIOMA_PERFIL.get(qualifier.casefold(), qualifier.casefold())
            actual = idiomas.get(clave, "")
            if LANGUAGE_HIERARCHY.get(nivel, 0) >= LANGUAGE_HIERARCHY.get(actual, 0):
                idiomas[clave] = nivel
        elif categoria == "education":
            nivel = _nivel_educativo(f"{codigo} {texto}")
            if nivel is not None and (
                educacion_nivel is None or nivel > educacion_nivel
            ):
                educacion_nivel = nivel
            if str(fact.get("education_status") or "").strip() == "pursuing":
                educacion_en_curso = True

    anios = anios_total if anios_total is not None else (anios_suma or None)
    texto_semantico = " | ".join(
        ([temas[0]] if temas else [])
        + skills
        + titulos
    )
    return {
        "skills": skills,
        "titulos": titulos,
        "temas": temas,
        "idiomas": idiomas,
        "experiencia_anios": anios,
        "educacion_nivel": educacion_nivel,
        "educacion_en_curso": educacion_en_curso,
        "texto_semantico": texto_semantico,
    }


@dataclass
class DesgloseATS:
    """Los componentes del score de una vacante y el detalle de skills."""

    componentes: Dict[str, ComponenteATS]
    skills_cubiertas: List[str] = field(default_factory=list)
    skills_faltantes: List[str] = field(default_factory=list)


def _codigo_idioma(codigo: Any = None, texto: Any = None) -> str:
    """Codigo canonico de idioma ("es"/"en"/...) de un requisito.

    OJO: en el corpus los requisitos de idioma vienen como ``espanol`` /
    ``ingles`` (no "es"/"en") y el codigo canonico del aviso como "es"/"en".
    Sin normalizar, el perfil (que si usa es/en) no casaba con ninguno y el
    componente de idiomas salia 0 %.
    """
    for candidato in (codigo, texto):
        limpio = str(candidato or "").strip().casefold()
        if not limpio:
            continue
        canonico = CODIGO_IDIOMA_PERFIL.get(limpio)
        if canonico:
            return canonico
    return ""


def componentes_ats(
    perfil: Mapping[str, Any],
    *,
    requisitos: Sequence[Mapping[str, Any]] = (),
    semantic_score: Optional[float] = None,
    skills_vacante: Sequence[str] = (),
    notas: Optional[Mapping[str, str]] = None,
) -> DesgloseATS:
    """Calcula los 5 componentes del score de UNA vacante (sin ponderar).

    * ``requisitos``: los requisitos del aviso (con la regla de idioma ya
      aplicada). Los obligatorios pesan; "preferred" no bloquea.
    * ``semantic_score``: similitud (0-1) perfil↔aviso, o None.
    * ``skills_vacante``: skills extraidas del aviso (``jobs.skills``): el
      respaldo cuando el aviso no declara requisitos obligatorios.
    * ``notas``: texto extra del detalle de cada componente.
    """
    perfil = dict(perfil or {})
    notas = dict(notas or {})
    componentes: Dict[str, ComponenteATS] = {}

    # 1) SEMANTICA (perfil <-> aviso)
    if semantic_score is None:
        componentes["semantica"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["semantica"], None, "sin embeddings"
        )
    else:
        pct = max(0.0, min(1.0, float(semantic_score))) * 100.0
        componentes["semantica"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["semantica"], pct,
            notas.get("semantica") or f"similitud {pct:.0f} %",
        )

    # 2) SKILLS: el GAP de skills del aviso (lo que un ATS verifica).
    #    Denominador: los requisitos obligatorios del aviso (con evidencia) +
    #    las skills extraidas que son COMPETENCIAS (las frases de tarea se
    #    filtran: "elaborar cotizaciones" no es una competencia verificable).
    #    Numerador: las que el perfil cubre.
    obligatorias = [
        requisito
        for requisito in requisitos
        if str(requisito.get("category") or "") == "skill"
        and str(requisito.get("requirement_level") or "") == "required"
    ]
    skills_perfil = list(perfil.get("skills") or [])
    lista: List[str] = []
    for requisito in obligatorias:
        texto = str(
            requisito.get("value_text") or requisito.get("value_code") or ""
        ).strip()
        if texto and texto not in lista:
            lista.append(texto)
    for texto in skills_utiles(skills_vacante):
        if texto not in lista:
            lista.append(texto)
    origen = (
        f"{len(obligatorias)} requisito(s) + skills del aviso"
        if obligatorias
        else "skills del aviso"
    )
    pct, cubiertas, faltantes = cobertura_skills(lista, skills_perfil)
    if pct is None:
        componentes["skills"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["skills"], None, "el aviso no declara skills"
        )
    else:
        componentes["skills"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["skills"], pct,
            notas.get("skills")
            or f"{len(cubiertas)}/{len(cubiertas) + len(faltantes)} ({origen})",
        )

    # 3) EXPERIENCIA
    minimos = [
        float(requisito["minimum"])
        for requisito in requisitos
        if str(requisito.get("category") or "") == "experience"
        and str(requisito.get("requirement_level") or "") == "required"
        and requisito.get("minimum") is not None
        and str(requisito.get("unit") or "").casefold() in {"years", "year", "años", "ano"}
    ]
    req_anos = max(minimos) if minimos else None
    cand_anos = perfil.get("experiencia_anios")
    if req_anos is None:
        componentes["experiencia"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["experiencia"], None, "el aviso no pide años"
        )
    elif cand_anos is None:
        componentes["experiencia"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["experiencia"], None, "el perfil no registra años"
        )
    else:
        cand = float(cand_anos)
        pct = 100.0 if cand >= req_anos else 100.0 * cand / req_anos
        componentes["experiencia"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["experiencia"], pct,
            f"{cand:g} de {req_anos:g} años",
        )

    # 4) EDUCACION
    edu_requisitos = [
        requisito
        for requisito in requisitos
        if str(requisito.get("category") or "") == "education"
        and str(requisito.get("requirement_level") or "") == "required"
    ]
    niveles = [
        nivel
        for nivel in (
            _nivel_educativo(
                f"{requisito.get('value_code') or ''} {requisito.get('value_text') or ''}"
            )
            for requisito in edu_requisitos
        )
        if nivel is not None
    ]
    req_nivel = max(niveles) if niveles else None
    cand_nivel = perfil.get("educacion_nivel")
    if req_nivel is None:
        componentes["educacion"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["educacion"], None, "el aviso no pide estudios"
        )
    elif cand_nivel is None:
        componentes["educacion"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["educacion"], None, "el perfil no registra estudios"
        )
    elif bool(perfil.get("educacion_en_curso")):
        componentes["educacion"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["educacion"], 0.0, "estudios en curso"
        )
    else:
        cand = int(cand_nivel)
        pct = 100.0 if cand >= req_nivel else 100.0 * cand / max(req_nivel, 1)
        componentes["educacion"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["educacion"], pct,
            f"nivel {cand} vs {req_nivel}",
        )

    # 5) IDIOMAS
    pedidos: Dict[str, str] = {}
    for requisito in requisitos:
        if str(requisito.get("category") or "") != "language":
            continue
        if str(requisito.get("requirement_level") or "") == "preferred":
            continue
        codigo = _codigo_idioma(
            requisito.get("value_code"), requisito.get("value_text")
        )
        if not codigo:
            continue
        qualifier = str(requisito.get("qualifier") or "")
        actual = pedidos.get(codigo)
        if actual is None or LANGUAGE_HIERARCHY.get(
            qualifier.casefold(), 1
        ) > LANGUAGE_HIERARCHY.get(actual.casefold(), 1):
            pedidos[codigo] = qualifier
    perfil_idiomas = dict(perfil.get("idiomas") or {})
    if not pedidos:
        componentes["idiomas"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["idiomas"], None, "el aviso no pide idioma"
        )
    elif not perfil_idiomas:
        componentes["idiomas"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["idiomas"], None, "el perfil no registra idiomas"
        )
    else:
        partes: List[float] = []
        for codigo, qualifier in pedidos.items():
            req = LANGUAGE_HIERARCHY.get(qualifier.casefold(), 1)
            cand = LANGUAGE_HIERARCHY.get(
                str(perfil_idiomas.get(codigo, "")).casefold(), 0
            )
            partes.append(100.0 if cand >= req else 100.0 * cand / max(req, 1))
        componentes["idiomas"] = ComponenteATS(
            ETIQUETAS_COMPONENTE["idiomas"], sum(partes) / len(partes),
            f"{len(partes)} idioma(s) pedido(s)",
        )

    return DesgloseATS(componentes, cubiertas, faltantes)


def ranking_ats(
    perfil: Mapping[str, Any],
    *,
    requisitos: Sequence[Mapping[str, Any]] = (),
    semantic_score: Optional[float] = None,
    skills_vacante: Sequence[str] = (),
    weights: Optional[Mapping[str, float]] = None,
    imputacion: Optional[Mapping[str, float]] = None,
    notas: Optional[Mapping[str, str]] = None,
    desglose: Optional[DesgloseATS] = None,
) -> RankingATS:
    """Score ATS 0-100 de una vacante contra el perfil (ranking, no estado).

    * ``requisitos``: los requisitos del aviso (con la regla de idioma ya
      aplicada). Los obligatorios pesan; "preferred" no bloquea.
    * ``semantic_score``: similitud (0-1) perfil↔aviso, o None.
    * ``skills_vacante``: skills extraidas del aviso (respaldo cuando el
      aviso no declara requisitos obligatorios).
    * ``imputacion``: valor por componente para cuando el aviso NO tiene
      dato. Con imputacion el score usa los PESOS FIJOS (todos los avisos
      son comparables: un componente sin dato toma el promedio del corpus,
      ni premia ni castiga). Sin imputacion, los componentes sin dato se
      excluyen y su peso se redistribuye (score de una vacante suelta).
    """
    pesos = dict(weights or PESOS_RANKING)
    if desglose is None:
        desglose = componentes_ats(
            perfil,
            requisitos=requisitos,
            semantic_score=semantic_score,
            skills_vacante=skills_vacante,
            notas=notas,
        )
    componentes = dict(desglose.componentes)
    cubiertas = list(desglose.skills_cubiertas)
    faltantes = list(desglose.skills_faltantes)

    # -- un componente SIN DATO: se imputa el promedio del corpus ----------
    if imputacion is not None:
        for clave, componente in list(componentes.items()):
            if componente.pct is not None:
                continue
            valor = imputacion.get(clave)
            if valor is None:
                continue
            componentes[clave] = ComponenteATS(
                componente.nombre,
                float(valor),
                f"sin dato (promedio del corpus: {float(valor):.0f} %)",
            )

    # -- total: solo los componentes con dato ------------------------------
    disponibles = {
        clave: valor
        for clave, valor in componentes.items()
        if valor.pct is not None and pesos.get(clave, 0) > 0
    }
    if not disponibles:
        return RankingATS(None, VEREDICTO_SIN_DATOS, componentes, cubiertas, faltantes, {})
    total_peso = sum(pesos[clave] for clave in disponibles)
    pesos_usados = {clave: pesos[clave] / total_peso for clave in disponibles}
    total = sum(
        pesos_usados[clave] * float(componentes[clave].pct) for clave in disponibles
    )
    if total >= UMBRALES_RANKING["fuerte"]:
        veredicto = "fuerte"
    elif total >= UMBRALES_RANKING["ajustable"]:
        veredicto = "ajustable"
    else:
        veredicto = "debil"
    return RankingATS(
        total=round(total, 1),
        veredicto=veredicto,
        componentes=componentes,
        skills_cubiertas=cubiertas,
        skills_faltantes=faltantes,
        pesos_usados=pesos_usados,
    )