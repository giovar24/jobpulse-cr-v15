# -*- coding: utf-8 -*-
"""Paso 5: emparejar requisitos de la vacante contra los hechos del perfil.

Reglas del bloqueante de educacion (acordadas con el usuario):

* Solo bloquea un requisito de TITULO UNIVERSITARIO (o superior) que el perfil
  NO alcanza.
* La confirmacion se busca en el TEXTO COMPLETO de la oferta
  (``requirements_raw`` + ``description_raw``), no solo en ``evidence``.
* Si hay negacion cercana ("not required", "No university degree required",
  "no requerido", "deseable", "preferred") o alternativa ("or its equivalent",
  "or equivalent experience", "Associate's or bachelor's degree", "Bachelor's
  degree or certification", "or other technical/scientific experience") la
  exigencia NO se confirma: la vacante va a ``revisar_a_mano`` con motivo
  ``educacion_no_confirmada``.
* "bachiller" NO es titulo universitario en Costa Rica (es secundaria);
  "licenciatura" si lo es.
* "bachelor" solo cuenta como requisito si la palabra "degree" aparece cerca:
  si no, es el TITULO del puesto ("Intern - Bachelor's Tech").
* La OBLIGATORIEDAD la decide el TEXTO, no solo ``requirement_level``: si la
  clausula exige el titulo ("Required Qualifications", "Minimum
  Qualifications", "must have", "degree or above", "Requisitos") bloquea
  aunque el extractor lo haya marcado ``ambiguous``/``inferred``. Si el texto
  solo lo prefiere ("Preferred: ...") NO bloquea.
* "or equivalent field of study / discipline / degree" NO es una via
  alternativa: sigue exigiendo un titulo universitario (misma nivel, otra
  carrera).
* Un requisito de ESTUDIANTE ACTIVO ("currently pursuing", "must be
  enrolled") es un criterio DISTINTO del titulo completado: se cumple solo si
  el perfil registra un hecho educativo ``education_status='pursuing'``; si no,
  el motivo es ``titulo_universitario_en_curso_requerido``.

Precedencia de estados (definida en el plan del paso 5):

1. ``descartada``          bloqueante universitario CONFIRMADO en el texto.
2. ``revisar_a_mano``      requisito universitario obligatorio NO confirmado.
3. ``datos_insuficientes`` cobertura < 0.60.
4. ``revisar_a_mano``      otros requisitos no cumplidos.
5. ``calificada``          puntaje >= 0.80.
6. ``baja_compatibilidad`` resto.

El modulo no lleva datos del candidato hardcodeados: todo sale de
``candidate_profile_facts`` y ``concepto``.

Trazabilidad: cada corrida escribe filas NUEVAS en ``job_match`` (PK
``job_id, corrida_id``) y deja las corridas anteriores con ``valida = 0``
(migracion 015). Nunca se actualiza una corrida ya emitida.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

UMBRAL_COBERTURA = 0.60
UMBRAL_PUNTAJE = 0.80

IDIOMA_ORDEN = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

ESTADO_CALIFICADA = "calificada"
ESTADO_REVISAR = "revisar_a_mano"
ESTADO_DESCARTADA = "descartada"
ESTADO_DATOS_INSUFICIENTES = "datos_insuficientes"
ESTADO_SIN_REQUISITOS = "sin_requisitos"
ESTADO_BAJA_COMPATIBILIDAD = "baja_compatibilidad"

MOTIVO_BLOQUEANTE = "titulo_universitario_requerido"
MOTIVO_TITULO_EN_CURSO = "titulo_universitario_en_curso_requerido"
MOTIVO_EDUCACION_NO_CONFIRMADA = "educacion_no_confirmada"
MOTIVO_EDUCACION_NO_CUMPLE = "educacion_no_cumple"
MOTIVO_SKILL = "skill_faltante"
MOTIVO_IDIOMA = "idioma_no_comparable"
MOTIVO_EXPERIENCIA = "experiencia_no_verificable"
MOTIVO_LICENCIA = "licencia_no_comparable"
MOTIVO_COBERTURA = "cobertura_insuficiente"
MOTIVO_CUMPLE_UMBRAL = "cumple_umbral"
MOTIVO_PUNTAJE_BAJO = "puntaje_bajo"
MOTIVO_SIN_REQUISITOS = "sin_requisitos_mapeados"

# Orden de prioridad al elegir el motivo cuando coexisten varios.
PRIORIDAD_MOTIVOS = (
    # El motivo "en curso" va primero: cuando el aviso exige ser ESTUDIANTE
    # ACTIVO, esa es la explicacion mas precisa del descarte (el extractor
    # suele duplicar la misma frase con 'education_status' distinto).
    MOTIVO_TITULO_EN_CURSO,
    MOTIVO_BLOQUEANTE,
    MOTIVO_EDUCACION_NO_CONFIRMADA,
    MOTIVO_EDUCACION_NO_CUMPLE,
    MOTIVO_SKILL,
    MOTIVO_IDIOMA,
    MOTIVO_EXPERIENCIA,
    MOTIVO_LICENCIA,
    MOTIVO_COBERTURA,
)

NIVEL_UNIVERSITARIO = 3


# --------------------------------------------------------------------------
# Deteccion textual del requisito educativo
# --------------------------------------------------------------------------

# Distancia maxima (caracteres) entre el termino y una negacion/alternativa
# para que esta se considere pertains al mismo requisito.
VENTANA_NEGACION_ANTES = 30
VENTANA_NEGACION_DESPUES = 45
VENTANA_ALTERNATIVA_ANTES = 40
VENTANA_ALTERNATIVA_DESPUES = 110

# Terminos que SI son un titulo universitario, sin ambiguedad.
_TERMINO_UNIVERSIDAD_EXPLICITO = re.compile(
    r"\b(?:"
    r"university\s+degree\b"
    r"|college\s+degree\b"
    r"|four[\s-]?year\s+(?:college\s+)?degree\b"
    r"|undergraduate\s+degree\b"
    r"|bachelor\s+of\s+(?:science|arts|engineering|business)\b"
    r"|licenciatura\b"
    r"|licenciado\b"
    r"|t[íi]tulo\s+universitario\b"
    r"|grado\s+universitario\b"
    r"|estudios\s+universitarios\b"
    r"|master(?:['\u2019]s|s)?\s+degree\b"
    r"|maestr[íi]a\b"
    r"|mba\b"
    r"|doctorate\b"
    r"|ph\.?\s?d\.?"
    r")",
    re.IGNORECASE,
)

# "Bachelor" a secas: se acepta solo si la palabra "degree" esta cerca, para
# no confundir el TITULO del puesto ("Intern - Bachelor's Tech") con un
# requisito.
_TERMINO_BACHELOR = re.compile(r"\bbachelor(?:['\u2019]s|s)?\b", re.IGNORECASE)
_PALABRA_DEGREE = re.compile(r"\bdegrees?\b", re.IGNORECASE)

# Contextos que NO son titulo universitario.
# OJO: "four year college degree" SI es universitario (solo se excluyen los
# grados de dos anos / associate, que en CR equivalen a tecnico).
_CONTEXTO_NO_UNIVERSIDAD = re.compile(
    r"(?:two|2)[\s-]?year\s+(?:college\s+)?degree"
    r"|associate\s+degree"
    r"|community\s+college"
    r"|high\s+school"
    r"|bachiller(?:ato)?"
    r"|technical\s+school"
    r"|secondary\s+school"
    r"|educaci[óo]n\s+media",
    re.IGNORECASE,
)

# Negaciones: el requisito universitario NO es obligatorio.
_NEGACION = re.compile(
    r"\b(?:"
    r"not\s+required"
    r"|no\s+required"
    r"|not\s+necessary"
    r"|not\s+mandatory"
    r"|not\s+obligatory"
    r"|no\s+(?:se\s+)?requiere"
    r"|no\s+requerid[oa]s?"
    r"|no\s+requerido"
    r"|deseable"
    r"|desead[oa]s?"
    r"|preferible"
    r"|preferid[oa]s?"
    r"|preferred"
    r"|opcional"
    r"|optional"
    r"|nice\s+to\s+have"
    r"|is\s+a\s+plus"
    r")",
    re.IGNORECASE,
)

# "No university degree required" / "No bachelor degree required".
_NEGACION_GRADO = re.compile(
    r"\bno\s+(?:[a-z]+\s+){0,3}degree\s+required\b"
    r"|\bno\s+(?:university|college|bachelor|master|licenciatura)\b"
    r"|\bdegree\s+is\s+not\s+required\b"
    r"|\bnot\s+required\s+to\s+have\b",
    re.IGNORECASE,
)

# Negacion pegada al termino: "No university degree required", "Not a degree".
_NEGACION_PEGADA = re.compile(r"\b(?:no|not|sin|without)\s*$", re.IGNORECASE)

# Alternativas: el puesto NO exige el titulo porque ofrece otra via.
_ALTERNATIVA = re.compile(
    r"\b(?:"
    r"or\s+(?:its\s+|the\s+|an?\s+)?equivalent\b"
    r"|or\s+additional\s+experience\b"
    r"|or\s+other\s+[\w/-]*\s*experience\b"
    r"|equivalent\s+(?:practical\s+|relevant\s+|professional\s+)?experience\b"
    r"|or\s+(?:an?\s+)?certification\b"
    r"|or\s+(?:an?\s+)?technical\s+degree\b"
    r"|or\s+advanced\s+(?:university\s+)?(?:coursework|studies)\b"
    r"|or\s+university\s+(?:coursework|studies)\b"
    r"|or\s+(?:completing\s+)?coursework\s+(?:in|of|toward|towards)\b"
    r"|associate(?:['\u2019]s)?\s+or\s+bachelor"
    r"|o\s+experiencia\s+equivalente\b"
    r"|o\s+equivalente\b"
    r")",
    re.IGNORECASE,
)

# "or 3 years of experience", "or seven years of experience".
_ALTERNATIVA_ANIOS = re.compile(
    r"\bor\s+(?:\d+|a|an|several|some|few)?\s*\+?\s*"
    r"(?:years?|años?|anos?)\s+(?:of\s+|de\s+)?(?:related\s+)?experience\b",
    re.IGNORECASE,
)

# Alternativa que aparece en la clausula SIGUIENTE (caso real: "... related
# field; equivalent practical experience may be considered.").
_ALTERNATIVA_SIGUIENTE = re.compile(
    r"\bequivalent\b[^.]{0,40}\bexperience\b"
    r"|\bor\s+(?:its\s+|the\s+|an?\s+)?equivalent\b"
    r"|\bexperience\s+(?:may\s+be|can\s+be)\s+considered\b",
    re.IGNORECASE,
)

# "or equivalent field of study / discipline / degree" NO es una via
# alternativa: sigue exigiendo un TITULO UNIVERSITARIO (misma nivel, otra
# carrera). Caso real: "Bachelor's degree in engineering, Science, or
# equivalent field of study."
_EXCEPTO_EQUIVALENTE = re.compile(
    r"\s+(?:field|discipline|area|course)\s+of\s+study\b"
    r"|\s+fields?\b"
    r"|\s+disciplines?\b"
    r"|\s+degree\b",
    re.IGNORECASE,
)

# Marcadores de OBLIGATORIEDAD dentro de la clausula del titulo.
# Se separan en "antes" (encabezado de la seccion de requisitos) y "dentro"
# (el propio requisito se declara exigido) para no confundir un encabezado
# con una mencion de otra clausula.
_OBLIGATORIEDAD_ANTES = re.compile(
    r"\brequired\s+qualifications\b"
    r"|\bminimum\s+qualifications\b"
    r"|\bbasic\s+qualifications\b"
    r"|\bqualifications?\s+required\b"
    r"|\beducation\s+required\b"
    r"|\brequired\s*:"
    r"|\brequired\b"
    r"|\bqualifications\b"
    r"|\brequisitos\b"
    r"|\bse\s+requiere\b"
    r"|\bobligatorio\b"
    r"|\brequerido\b",
    re.IGNORECASE,
)

_OBLIGATORIEDAD = re.compile(
    r"\bmust\s+have\b"
    r"|\bmust\s+be\b"
    r"|\bmust\s+possess\b"
    r"|\b(?:is|are)\s+required\b"
    r"|\bdegree\s+or\s+above\b"
    r"|\bse\s+requiere\b"
    r"|\bobligatorio\b"
    r"|\brequerido\b",
    re.IGNORECASE,
)

# Suavizadores: la clausula NO obliga ("Preferred: Bachelor's degree ...").
_SUAVIZADOR = re.compile(
    r"\bpreferred\b"
    r"|\bdesirable\b"
    r"|\bnice\s+to\s+have\b"
    r"|\bis\s+a\s+plus\b"
    r"|\boptional\b"
    r"|\bdeseable\b"
    r"|\bpreferible\b",
    re.IGNORECASE,
)

# Encabezado de la SECCION de requisitos, cuando va en su propia linea/vineta:
# "Qualifications\nBachelor's degree ...". Lo que sigue a ese encabezado
# obliga (y "Preferred Qualifications" NO obliga).
_ENCABEZADO_REQUISITOS = re.compile(
    r"^\s*(?:"
    r"(?:required|minimum|basic|essential|preferred)?\s*qualifications?"
    r"|(?:minimum|basic|required)\s+(?:education\s+and\s+)?experience"
    r"|education\s*(?:and|&)\s*experience(?:\s+required)?"
    r"|what\s+you\s+(?:will\s+)?need(?:\s*\(\s*required\s*\))?"
    r"|requirements?"
    r"|requisitos"
    r"|required\s+education"
    r")\s*[.:]?\s*$",
    re.IGNORECASE,
)

# Requisito de ESTUDIANTE ACTIVO (no de titulo completado): "Currently
# pursuing a Bachelor's degree", "Must be enrolled ...".
_EN_CURSO = re.compile(
    r"\bcurrently\s+pursuing\b"
    r"|\bpursuing\s+(?:a|an|the|your)\b"
    r"|\bcurrently\s+enrolled\b"
    r"|\benrolled\s+(?:in|at|as|full[\s-]?time)\b"
    r"|\bmust\s+be\s+enrolled\b"
    r"|\bstudents?\s+(?:of\s+college|or\s+recent\s+graduates)\b"
    r"|\bactive\s+student\b"
    r"|\bundergraduate\s+student\b"
    r"|\banticipated\s+graduation\b",
    re.IGNORECASE,
)

# Separadores de clausula: fin de linea, ';' y las vinetas de los portales.
_SEPARADOR_CLAUSULA = re.compile(r"(?:\r?\n|[;·•])|(?<=[.!?])\s+")


@dataclass
class ConfirmacionEducacion:
    """Resultado de buscar un titulo universitario en el texto de la oferta.

    ``obligatorio``: el TEXTO exige el titulo (encabezado de requisitos,
    "must have", "degree or above", ...), no solo lo sugiere.
    ``suave``: el texto solo lo prefiere ("Preferred: ..."); no obliga.
    ``en_curso``: el requisito es de ESTUDIANTE ACTIVO ("currently pursuing",
    "must be enrolled"), que es un criterio DISTINTO del titulo completado.
    """

    confirmada: bool
    termino: str | None = None
    segmento: str | None = None
    motivo: str = "sin_termino"
    obligatorio: bool = False
    en_curso: bool = False
    suave: bool = False

    @property
    def es_negacion(self) -> bool:
        return self.motivo == "negacion"

    @property
    def es_alternativa(self) -> bool:
        return self.motivo == "alternativa"


def segmentar(texto: str) -> list[str]:
    """Parte el texto de la oferta en frases/vinetas utilizables."""
    partes: list[str] = []
    for linea in (texto or "").splitlines():
        limpia = _VINETA_LINEA.sub("", linea).strip()
        if not limpia:
            continue
        for bloque in _VINETA_INLINE.split(limpia):
            for trozo in _CORTE_SENTENCIA.split(bloque):
                trozo = trozo.strip()
                if trozo:
                    partes.append(trozo)
    return partes


_CORTE_SENTENCIA = re.compile(r"(?<=[.!?])\s+")
_VINETA_LINEA = re.compile(r"^\s*[-*\u2022\u00b7]+\s*")
_VINETA_INLINE = re.compile(r"\s+[\u00b7\u2022]\s+")


def _clausulas(texto: str) -> list[tuple[str, int]]:
    """Divide el texto en clausulas y devuelve (texto, offset_inicial).

    La clausula es la unidad semantica: una vineta, un punto y coma o una
    frase. Sirve para decidir si una negacion o una alternativa pertenece al
    mismo requisito que el termino universitario.
    """
    partes: list[tuple[str, int]] = []
    pos = 0
    for match in _SEPARADOR_CLAUSULA.finditer(texto):
        fragmento = texto[pos: match.start()]
        if fragmento.strip():
            partes.append((fragmento, pos))
        pos = match.end()
    fragmento = texto[pos:]
    if fragmento.strip():
        partes.append((fragmento, pos))
    return partes


def _indice_clausula(clausulas: list[tuple[str, int]], posicion: int) -> int | None:
    """Indice de la clausula que contiene la posicion indicada."""
    for indice, (texto, inicio) in enumerate(clausulas):
        if inicio <= posicion < inicio + len(texto):
            return indice
    return None


def _es_universitario(ventana: str) -> bool:
    """Filtra terminos que en realidad son secundaria ('Bachelor in high school')."""
    return _CONTEXTO_NO_UNIVERSIDAD.search(ventana) is None


def _es_titulo_empleo(ventana: str) -> bool:
    """True si 'Bachelor' es parte del TITULO del puesto, no del requisito.

    Ejemplo real: 'Intern - Bachelor's Tech This role has been designed as...'
    """
    return _PALABRA_DEGREE.search(ventana) is None


def _frase_de(texto: str, posicion: int) -> str:
    """Devuelve la vineta/frase que contiene la posicion indicada.

    Recorta por vineta ('·', '•', salto de linea, ';') y luego por frase,
    de modo que la evidencia citada sea la oracion completa del aviso.
    """
    inicio = 0
    for separador in ("\n", "·", "•", ";"):
        pos = texto.rfind(separador, 0, posicion)
        if pos >= 0:
            inicio = max(inicio, pos + 1)
    fin = len(texto)
    for separador in ("\n", "·", "•", ";"):
        pos = texto.find(separador, posicion)
        if pos >= 0:
            fin = min(fin, pos)

    trozo = texto[inicio:fin]
    relativo = posicion - inicio
    corte = 0
    for match in re.finditer(r"(?<=[.!?])\s+", trozo):
        if match.end() <= relativo:
            corte = match.end()
    fin_frase = len(trozo)
    for match in re.finditer(r"(?<=[.!?])\s+", trozo):
        if match.start() >= relativo:
            fin_frase = match.start()
            break
    frase = trozo[corte:fin_frase].strip()
    if len(frase) > 400:
        centro = relativo - corte
        ini = max(0, centro - 200)
        fin_ventana = min(len(frase), centro + 200)
        frase = "...%s..." % frase[ini:fin_ventana]
    return " ".join(frase.split())


def _tiene_alternativa(ventana: str) -> bool:
    """True si la ventana ofrece una VIA alternativa al titulo.

    Excepcion: "or equivalent field of study / discipline / degree" no es una
    via alternativa (sigue exigiendo un titulo universitario, solo cambia la
    carrera). Si no, "Bachelor's degree in engineering, Science, or equivalent
    field of study" se perderia como bloqueo real.
    """
    if _ALTERNATIVA_ANIOS.search(ventana):
        return True
    for match in _ALTERNATIVA.finditer(ventana):
        if _EXCEPTO_EQUIVALENTE.match(ventana, match.end()):
            continue
        return True
    return False


def _analisis_clausula(clausula: str, posicion: int) -> tuple[bool, bool]:
    """(obligatorio, suave) de la clausula que contiene el titulo.

    * ``obligatorio``: la clausula marca el requisito como exigido
      ("Required Qualifications", "Minimum Qualifications", "must have",
      "degree or above", "Requisitos", ...). El encabezado cuenta solo si
      aparece ANTES del termino: "3 years of experience required" al final de
      la misma clausula NO vuelve obligatorio un titulo que se menciona de
      paso.
    * ``suave``: la clausula lo presenta como preferencia ("Preferred:
      Bachelor's degree ..."), es decir NO obliga.
    """
    if _SUAVIZADOR.search(clausula):
        return False, True
    antes = clausula[:posicion] if posicion > 0 else ""
    if _OBLIGATORIEDAD_ANTES.search(antes) or _OBLIGATORIEDAD.search(clausula):
        return True, False
    return False, False


def confirmar_requisito_universitario(texto: str) -> ConfirmacionEducacion:
    """Busca en el texto completo una exigencia de titulo universitario firme.

    Positivo si el titulo aparece sin negacion ni alternativa en su vicinity.
    Negativo si el termino aparece negado ("not required", "No university degree
    required") o como alternativa ("or equivalent experience", "Associate's or
    bachelor's degree", "Bachelor's degree or certification").

    Ventanas (acordadas): negacion 30 chars antes / 45 despues; alternativa
    40 antes / 110 despues. Ademas se revisa la clausula siguiente, donde los
    portales poner "equivalent practical experience may be considered".

    Ademas clasifica la clausula del titulo:
    * ``obligatorio``: el texto exige el titulo (no solo lo sugiere);
    * ``suave``: el texto solo lo prefiere ("Preferred: ...");
    * ``en_curso``: el requisito es de ESTUDIANTE ACTIVO ("currently
      pursuing", "must be enrolled"), no de titulo completado.
    """
    texto = texto or ""
    negativa: ConfirmacionEducacion | None = None
    clausulas = _clausulas(texto)

    candidatos: list[tuple[re.Match, bool]] = []
    for match in _TERMINO_UNIVERSIDAD_EXPLICITO.finditer(texto):
        candidatos.append((match, True))
    for match in _TERMINO_BACHELOR.finditer(texto):
        candidatos.append((match, False))
    candidatos.sort(key=lambda par: par[0].start())

    confirmaciones: list[ConfirmacionEducacion] = []
    for match, explicito in candidatos:
        inicio, fin = match.start(), match.end()
        entorno = texto[max(0, inicio - 60): fin + 60]
        if not _es_universitario(entorno):
            continue
        if not explicito:
            cercano = texto[max(0, inicio - 40): fin + 40]
            if _es_titulo_empleo(cercano):
                continue

        antes = texto[max(0, inicio - VENTANA_NEGACION_ANTES): inicio]
        despues = texto[fin: fin + VENTANA_NEGACION_DESPUES]
        if (
            _NEGACION.search(antes)
            or _NEGACION.search(despues)
            or _NEGACION_GRADO.search(antes)
            or _NEGACION_GRADO.search(despues)
            or _NEGACION_PEGADA.search(antes)
        ):
            if negativa is None:
                negativa = ConfirmacionEducacion(
                    False, match.group(0), _frase_de(texto, inicio), "negacion"
                )
            continue

        alt_antes = texto[max(0, inicio - VENTANA_ALTERNATIVA_ANTES): inicio]
        alt_despues = texto[fin: fin + VENTANA_ALTERNATIVA_DESPUES]
        ventana_alternativa = alt_antes + match.group(0) + alt_despues
        indice = _indice_clausula(clausulas, inicio)
        clausula_actual = clausulas[indice][0] if indice is not None else ""
        clausula_siguiente = ""
        if indice is not None and indice + 1 < len(clausulas):
            clausula_siguiente = clausulas[indice + 1][0]
        if (
            _tiene_alternativa(ventana_alternativa)
            or _tiene_alternativa(clausula_actual)
            or _ALTERNATIVA_SIGUIENTE.search(clausula_siguiente)
        ):
            if negativa is None:
                negativa = ConfirmacionEducacion(
                    False, match.group(0), _frase_de(texto, inicio), "alternativa"
                )
            continue

        # Zona de analisis: la clausula del titulo y, si la anterior es un
        # ENCABEZADO de la seccion de requisitos, tambien esa (el encabezado
        # obliga a lo que viene debajo).
        if len(clausula_actual) > 400:
            inicio_ventana = max(0, inicio - 120)
            zona = texto[inicio_ventana: fin + 120]
            posicion_zona = inicio - inicio_ventana
        else:
            zona = clausula_actual
            posicion_zona = inicio - (clausulas[indice][1] if indice is not None else 0)
            clausula_anterior = ""
            if indice is not None and indice > 0:
                clausula_anterior = clausulas[indice - 1][0]
            if _ENCABEZADO_REQUISITOS.match(clausula_anterior):
                zona = clausula_anterior + " " + zona
                posicion_zona += len(clausula_anterior) + 1
        obligatorio, suave = _analisis_clausula(zona, posicion_zona)
        confirmaciones.append(
            ConfirmacionEducacion(
                True,
                match.group(0),
                _frase_de(texto, inicio),
                "confirmado",
                obligatorio=obligatorio,
                en_curso=bool(_EN_CURSO.search(zona)),
                suave=suave,
            )
        )

    if confirmaciones:
        # Preferir la confirmacion en clausula OBLIGATORIA y no "preferred".
        confirmaciones.sort(key=lambda c: (c.obligatorio, not c.suave), reverse=True)
        return confirmaciones[0]
    return negativa or ConfirmacionEducacion(False)


# --------------------------------------------------------------------------
# Evaluacion
# --------------------------------------------------------------------------


@dataclass
class Requisito:
    requirement_id: int
    category: str
    value_code: str
    value_text: str
    qualifier: str | None
    requirement_level: str | None
    minimum: float | None
    codigo_canonico: str
    education_status: str | None = None


@dataclass
class Resultado:
    job_id: str
    estado: str
    puntaje: float | None
    cobertura: float
    motivo: str
    cubiertos: list[str]
    faltantes: list[str]
    total_req: int
    evaluables: int
    cubiertos_count: int
    faltantes_count: int
    no_v_count: int
    nc_count: int


class EvaluadorPaso5:
    """Evalua vacantes contra los hechos del perfil (sin datos hardcodeados)."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._niveles: dict[tuple[str, str], int | None] = {}
        self.facts = self._cargar_facts()
        self.total_anos = self._cargar_experiencia()
        self.requisitos_por_job = self._cargar_requisitos()
        self.textos_por_job = self._cargar_textos()
        self.jobs_con_analisis = self._cargar_jobs_con_analisis()

    # -- carga ------------------------------------------------------------
    def _cargar_facts(self) -> dict[str, list[dict]]:
        facts: dict[str, list[dict]] = {"skill": [], "language": [], "education": []}
        for row in self.connection.execute(
            """
            SELECT category, value_code, codigo_canonico, qualifier, education_status
            FROM candidate_profile_facts
            WHERE codigo_canonico IS NOT NULL
              AND category IN ('skill', 'language', 'education')
            """
        ):
            facts[row["category"]].append(
                {
                    "value_code": row["value_code"],
                    "codigo_canonico": row["codigo_canonico"],
                    "qualifier": row["qualifier"],
                    "education_status": row["education_status"],
                }
            )
        return facts

    def _cargar_experiencia(self) -> float | None:
        row = self.connection.execute(
            """
            SELECT numeric_value FROM candidate_profile_facts
            WHERE category = 'experience' AND value_code = 'total'
              AND numeric_value IS NOT NULL
            """
        ).fetchone()
        return row["numeric_value"] if row else None

    def _cargar_requisitos(self) -> dict[str, list[Requisito]]:
        por_job: dict[str, list[Requisito]] = {}
        rows = self.connection.execute(
            """
            SELECT j.job_id, r.requirement_id, r.category, r.value_code, r.value_text,
                   r.qualifier, r.requirement_level, r.minimum, r.codigo_canonico,
                   r.education_status
            FROM job_requirements r
            JOIN job_analysis a ON a.analysis_id = r.analysis_id
            JOIN jobs j ON j.job_id = a.job_id
            WHERE a.is_current = 1
              AND r.category IN ('skill', 'language', 'education', 'experience', 'license')
              AND r.codigo_canonico IS NOT NULL
            """
        ).fetchall()
        for row in rows:
            por_job.setdefault(row["job_id"], []).append(
                Requisito(
                    requirement_id=row["requirement_id"],
                    category=row["category"],
                    value_code=row["value_code"],
                    value_text=row["value_text"] or row["value_code"],
                    qualifier=row["qualifier"],
                    requirement_level=row["requirement_level"],
                    minimum=row["minimum"],
                    codigo_canonico=row["codigo_canonico"],
                    education_status=row["education_status"],
                )
            )
        return por_job

    def _cargar_textos(self) -> dict[str, str]:
        textos: dict[str, str] = {}
        for row in self.connection.execute(
            "SELECT job_id, requirements_raw, description_raw FROM jobs"
        ):
            partes = [row["requirements_raw"] or "", row["description_raw"] or ""]
            textos[row["job_id"]] = "\n".join(p for p in partes if p)
        return textos

    def _cargar_jobs_con_analisis(self) -> list[str]:
        return [
            row["job_id"]
            for row in self.connection.execute(
                """
                SELECT DISTINCT j.job_id FROM jobs j
                JOIN job_analysis a ON a.job_id = j.job_id
                WHERE a.is_current = 1
                ORDER BY j.job_id
                """
            )
        ]

    # -- comparaciones ----------------------------------------------------
    def nivel_concepto(self, codigo_canonico: str, categoria: str) -> int | None:
        clave = (categoria, codigo_canonico)
        if clave not in self._niveles:
            row = self.connection.execute(
                """
                SELECT MAX(nivel_orden) AS nivel FROM concepto
                WHERE codigo_canonico = ? AND categoria = ?
                """,
                (codigo_canonico, categoria),
            ).fetchone()
            self._niveles[clave] = row["nivel"] if row else None
        return self._niveles[clave]

    def nivel_candidato_educacion(self) -> int | None:
        niveles = [
            self.nivel_concepto(fact["codigo_canonico"], "education")
            for fact in self.facts["education"]
        ]
        niveles = [n for n in niveles if n is not None]
        return max(niveles) if niveles else None

    def cumple_skill(self, codigo: str) -> bool:
        return any(f["codigo_canonico"] == codigo for f in self.facts["skill"])

    def cumple_language(self, codigo: str, qualifier: str | None):
        for fact in self.facts["language"]:
            if fact["codigo_canonico"] != codigo:
                continue
            if qualifier is None:
                return True
            nivel_fact = IDIOMA_ORDEN.get(fact["qualifier"])
            nivel_req = IDIOMA_ORDEN.get(qualifier)
            if nivel_fact is None or nivel_req is None:
                return "no_verificable"
            return nivel_fact >= nivel_req
        return False

    def cumple_experience(self, minimum: float | None):
        if self.total_anos is None or minimum is None:
            return "no_verificable"
        return self.total_anos >= minimum

    # -- educacion --------------------------------------------------------
    def candidato_universitario_en_curso(self, nivel_req: int) -> bool:
        """True si el perfil registra un hecho educativo 'pursuing' suficiente.

        Es lo que permite cumplir un requisito de ESTUDIANTE ACTIVO
        ("currently pursuing a Bachelor's degree"), que es un criterio
        DISTINTO del titulouniversitario completado.
        """
        for fact in self.facts["education"]:
            if fact.get("education_status") != "pursuing":
                continue
            nivel = self.nivel_concepto(fact["codigo_canonico"], "education")
            if nivel is not None and nivel >= nivel_req:
                return True
        return False

    def evaluar_educacion(
        self, requisito: Requisito, texto: str
    ) -> tuple[str, ConfirmacionEducacion | None]:
        """Devuelve (estado_requisito, confirmacion).

        estado_requisito: 'cumple' | 'faltante' | 'bloqueante' | 'no_confirmado'

        Regla (acordada 2026-10-29):

        * El TEXTO decide la obligatoriedad, no solo ``requirement_level``:
          "Required Qualifications: Bachelor's degree" bloquea aunque el
          extractor lo haya marcado ``ambiguous``/``inferred``.
        * ``bloqueante`` (descartada) solo si el texto CONFIRMA el titulo
          universitario sin negacion y sin alternativa.
        * Un requisito de ESTUDIANTE ACTIVO ("currently pursuing", "must be
          enrolled") es un criterio DISTINTO del titulo completado: se cumple
          solo si el perfil registra un hecho educativo 'pursuing'.
        """
        nivel_req = self.nivel_concepto(requisito.codigo_canonico, "education")
        if nivel_req is None:
            return "no_confirmado", None
        nivel_cand = self.nivel_candidato_educacion()
        if nivel_cand is not None and nivel_cand >= nivel_req:
            return "cumple", None
        if nivel_req < NIVEL_UNIVERSITARIO:
            # El perfil no alcanza un nivel no universitario (p. ej. tecnico).
            return "faltante", None
        confirmacion = confirmar_requisito_universitario(texto)
        # El extractor puede marcar 'required' sin que el texto lo exija, o
        # marcarlo 'ambiguous'/'inferred' cuando el texto SI lo exige.
        obligatorio = (
            requisito.requirement_level == "required" or confirmacion.obligatorio
        )
        if not obligatorio:
            # No es obligatorio: no bloquea, pero tampoco se da por cumplido.
            return "faltante", confirmacion
        if not confirmacion.confirmada or confirmacion.suave:
            # Obligatorio pero el texto NO lo confirma (o lo deja como
            # preferencia): nunca se descarta por heuristica.
            return "no_confirmado", confirmacion
        # Confirmado y obligatorio. Si el requisito es de ESTUDIANTE ACTIVO,
        # el perfil debe registrar un hecho educativo 'pursuing'.
        en_curso = confirmacion.en_curso or requisito.education_status == "pursuing"
        if en_curso:
            confirmacion.en_curso = True
            if self.candidato_universitario_en_curso(nivel_req):
                return "cumple", confirmacion
        return "bloqueante", confirmacion

    # -- evaluacion de una vacante ---------------------------------------
    def evaluar_job(self, job_id: str) -> Resultado:
        requisitos = self.requisitos_por_job.get(job_id, [])
        if not requisitos:
            return Resultado(
                job_id=job_id,
                estado=ESTADO_SIN_REQUISITOS,
                puntaje=None,
                cobertura=0.0,
                motivo=MOTIVO_SIN_REQUISITOS,
                cubiertos=[],
                faltantes=[],
                total_req=0,
                evaluables=0,
                cubiertos_count=0,
                faltantes_count=0,
                no_v_count=0,
                nc_count=0,
            )

        texto = self.textos_por_job.get(job_id, "")
        cubiertos: list[str] = []
        faltantes: list[str] = []
        motivos: list[str] = []
        bloqueante = False
        no_confirmado_educacion = False
        matched = faltante = no_v = nc = 0

        for req in requisitos:
            categoria = req.category
            if categoria == "skill":
                ok = self.cumple_skill(req.codigo_canonico)
            elif categoria == "language":
                ok = self.cumple_language(req.codigo_canonico, req.qualifier)
            elif categoria == "education":
                estado_req, conf = self.evaluar_educacion(req, texto)
                if estado_req == "cumple":
                    ok = True
                elif estado_req == "bloqueante":
                    ok = False
                    bloqueante = True
                    if conf is not None and conf.en_curso:
                        # Requisito de ESTUDIANTE ACTIVO: criterio distinto del
                        # titulo universality completado.
                        motivos.append(MOTIVO_TITULO_EN_CURSO)
                    else:
                        motivos.append(MOTIVO_BLOQUEANTE)
                elif estado_req == "no_confirmado":
                    ok = "no_confirmado"
                    no_confirmado_educacion = True
                else:
                    ok = False
                    motivos.append(MOTIVO_EDUCACION_NO_CUMPLE)
            elif categoria == "experience":
                ok = self.cumple_experience(req.minimum)
            elif categoria == "license":
                ok = False
            else:
                ok = False

            if ok is True:
                matched += 1
                cubiertos.append(req.value_code)
            elif ok == "no_verificable":
                no_v += 1
            elif ok == "no_confirmado":
                nc += 1
                faltantes.append(req.value_code)
                motivos.append(MOTIVO_EDUCACION_NO_CONFIRMADA)
            else:
                faltante += 1
                faltantes.append(req.value_code)
                motivos.append(
                    {
                        "skill": MOTIVO_SKILL,
                        "language": MOTIVO_IDIOMA,
                        "education": MOTIVO_EDUCACION_NO_CUMPLE,
                        "experience": MOTIVO_EXPERIENCIA,
                        "license": MOTIVO_LICENCIA,
                    }.get(categoria, "requisito_no_cumplido")
                )

        total = matched + faltante + no_v + nc
        evaluables = total - no_v
        cobertura = evaluables / total if total else 0.0
        puntaje = matched / evaluables if evaluables else 0.0

        if bloqueante:
            estado = ESTADO_DESCARTADA
        elif no_confirmado_educacion:
            estado = ESTADO_REVISAR
        elif cobertura < UMBRAL_COBERTURA:
            estado = ESTADO_DATOS_INSUFICIENTES
            motivos.append(MOTIVO_COBERTURA)
        elif faltante > 0 or nc > 0:
            estado = ESTADO_REVISAR
        elif puntaje >= UMBRAL_PUNTAJE:
            estado = ESTADO_CALIFICADA
            motivos.append(MOTIVO_CUMPLE_UMBRAL)
        else:
            estado = ESTADO_BAJA_COMPATIBILIDAD
            motivos.append(MOTIVO_PUNTAJE_BAJO)

        motivo = _elegir_motivo(motivos, estado)

        return Resultado(
            job_id=job_id,
            estado=estado,
            puntaje=round(puntaje, 2),
            cobertura=round(cobertura, 2),
            motivo=motivo,
            cubiertos=cubiertos,
            faltantes=faltantes,
            total_req=total,
            evaluables=evaluables,
            cubiertos_count=matched,
            faltantes_count=faltante,
            no_v_count=no_v,
            nc_count=nc,
        )


def _elegir_motivo(motivos: Sequence[str], estado: str) -> str:
    for motivo in PRIORIDAD_MOTIVOS:
        if motivo in motivos:
            return motivo
    if estado == ESTADO_CALIFICADA:
        return MOTIVO_CUMPLE_UMBRAL
    if estado == ESTADO_BAJA_COMPATIBILIDAD:
        return MOTIVO_PUNTAJE_BAJO
    if estado == ESTADO_SIN_REQUISITOS:
        return MOTIVO_SIN_REQUISITOS
    return MOTIVO_COBERTURA


# --------------------------------------------------------------------------
# Persistencia
# --------------------------------------------------------------------------


def invalidar_corridas_previas(connection: sqlite3.Connection, corrida_id: str) -> int:
    """Marca como invalidas todas las corridas anteriores a la indicada."""
    cur = connection.execute(
        "UPDATE job_match SET valida = 0 WHERE corrida_id <> ? AND valida <> 0",
        (corrida_id,),
    )
    return cur.rowcount


def guardar_resultados(
    connection: sqlite3.Connection,
    resultados: Iterable[Resultado],
    corrida_id: str,
    invalidar_previas: bool = True,
) -> int:
    """Persiste una corrida nueva en ``job_match`` (nunca UPDATE de otra corrida)."""
    filas = [
        (
            r.job_id,
            r.estado,
            r.puntaje,
            json.dumps(r.cubiertos, ensure_ascii=False),
            json.dumps(r.faltantes, ensure_ascii=False),
            r.motivo,
            r.cobertura,
            corrida_id,
            datetime.now().isoformat(timespec="seconds"),
            r.cubiertos_count,
            r.faltantes_count,
            r.no_v_count,
            r.nc_count,
            r.total_req,
            r.evaluables,
            1,
        )
        for r in resultados
    ]
    connection.execute("DELETE FROM job_match WHERE corrida_id = ?", (corrida_id,))
    connection.executemany(
        """
        INSERT INTO job_match (
            job_id, estado, puntaje, cubiertos, faltantes, motivo, cobertura,
            corrida_id, evaluado_at, cubiertos_count, faltantes_count, no_v_count,
            nc_count, total_req, evaluables, valida
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        filas,
    )
    if invalidar_previas:
        invalidar_corridas_previas(connection, corrida_id)
    connection.commit()
    return len(filas)


def ejecutar_paso5(
    connection: sqlite3.Connection,
    corrida_id: str | None = None,
    invalidar_previas: bool = True,
) -> tuple[str, list[Resultado]]:
    """Corre el paso 5 completo y persiste una corrida nueva."""
    evaluador = EvaluadorPaso5(connection)
    resultados = [evaluador.evaluar_job(job_id) for job_id in evaluador.jobs_con_analisis]
    corrida = corrida_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    guardar_resultados(connection, resultados, corrida, invalidar_previas)
    return corrida, resultados
