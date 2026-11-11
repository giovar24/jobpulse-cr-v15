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
* El ALCANCE de la negacion, del suavizador y de la obligatoriedad es el
  GRUPO de terminos unidos por enumeracion ("Bachelor's or Master's degree"),
  no la clausula completa: un "preferred" que pertenece al segundo titulo de
  una enumeracion ("Bachelor's/University degree, Master's degree preferred")
  no invalida al primero, pero si lo invalida cuando la enumeracion es
  continua ("Bachelor's or Master's degree preferred").
* Un requisito de ESTUDIANTE ACTIVO ("currently pursuing", "must be
  enrolled") es un criterio DISTINTO del titulo completado: se cumple solo si
  el perfil registra un hecho educativo ``education_status='pursuing'``; si no,
  el motivo es ``titulo_universitario_en_curso_requerido``.
* ESCALERA EDUCATIVA (regla de negocio 2026-11-08/10, ver
  ``docs/REGLAS_NEGOCIO_EDUCACION.md``): secundaria (1) < superior de ciclo
  corto (2) < estudiante avanzado (3) < titulo universitario (4) < posgrado
  (5). Un hecho ``pursuing`` NO confiere titulo: su nivel EFECTIVO es el
  escalon inferior (un bachelor en curso cuenta como estudiante avanzado).
  Un aviso con "X % de completitud" declara el escalon 3, no el 4.
  "Estudiante avanzado" = **80 % o mas de los creditos** (regla del usuario,
  referencia EE. UU.): el umbral se EXIGE, no se supone. El aviso que pide
  menos del 80 % queda por debajo del escalon 3; un hecho ``pursuing`` sin el
  80 % documentado no alcanza el escalon 3 (ver ``porcentaje_avance_fact``).
* SEMANTICA DE LA AUSENCIA DEL FACT (acordada 2026-10-29):
  - El perfil registra hechos educativos y NINGUNO dice 'pursuing' -> se sabe
    que la persona NO esta registrada como estudiante activo -> 'NO CUMPLE':
    el requisito de estudiante activo BLOQUEA con su motivo propio.
  - El perfil NO registra NINGUN hecho educativo -> la dimension educativa no
    es verificable: NUNCA se descarta por falta de informacion; la vacante va
    a ``revisar_a_mano`` con motivo ``educacion_no_verificable``.
* DECISIONES FIRMADAS (Paso 7 · tabla ``job_match_decision``): cuando el motor
  NO pudo decidir (estado ``no_confirmado``), el veredicto de una SEGUNDA
  persona cierra el caso:
    - ``bloqueo_real`` -> el requisito bloquea -> la vacante se ``descartada``;
    - ``no_bloqueo``   -> el requisito queda ``faltante`` (no bloquea, pero el
      perfil no lo tiene) -> la vacante a ``revisar_a_mano``;
    - ``dudoso``       -> sin cambio: el caso sigue ABIERTO (falta una
      decision de negocio).
  La decision esta anclada al sha256 del TEXTO que se reviso: si el aviso se
  re-raspa y su texto cambia, la decision deja de aplicar (hay que volver a
  firmarlo). **Una decision NUNCA pisa un veredicto que el motor ya dio.**

Precedencia de estados (definida en el plan del paso 5):

1. ``descartada``          bloqueante universitario CONFIRMADO en el texto.
2. ``revisar_a_mano``      requisito universitario obligatorio NO confirmado
   (o education no verificable: el perfil no registra hechos educativos).
3. ``datos_insuficientes`` cobertura < 0.60.
4. ``revisar_a_mano``      otros requisitos no cumplidos.
5. ``calificada``          puntaje >= 0.80.
6. ``baja_compatibilidad`` resto.

Ademas, antes de evaluar los requisitos, se aplica el FILTRO POR AREA: si el
perfil marco areas de empleo (``candidate_profile_facts.category='area'``) y
la oferta esta clasificada en un area que NO marco el usuario, la vacante no
se evalua: queda con estado ``fuera_de_area`` (motivo
``fuera_de_area_del_perfil``). Reglas conservadoras: sin areas marcadas no hay
filtro (se evalua todo); las ofertas sin area o en el area ``otros`` (titulo
ambiguo o sin encaje) SIEMPRE se evaluan; y la corrida sigue escribiendo una
fila por vacante, para que la exclusion quede auditable.

El modulo no lleva datos del candidato hardcodeados: todo sale de
``candidate_profile_facts``, ``concepto`` y ``job_area``.

Trazabilidad: cada corrida escribe filas NUEVAS en ``job_match`` (PK
``job_id, corrida_id``) y deja las corridas anteriores con ``valida = 0``
(migracion 015). Nunca se actualiza una corrida ya emitida.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from jobpulse_v15 import areas
from jobpulse_v15 import decisiones
from jobpulse_v15 import idiomas

UMBRAL_COBERTURA = 0.60
UMBRAL_PUNTAJE = 0.80

#: Escala de niveles de idioma (A1..C2). La fuente de verdad es
#: ``idiomas.ORDEN_NIVEL`` (agrega "nativo" y normaliza "B2+", "C1-C2",
#: "fluent"...). Antes esta tabla vivia aqui con las claves EN MAYUSCULAS y
#: los requisitos traen el nivel en minusculas ("b2"): la comparacion caia en
#: "no_verificable" y el gap de idioma se escondia en silencio.
IDIOMA_ORDEN = dict(idiomas.ORDEN_NIVEL)

# REGLA DE IDIOMA (acordada 2026-10-31): el requisito de idioma de un aviso
# es **el idioma en que esta escrito**, salvo que el aviso pida uno o varios
# idiomas como requisito (los que pide el aviso son los requisitos).
# El mapeo idioma -> codigo canonico vive en ``idiomas`` (fuente unica).
EVIDENCIA_IDIOMA_DEL_AVISO = "idioma del aviso"

ESTADO_CALIFICADA = "calificada"
ESTADO_REVISAR = "revisar_a_mano"
ESTADO_DESCARTADA = "descartada"
ESTADO_DATOS_INSUFICIENTES = "datos_insuficientes"
ESTADO_SIN_REQUISITOS = "sin_requisitos"
ESTADO_BAJA_COMPATIBILIDAD = "baja_compatibilidad"
# El perfil marco areas de empleo y esta oferta NO esta en ellas: no se
# evalua (queda registrada para que la exclusion sea auditable).
ESTADO_FUERA_DE_AREA = "fuera_de_area"

MOTIVO_BLOQUEANTE = "titulo_universitario_requerido"
MOTIVO_TITULO_EN_CURSO = "titulo_universitario_en_curso_requerido"
MOTIVO_EDUCACION_NO_CONFIRMADA = "educacion_no_confirmada"
MOTIVO_EDUCACION_NO_VERIFICABLE = "educacion_no_verificable"
MOTIVO_EDUCACION_NO_CUMPLE = "educacion_no_cumple"
MOTIVO_SKILL = "skill_faltante"
MOTIVO_IDIOMA = "idioma_no_comparable"
MOTIVO_EXPERIENCIA = "experiencia_no_verificable"
MOTIVO_LICENCIA = "licencia_no_comparable"
MOTIVO_COBERTURA = "cobertura_insuficiente"
MOTIVO_CUMPLE_UMBRAL = "cumple_umbral"
MOTIVO_PUNTAJE_BAJO = "puntaje_bajo"
MOTIVO_SIN_REQUISITOS = "sin_requisitos_mapeados"
MOTIVO_FUERA_DE_AREA = "fuera_de_area_del_perfil"

# Orden de prioridad al elegir el motivo cuando coexisten varios.
PRIORIDAD_MOTIVOS = (
    # El motivo "en curso" va primero: cuando el aviso exige ser ESTUDIANTE
    # ACTIVO, esa es la explicacion mas precisa del descarte (el extractor
    # suele duplicar la misma frase con 'education_status' distinto).
    MOTIVO_TITULO_EN_CURSO,
    MOTIVO_BLOQUEANTE,
    MOTIVO_EDUCACION_NO_CONFIRMADA,
    MOTIVO_EDUCACION_NO_VERIFICABLE,
    MOTIVO_EDUCACION_NO_CUMPLE,
    MOTIVO_SKILL,
    MOTIVO_IDIOMA,
    MOTIVO_EXPERIENCIA,
    MOTIVO_LICENCIA,
    MOTIVO_COBERTURA,
)

# Escalera educativa (de menor a mayor). El escalon "estudiante avanzado" esta
# entre el superior de ciclo corto y el titulo universitario: un hecho en curso
# NO confiere titulo (regla de negocio 2026-11-08, R2). Los numeros son los
# mismos que ``nivel_escala.orden`` y ``concepto.nivel_orden``.
NIVEL_SECUNDARIA = 1
NIVEL_SUPERIOR_CORTO = 2
NIVEL_ESTUDIANTE_AVANZADO = 3
NIVEL_UNIVERSITARIO = 4
NIVEL_POSGRADO = 5

# "Estudiante avanzado" = la mayor parte de la carrera finalizada: 80 % o mas
# de los creditos (regla del usuario, referencia del sistema educativo de
# EE. UU.: "X % of completeness of a bachelor's degree program"). Es un
# UMBRAL EXIGIDO, no supuesto: ni el aviso que pide menos lo declara ni el
# hecho del perfil que no lo documenta alcanza el escalon 3.
UMBRAL_ESTUDIANTE_AVANZADO = 80.0


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
    r"|bachiller(?:ato)?\s+universitari[oa]\b"
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
# OJO 2: "bachiller/bachillerato" SIN "universitario" es SECUNDARIA en CR, pero
# NO se filtra aqui: es el filtro por CONTEXTO de otro termino, y "Licenciatura o
# bachillerato universitario" es un titulo universitario valido (si el filtro
# lo alcanzara, mataria el "Licenciatura" de la misma clausula).
_CONTEXTO_NO_UNIVERSIDAD = re.compile(
    r"(?:two|2)[\s-]?year\s+(?:college\s+)?degree"
    r"|associate\s+degree"
    r"|community\s+college"
    r"|high\s+school"
    r"|technical\s+school"
    r"|secondary\s+school"
    r"|educaci[óo]n\s+media",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------
# NIVEL EDUCATIVO DECLARADO POR EL TEXTO (escalera GENERAL, no por pais)
# --------------------------------------------------------------------------
#
# El nivel de un requisito NO se toma del codigo canonico sino de la FRASE que
# aparece en el texto de la oferta. La escalera es general (tipo ISCED):
#
#   1 = secundaria              high school, secondary school, bachillerato
#   2 = superior de ciclo corto associate degree, two-year college degree,
#                                 technical degree, tecnico superior
#   3 = estudiante avanzado     "X% completeness of a bachelor's degree"
#                                 (avance parcial: NO confiere titulo)
#   4 = universitario           bachelor's degree, university degree,
#                                 licenciatura, bachillerato universitario
#   5 = posgrado                master's degree, MBA, postgraduate degree
#
# Un aviso del extranjero se lee con SU propio vocabulario: lo que decide el
# nivel es la frase del texto, no la equivalencia de un pais. El perfil se
# expresa en la misma escalera, de modo que la comparacion no depende de donde
# viva la persona ni de donde se publico la vacante.
_FRASES_NIVEL: tuple[tuple[re.Pattern[str], int], ...] = (
    # --- 5: posgrado ---
    (re.compile(r"\bmaster(?:['\u2019]s|s)?\s+degree\b", re.I), NIVEL_POSGRADO),
    (re.compile(r"\bmba\b", re.I), NIVEL_POSGRADO),
    (re.compile(r"\bpostgraduate\s+degree\b", re.I), NIVEL_POSGRADO),
    (re.compile(r"\bdoctorate\b|\bph\.?\s?d\.?\b", re.I), NIVEL_POSGRADO),
    # --- 4: universitario ---
    (re.compile(r"\bbachelor(?:['\u2019]s|s)?\s+degree\b", re.I), NIVEL_UNIVERSITARIO),
    (re.compile(r"\bbaccalaureate\b", re.I), NIVEL_UNIVERSITARIO),
    (re.compile(r"\buniversity\s+degree\b", re.I), NIVEL_UNIVERSITARIO),
    (re.compile(r"\bfour[\s-]?year\s+(?:college\s+)?degree\b", re.I), NIVEL_UNIVERSITARIO),
    (re.compile(r"\blicenciatura\b|\blicenciado\b", re.I), NIVEL_UNIVERSITARIO),
    (re.compile(r"\bbachiller(?:ato)?\s+universitari[oa]\b", re.I), NIVEL_UNIVERSITARIO),
    (re.compile(r"\bgrado\s+universitario\b", re.I), NIVEL_UNIVERSITARIO),
    (re.compile(r"\bt[íi]tulo\s+universitario\b", re.I), NIVEL_UNIVERSITARIO),
    (re.compile(r"\bestudios\s+universitarios\b", re.I), NIVEL_UNIVERSITARIO),
    # --- 2: superior de ciclo corto ---
    (re.compile(r"\b(?:two|2)[\s-]?year\s+(?:college\s+)?degree\b", re.I), NIVEL_SUPERIOR_CORTO),
    (re.compile(r"\bassociate(?:['\u2019]s)?\s+degree\b", re.I), NIVEL_SUPERIOR_CORTO),
    (re.compile(r"\btechnical\s+degree\b", re.I), NIVEL_SUPERIOR_CORTO),
    (re.compile(r"\bt[ée]cnico\s+superior\b", re.I), NIVEL_SUPERIOR_CORTO),
    (re.compile(r"\bpostsecondary\s+(?:certificate|diploma)\b", re.I), NIVEL_SUPERIOR_CORTO),
    (re.compile(r"\bcommunity\s+college\s+degree\b", re.I), NIVEL_SUPERIOR_CORTO),
    # --- 1: secundaria ---
    (re.compile(r"\bhigh\s+school\b", re.I), NIVEL_SECUNDARIA),
    (re.compile(r"\bsecondary\s+school\b", re.I), NIVEL_SECUNDARIA),
    (re.compile(r"\bdiploma\s+de\s+secundaria\b", re.I), NIVEL_SECUNDARIA),
    (re.compile(r"\beducaci[óo]n\s+media\b", re.I), NIVEL_SECUNDARIA),
)

# ESTUDIOS UNIVERSITARIOS PARCIALES: el aviso define su propio umbral
# ("80% completeness of a bachelor's degree program"). El porcentaje NO
# confiere titulo (ISCED 2011: "partial level completion" es una subcategoria
# de nivel, no una cualificacion): si el aviso pide >= 80 % declara el escalon
# "estudiante avanzado" (3); si pide menos, queda por debajo de ese escalon.
_PATRON_ESTUDIOS_PARCIALES = re.compile(
    r"\b(\d{1,3})\s*%?\s*(?:of\s+)?completeness\s+of\s+(?:a|an|the)\s+"
    r"bachelor(?:['\u2019]s|s)?\s+degree\s+program\b"
    r"|\b(\d{1,3})\s*%\s*(?:of\s+)?(?:a|an|the)\s+bachelor(?:['\u2019]s|s)?\s+"
    r"degree\s+program\b"
    r"|\b(\d{1,3})\s*%\s*completion\s+of\s+(?:a|an|the)\s+"
    r"bachelor(?:['\u2019]s|s)?\s+degree\b",
    re.IGNORECASE,
)

# Porcentaje de avance que puede declarar un HECHO educativo del perfil, en su
# texto libre (``qualifier``/``notes``/``value_text``) o en ``numeric_value``
# con una unidad de porcentaje. Sin este dato, un ``pursuing`` no alcanza el
# escalon "estudiante avanzado".
_PATRON_PORCENTAJE_AVANCE = re.compile(
    r"(\d{1,3}(?:[.,]\d+)?)\s*(?:%|percent\b|por\s?ciento\b|pct\b)",
    re.IGNORECASE,
)
_UNIDADES_PORCENTAJE = frozenset(
    {"%", "percent", "percentage", "porcentaje", "pct", "por ciento"}
)

# VIAS ALTERNATIVAS ACADEMICAS con el nivel que declara el texto. Una via
# solo desbloquea al perfil si el perfil tiene ESE nivel de estudios: una via
# que presupone mas estudios de los que el perfil tiene no es una via.
# ("or advanced university studies" = posgrado sin titulo: presupone un
# titulo universitario previo; "or coursework/studies toward a university
# degree" = estudiante avanzado; "or technical degree" = ciclo corto).
_VIA_ACADEMICA_NIVEL: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"\bor\s+advanced\s+university\s+studies\b", re.I), NIVEL_POSGRADO),
    (re.compile(r"\bor\s+advanced\s+(?:university\s+)?coursework\b", re.I), NIVEL_ESTUDIANTE_AVANZADO),
    (re.compile(r"\bor\s+university\s+(?:coursework|studies)\b", re.I), NIVEL_ESTUDIANTE_AVANZADO),
    (re.compile(r"\bor\s+(?:completing\s+)?coursework\s+(?:in|of|toward|towards)\b", re.I), NIVEL_ESTUDIANTE_AVANZADO),
    (re.compile(r"\bor\s+(?:an?\s+)?technical\s+degree\b", re.I), NIVEL_SUPERIOR_CORTO),
    (re.compile(r"\bor\s+(?:an?\s+)?associate(?:['\u2019]s)?\s+degree\b", re.I), NIVEL_SUPERIOR_CORTO),
)

# Negacion DURA: el requisito universitario NO es obligatorio ("not
# required", "no se requiere"). Se separa de los SUAVIZADORES ("preferred",
# "deseable") porque cuando aparecen juntos manda la negacion dura
# ("is preferred but not required" -> negacion, no preferencia).
_NEGACION_DURA = re.compile(
    r"\b(?:"
    r"not\s+required"
    r"|no\s+required"
    r"|not\s+necessary"
    r"|not\s+mandatory"
    r"|not\s+obligatory"
    r"|no\s+(?:se\s+)?requiere"
    r"|no\s+requerid[oa]s?"
    r"|no\s+requerido"
    r")",
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
    # "…; alternatively, 3+ years of relevant professional experience".
    r"|\balternatively\b"
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
# field; equivalent practical experience may be considered." y "...; alternatively,
# 3+ years of relevant professional experience").
_ALTERNATIVA_SIGUIENTE = re.compile(
    r"\bequivalent\b[^.]{0,40}\bexperience\b"
    r"|\bor\s+(?:its\s+|the\s+|an?\s+)?equivalent\b"
    r"|\bexperience\s+(?:may\s+be|can\s+be)\s+considered\b"
    r"|\balternatively\b"
    r"|\bor\s+(?:\d+|a|an|several|some|few)?\s*\+?\s*"
    r"(?:years?|años?|anos?)\s+(?:of\s+|de\s+)?(?:related\s+)?experience\b",
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

# Enlazador de una enumeracion de titulos ("Bachelor's or Master's degree",
# "Bachelor's/University degree"). Un suavizador o una negacion al final de la
# enumeracion ("... or Master's degree preferred") alcanza a TODOS sus
# miembros: por eso los terminos unidos asi se analizan como un GRUPO.
_COORDINACION = re.compile(
    r"^[\s,]*(?:or|and|&|y)\b"
    r"|^[\s,]*\/"
    r"|^[\s,]*o\b",
    re.IGNORECASE,
)

# "What you need to bring", "What you'll need (Required)", "What you will need".
_PATRON_WHAT_YOU_NEED = (
    r"what\s+you(?:['\u2019]ll)?\s*(?:will\s+)?need"
    r"(?:\s*\(\s*required\s*\))?"
    r"(?:\s+to\s+\w+)?"
    r"(?!\w)"
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
    r"|\b(?:job|role|further|key|minimum|basic)?\s*requirements\b"
    r"|" + _PATRON_WHAT_YOU_NEED +
    r"|\beducation\s*(?:&|and)\s*experience\b"
    r"|\beducation\s*:"
    r"|\bformaci[óo]n\s*:"
    r"|\bcalificaciones\b"
    r"|\bnecesitar[áa]s\s+las\s+siguientes\b"
    r"|\brequisitos\b"
    r"|\bse\s+requiere\b"
    r"|\bnecesita(?:r[áa]|ndo)?\b"
    r"|\bse\s+necesita\b"
    r"|\byou\s+will\s+need\b"
    r"|\byou\s+need\s+to\s+have\b"
    r"|\bwill\s+need\s+to\s+have\b"
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
    # "Bachelor's degree in ... discipline required" (la palabra 'required'
    # cerca del TITULO, no de la experiencia).
    r"|\b(?:degree|diploma|title|study|studies)\b[^.;]{0,40}\brequired\b"
    # Perfil de ESTUDIANTE ACTIVO: la frase describe a quien la empresa
    # quiere -> es una exigencia ("Active university student", "Students or
    # recent graduates ... pursuing diplomas or degrees").
    r"|\bactive\s+university\s+student\b"
    r"|\buniversity\s+students\s+actively\s+enrolled\b"
    r"|\bstudents\s+(?:or\s+recent\s+graduates\s+)?[^.;]{0,100}\bpursuing\b"
    r"|\bcurrently\s+pursuing\b"
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
    r"|(?:minimum|basic|required)?\s*(?:job|role|further|key)?\s*requirements?"
    r"|(?:minimum|basic|required)\s+(?:education\s+and\s+)?experience"
    r"|education\s*(?:and|&)\s*experience(?:\s+required)?"
    r"|" + _PATRON_WHAT_YOU_NEED + r"|education"
    r"|requirements?"
    r"|requisitos"
    r"|required\s+education"
    r")\s*[.:]?\s*$",
    re.IGNORECASE,
)

# Encabezado de requisitos seguido de contenido ("Job Requirements: Active
# university student ..."): el encabezado gobierna la clausula SIGUIENTE.
_ENCABEZADO_REQUISITOS_INICIO = re.compile(
    r"^\s*(?:"
    r"(?:required|minimum|basic|essential|preferred)?\s*qualifications?"
    r"|(?:job|role|further|key|minimum|basic)?\s*requirements?"
    r"|education\s*(?:and|&)\s*experience"
    r"|" + _PATRON_WHAT_YOU_NEED + r")\s*:",
    re.IGNORECASE,
)

# Encabezado de la seccion de requisitos al FINAL de la clausula anterior
# ("...under pressure ______ What you need to bring:" -> gobierna la clausula
# siguiente). Acepta texto previo (subrayados, coletilla) antes del encabezado.
_ENCABEZADO_REQUISITOS_FIN = re.compile(
    r"(?:^|[\s\W_])(?:"
    r"(?:required|minimum|basic|essential|preferred)?\s*qualifications?"
    r"|(?:minimum|basic|required)?\s*(?:job|role|further|key)?\s*requirements?"
    r"|(?:minimum|basic|required)\s+(?:education\s+and\s+)?experience"
    r"|education\s*(?:and|&)\s*experience(?:\s+required)?"
    r"|" + _PATRON_WHAT_YOU_NEED +
    r"|education"
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

# Separadores de clausula: fin de linea, ';' y las vinetas de los portales
# ('·', '•', '●', '▪').
_SEPARADOR_CLAUSULA = re.compile(r"(?:\r?\n|[;·•●▪])|(?<=[.!?])\s+")


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
    # Vias alternativas ACADEMICAS detectadas, con el nivel que declara el
    # texto: [(nivel, etiqueta)]. Sirven para decidir si la via esta
    # DISPONIBLE para el perfil (si el perfil tiene ese nivel de estudios).
    vias: list[tuple[int, str]] = field(default_factory=list)

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


def _spans_nivel(texto: str) -> list[tuple[int, int, int]]:
    """(inicio, fin, nivel) de cada frase que declara un nivel educativo."""
    spans: list[tuple[int, int, int]] = []
    for patron, nivel in _FRASES_NIVEL:
        for match in patron.finditer(texto or ""):
            spans.append((match.start(), match.end(), nivel))
    return spans


def nivel_educativo_del_texto(texto: str, termino: str | None = None) -> int | None:
    """Nivel educativo que declara el TEXTO de la oferta (escalera general).

    Si se indica ``termino`` (el ``value_text`` del requisito extraido) se
    toma el nivel de la frase que CUBRE ese termino: la frase mas larga gana
    ("two year college degree" -> 2, aunque dentro diga "college degree").
    Si ninguna frase cubre el termino, se devuelve ``None`` y el llamador usa
    el nivel del codigo canonico.

    Sin ``termino``: el nivel mas alto declarado en el texto.
    """
    texto = texto or ""
    spans = _spans_nivel(texto)
    if not spans:
        return None
    termino = (termino or "").strip()
    if not termino:
        return max(nivel for _, _, nivel in spans)
    for match in re.finditer(re.escape(termino), texto, re.IGNORECASE):
        inicio, fin = match.start(), match.end()
        cubre = [s for s in spans if s[0] <= inicio and fin <= s[1]]
        if cubre:
            return max(cubre, key=lambda s: s[1] - s[0])[2]
        solapa = [s for s in spans if s[0] < fin and s[1] > inicio]
        if solapa:
            return max(solapa, key=lambda s: s[1] - s[0])[2]
    return None


def porcentaje_estudios_parciales(texto: str) -> float | None:
    """Porcentaje que declara el aviso en la frase de avance parcial, o None."""
    coincidencia = _PATRON_ESTUDIOS_PARCIALES.search(texto or "")
    if not coincidencia:
        return None
    for grupo in coincidencia.groups():
        if grupo is not None:
            return float(grupo)
    return None


def es_estudios_parciales(texto: str) -> bool:
    """True si el texto exige ESTUDIOS UNIVERSITARIOS PARCIALES (X % de un
    programa de bachelor). Es un requisito de nivel 3 SIN titulo."""
    return _PATRON_ESTUDIOS_PARCIALES.search(texto or "") is not None


def porcentaje_avance_fact(fact: Mapping[str, Any]) -> float | None:
    """% de creditos completados que declara un HECHO educativo (o None).

    Se acepta el dato en ``numeric_value`` (con ``unit`` de porcentaje) o en
    el texto libre del hecho (``qualifier``/``notes``/``value_text``). El
    perfil puede registrar "80 % de creditos", "80% completado", etc.
    """
    valores: list[float] = []
    numero = fact.get("numeric_value")
    unidad = str(fact.get("unit") or "").strip().casefold()
    if numero is not None and unidad in _UNIDADES_PORCENTAJE:
        valores.append(float(numero))
    for campo in ("qualifier", "notes", "value_text"):
        for coincidencia in _PATRON_PORCENTAJE_AVANCE.finditer(
            str(fact.get(campo) or "")
        ):
            valores.append(float(coincidencia.group(1).replace(",", ".")))
    return max(valores) if valores else None


def _vias_academicas(ventana: str) -> list[tuple[int, str]]:
    """Vias alternativas ACADEMICAS de la ventana: (nivel, etiqueta)."""
    vias: list[tuple[int, str]] = []
    for patron, nivel in _VIA_ACADEMICA_NIVEL:
        if patron.search(ventana or "") and (nivel, patron.pattern) not in vias:
            vias.append((nivel, patron.pattern))
    return vias


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


def _grupos_terminos(
    texto: str,
    candidatos: list[tuple[re.Match, bool]],
    clausulas: list[tuple[str, int]],
) -> list[list[tuple[re.Match, bool]]]:
    """Agrupa los terminos unidos por una enumeracion ("or", "/", "y").

    "Bachelor's or Master's degree preferred" es UNA sola exigencia: el
    suavizador ("preferred") alcanza a los dos terminos. En cambio
    "Bachelor's/University degree, Master's degree preferred" son DOS
    exigencias: la coma corta el alcance del suavizador.
    """
    grupos: list[list[tuple[re.Match, bool]]] = []
    for match, explicito in candidatos:
        if grupos:
            anterior = grupos[-1][-1][0]
            gap = texto[anterior.end(): match.start()]
            misma_clausula = _indice_clausula(
                clausulas, anterior.start()
            ) == _indice_clausula(clausulas, match.start())
            if misma_clausula and _COORDINACION.match(gap):
                grupos[-1].append((match, explicito))
                continue
        grupos.append([(match, explicito)])
    return grupos


def _analisis_clausula(antes: str, ambito: str) -> tuple[bool, bool]:
    """(obligatorio, suave) del grupo de terminos.

    * ``obligatorio``: el ambito del grupo exige el titulo
      ("Required Qualifications", "Minimum Qualifications", "must have",
      "degree or above", "Requisitos", ...). El encabezado cuenta solo si
      aparece ANTES del termino: "3 years of experience required" al final de
      la misma clausula NO vuelve obligatorio un titulo que se menciona de
      paso.
    * ``suave``: el texto solo lo prefiere ("Preferred: Bachelor's degree ..."),
      es decir NO obliga. Se evalua sobre el ambito del grupo, no sobre toda
      la clausula (asi "Master's degree preferred" no vuelve suave al
      "Bachelor's" de otra coma de la misma enumeracion).
    """
    if _SUAVIZADOR.search(ambito):
        return False, True
    if _OBLIGATORIEDAD_ANTES.search(antes) or _OBLIGATORIEDAD.search(ambito):
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

    El ALCANCE de la negacion, del suavizador y de la obligatoriedad es el
    GRUPO de terminos unidos por enumeracion ("Bachelor's or Master's
    degree"), no la clausula completa: asi un "preferred" que pertenece al
    segundo titulo de una enumeracion no invalida al primero.

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

    validos: list[tuple[re.Match, bool]] = []
    for match, explicito in candidatos:
        inicio, fin = match.start(), match.end()
        entorno = texto[max(0, inicio - 60): fin + 60]
        if not _es_universitario(entorno):
            continue
        if not explicito:
            cercano = texto[max(0, inicio - 40): fin + 40]
            if _es_titulo_empleo(cercano):
                continue
        validos.append((match, explicito))

    grupos = _grupos_terminos(texto, validos, clausulas)

    confirmaciones: list[ConfirmacionEducacion] = []
    for indice_grupo, grupo in enumerate(grupos):
        primero, ultimo = grupo[0][0], grupo[-1][0]
        g_ini, g_fin = primero.start(), ultimo.end()
        indice = _indice_clausula(clausulas, g_ini)
        clausula_actual = clausulas[indice][0] if indice is not None else ""
        inicio_clausula = clausulas[indice][1] if indice is not None else 0
        fin_clausula = inicio_clausula + len(clausula_actual)

        # Limites del ambito del grupo: la clausula, mas el grupo vecino.
        limite_izq = inicio_clausula
        if indice_grupo > 0:
            limite_izq = max(limite_izq, grupos[indice_grupo - 1][-1][0].end())
        limite_der = fin_clausula
        if indice_grupo + 1 < len(grupos):
            limite_der = min(limite_der, grupos[indice_grupo + 1][0][0].start())

        antes_amplio = texto[limite_izq:g_ini]
        ambito_completo = texto[limite_izq:limite_der]
        if len(clausula_actual) > 400:
            # Clausula muy larga (avisos sin separadores): el analisis se
            # limita a una ventana alrededor del titulo para que una seccion
            # lejana ("Preferred ...") no contamine al requisito.
            ambito = texto[
                max(limite_izq, g_ini - 200): min(limite_der, g_fin + 200)
            ]
        else:
            ambito = ambito_completo
        antes_ventana = texto[
            max(limite_izq, g_ini - VENTANA_NEGACION_ANTES): g_ini
        ]
        despues_ventana = texto[
            g_fin: min(limite_der, g_fin + VENTANA_NEGACION_DESPUES)
        ]

        # --- encabezado de la clausula anterior ---------------------------
        # "Qualifications" / "Job Requirements: ..." gobiernan la clausula del
        # titulo; si el encabezado es SUAVE ("Preferred Qualifications") NO
        # obliga.
        encabezado_anterior = ""
        encabezado_texto = ""
        if indice is not None and indice > 0:
            encabezado_anterior = clausulas[indice - 1][0]
            found = _ENCABEZADO_REQUISITOS_FIN.search(encabezado_anterior)
            if found:
                encabezado_texto = found.group(0)
        es_encabezado = bool(encabezado_texto)

        # --- negacion / suavizador (ALCANCE: el grupo) --------------------
        negacion_dura = (
            _NEGACION_DURA.search(antes_ventana)
            or _NEGACION_DURA.search(despues_ventana)
            or _NEGACION_GRADO.search(antes_ventana)
            or _NEGACION_GRADO.search(despues_ventana)
            or _NEGACION_PEGADA.search(antes_ventana)
        )
        if negacion_dura:
            if negativa is None:
                negativa = ConfirmacionEducacion(
                    False, primero.group(0), _frase_de(texto, g_ini), "negacion"
                )
            continue
        suavizado = (
            _NEGACION.search(antes_ventana)
            or _NEGACION.search(despues_ventana)
            or _SUAVIZADOR.search(antes_ventana)
            or _SUAVIZADOR.search(despues_ventana)
            or (es_encabezado and _SUAVIZADOR.search(encabezado_texto))
        )
        if suavizado:
            if negativa is None:
                negativa = ConfirmacionEducacion(
                    False,
                    primero.group(0),
                    _frase_de(texto, g_ini),
                    "suave",
                    suave=True,
                )
            continue

        # --- obligatoriedad: la decide el TEXTO --------------------------
        # Se calcula ANTES de la alternativa: asi la confirmacion negativa
        # tambien sabe si el titulo era obligatorio ("Minimum Qualifications
        # Bachelor's degree or advanced university studies" ES obligatorio).
        antes_obligacion = antes_amplio[-200:] if len(antes_amplio) > 200 else antes_amplio
        obligatorio, suave = _analisis_clausula(antes_obligacion, ambito)
        if es_encabezado and not obligatorio:
            # El encabezado de la seccion de requisitos gobierna lo que
            # viene debajo.
            obligatorio = True

        # --- alternativa (conservadora: clause + grupo + siguiente) ------
        alt_antes = texto[max(limite_izq, g_ini - VENTANA_ALTERNATIVA_ANTES): g_ini]
        alt_despues = texto[g_fin: min(limite_der, g_fin + VENTANA_ALTERNATIVA_DESPUES)]
        ventana_alternativa = alt_antes + primero.group(0) + alt_despues
        clausula_siguiente = ""
        if indice is not None and indice + 1 < len(clausulas):
            clausula_siguiente = clausulas[indice + 1][0]
        if (
            _tiene_alternativa(ventana_alternativa)
            or _tiene_alternativa(clausula_actual)
            or _ALTERNATIVA_SIGUIENTE.search(clausula_siguiente)
        ):
            # Vias ACADEMICAS con nivel declarado: el evaluador decide si
            # estan DISPONIBLES para el perfil.
            vias = (
                _vias_academicas(ventana_alternativa)
                + _vias_academicas(clausula_actual)
                + _vias_academicas(clausula_siguiente)
            )
            if negativa is None:
                negativa = ConfirmacionEducacion(
                    False,
                    primero.group(0),
                    _frase_de(texto, g_ini),
                    "alternativa",
                    obligatorio=obligatorio,
                    suave=suave,
                    vias=vias,
                )
            continue

        confirmaciones.append(
            ConfirmacionEducacion(
                True,
                primero.group(0),
                _frase_de(texto, g_ini),
                "confirmado",
                obligatorio=obligatorio,
                en_curso=bool(_EN_CURSO.search(ambito_completo)),
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
    # Frase literal del aviso donde se encontro el requisito: es el ancla
    # para leer el NIVEL que declara el texto (no el codigo canonico).
    evidence: str | None = None
    # True cuando el requisito NO lo pide el aviso sino que se deduce de la
    # REGLA de idioma (el aviso esta escrito en ese idioma).
    implicito: bool = False


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

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        aplicar_filtro_areas: bool = True,
    ) -> None:
        self.connection = connection
        self._niveles: dict[tuple[str, str], int | None] = {}
        self.facts = self._cargar_facts()
        self.total_anos = self._cargar_experiencia()
        self.requisitos_por_job = self._cargar_requisitos()
        self.idioma_aviso_por_job = self._cargar_idioma_aviso()
        self.textos_por_job = self._cargar_textos()
        # DECISIONES FIRMADAS por una segunda persona (tabla
        # ``job_match_decision``): solo aplican si el texto del aviso es EXACTO
        # el que se reviso (se ancla al sha256 del texto).
        self.decisiones_por_job = self._cargar_decisiones()
        self.jobs_con_analisis = self._cargar_jobs_con_analisis()
        # Filtro por area de empleo: las areas marcadas por el usuario y el
        # area de cada oferta. Si el perfil no marca ninguna, no hay filtro.
        # ``aplicar_filtro_areas=False`` = "evaluar todo" (ignora las areas).
        self.aplicar_filtro_areas = aplicar_filtro_areas
        self.areas_perfil = areas.areas_del_perfil(connection)
        self.area_por_job = areas.areas_por_oferta(connection)

    # -- carga ------------------------------------------------------------
    def _cargar_facts(self) -> dict[str, list[dict]]:
        facts: dict[str, list[dict]] = {
            "skill": [],
            "language": [],
            "education": [],
            "license": [],
        }
        for row in self.connection.execute(
            """
            SELECT category, value_code, codigo_canonico, qualifier, education_status,
                   value_text, numeric_value, unit, notes
            FROM candidate_profile_facts
            WHERE codigo_canonico IS NOT NULL
              AND category IN ('skill', 'language', 'education', 'license')
            """
        ):
            facts[row["category"]].append(
                {
                    "value_code": row["value_code"],
                    "codigo_canonico": row["codigo_canonico"],
                    "qualifier": row["qualifier"],
                    "education_status": row["education_status"],
                    "value_text": row["value_text"],
                    "numeric_value": row["numeric_value"],
                    "unit": row["unit"],
                    "notes": row["notes"],
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
                   r.education_status, r.evidence
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
                    evidence=row["evidence"],
                )
            )
        return por_job

    def _cargar_idioma_aviso(self) -> dict[str, str]:
        """Idioma declarado (o detectado) de cada aviso."""
        return {
            row["job_id"]: row["posting_language"]
            for row in self.connection.execute(
                "SELECT job_id, posting_language FROM jobs"
            )
        }

    def _cargar_textos(self) -> dict[str, str]:
        textos: dict[str, str] = {}
        for row in self.connection.execute(
            "SELECT job_id, requirements_raw, description_raw FROM jobs"
        ):
            textos[row["job_id"]] = decisiones.texto_aviso(
                row["requirements_raw"], row["description_raw"]
            )
        return textos

    def _cargar_decisiones(self) -> dict[str, dict[str, object]]:
        """Decisiones FIRMADAS de la dimension educativa, por aviso.

        La decision se ancla al sha256 del TEXTO que se reviso: si el aviso se
        re-scrapea y su texto cambia, la firma deja de aplicar (el caso vuelve
        a ``educacion_no_confirmada`` y hay que volver a firmarlo). Asi una
        firma vieja nunca se aplica a un texto que nadie leyo.
        """
        try:
            filas = self.connection.execute(
                """
                SELECT job_id, dimension, veredicto, criterio, revisor, fecha,
                       text_hash, corrida_id
                FROM job_match_decision
                WHERE dimension = ?
                """,
                (decisiones.DIMENSION_EDUCACION,),
            ).fetchall()
        except sqlite3.OperationalError:
            # La tabla todavia no existe (base anterior a la migracion 027):
            # no hay firmas que aplicar.
            return {}
        por_job: dict[str, dict[str, object]] = {}
        for fila in filas:
            job_id = fila["job_id"]
            texto = self.textos_por_job.get(job_id, "")
            if not texto:
                continue
            if decisiones.hash_texto(texto) != fila["text_hash"]:
                continue
            por_job[job_id] = dict(fila)
        return por_job

    def decision_educacion(self, job_id: str) -> dict[str, object] | None:
        """Decision firmada vigente para el aviso (o ``None``)."""
        return self.decisiones_por_job.get(job_id)

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

    def niveles_educativos(self) -> list[int]:
        """Niveles educativos EFECTIVOS del perfil (los declarados en ``concepto``).

        Un hecho ``education_status='pursuing'`` NO confiere el titulo: su
        nivel efectivo es el escalon inferior (regla de negocio 2026-11-08,
        R2). Un bachelor en curso cuenta como "estudiante avanzado" (3), no
        como titulo universitario (4).
        """
        niveles = [
            self.nivel_efectivo_fact(fact) for fact in self.facts["education"]
        ]
        return [n for n in niveles if n is not None]

    def nivel_efectivo_fact(self, fact: dict) -> int | None:
        """Nivel EFECTIVO de un hecho educativo del perfil.

        El nivel NOMINAL sale de ``concepto.nivel_orden``. Si el hecho esta
        ``pursuing`` NO confiere titulo:

        * **Universitario en curso**: solo alcanza el escalon "estudiante
          avanzado" (3) si el hecho DOCUMENTA el 80 % o mas de los creditos
          (``porcentaje_avance_fact``). Sin ese dato no se puede afirmar el
          escalon (devuelve ``None``): "nunca dar por hecho lo que el perfil
          no dice".
        * **Posgrado en curso**: el titulo universitario (4) es el requisito
          de entrada del programa, asi que lo confiere (no depende del avance).
        * **Ciclo corto o secundaria en curso**: baja un escalon (el avance
          parcial no confiere titulo), sin bajar nunca de secundaria.
        """
        nivel = self.nivel_concepto(fact["codigo_canonico"], "education")
        if nivel is None:
            return None
        if fact.get("education_status") != "pursuing":
            return nivel
        if nivel >= NIVEL_UNIVERSITARIO:
            if nivel == NIVEL_UNIVERSITARIO:
                avance = porcentaje_avance_fact(fact)
                if avance is None or avance < UMBRAL_ESTUDIANTE_AVANZADO:
                    return None
                return NIVEL_ESTUDIANTE_AVANZADO
            return NIVEL_UNIVERSITARIO
        return max(NIVEL_SECUNDARIA, nivel - 1)

    def nivel_candidato_educacion(self) -> int | None:
        niveles = self.niveles_educativos()
        return max(niveles) if niveles else None

    def tiene_nivel_educativo(self, nivel: int) -> bool:
        """True si el perfil alcanza AL MENOS ese nivel EFECTIVO de estudios.

        Mira el nivel alcanzado, no si el titulo se termino: un hecho en curso
        alcanza el escalon "estudiante avanzado" (3), no el universitario (4).
        """
        return any(n >= nivel for n in self.niveles_educativos())

    def nivel_efectivo_requisito(self, requisito: Requisito, texto: str) -> int | None:
        """Nivel del requisito educativo segun el TEXTO de la oferta.

        El texto manda sobre el codigo canonico: "Two year college degree"
        (que el extractor mapea a ``university_degree``) declara nivel 2. Si
        el texto no declara ningun nivel, se usa el del codigo canonico.

        Un aviso que acepta AVANCE PARCIAL ("X % completeness of a bachelor's
        degree program") declara el escalon "estudiante avanzado" (3) SOLO si
        pide el 80 % o mas; si pide menos, queda por debajo de ese escalon
        (2). El avance parcial no confiere titulo (ISCED 2011).
        """
        nivel_codigo = self.nivel_concepto(requisito.codigo_canonico, "education")
        evidencia = requisito.evidence or ""
        nivel = None
        if evidencia:
            nivel = nivel_educativo_del_texto(evidencia, requisito.value_text)
        if nivel is None and texto and texto.strip() != evidencia.strip():
            nivel = nivel_educativo_del_texto(texto, requisito.value_text)
        if nivel == NIVEL_UNIVERSITARIO:
            porcentaje = porcentaje_estudios_parciales(evidencia or texto or "")
            if porcentaje is not None:
                if porcentaje >= UMBRAL_ESTUDIANTE_AVANZADO:
                    return NIVEL_ESTUDIANTE_AVANZADO
                return NIVEL_SUPERIOR_CORTO
        return nivel if nivel is not None else nivel_codigo

    def cumple_skill(self, codigo: str) -> bool:
        return any(f["codigo_canonico"] == codigo for f in self.facts["skill"])

    def cumple_language(self, codigo: str, qualifier: str | None):
        """Compara el idioma con su NIVEL (no solo con el nombre).

        El nivel se NORMALIZA antes de comparar (``idiomas.normalizar_nivel``):
        el aviso puede pedir "B2", "b2", "B2+", "C1-C2", "fluent" o
        "intermedio" y el perfil puede registrar "B2" o "Nativo". Sin
        normalizar, los niveles no comparables caian en "no_verificable" y el
        gap de idioma NO se veia (fallo silencioso de alineacion).
        """
        for fact in self.facts["language"]:
            if fact["codigo_canonico"] != codigo:
                continue
            if qualifier is None:
                return True
            nivel_fact = idiomas.orden_nivel(fact["qualifier"])
            nivel_req = idiomas.orden_nivel(qualifier)
            if nivel_fact is None or nivel_req is None:
                return "no_verificable"
            return nivel_fact >= nivel_req
        return False

    def cumple_idioma_del_aviso(self, codigo: str):
        """Cumple el requisito IMPLICITO: el idioma en que esta escrito el aviso.

        * ``True``: el perfil registra ese idioma.
        * ``"no_verificable"``: el perfil NO registra ningun idioma -> no se
          puede afirmar que no lo tenga (nunca se descarta por falta de
          informacion).
        * ``False``: el perfil registra otros idiomas, pero no este.
        """
        if not self.facts["language"]:
            return "no_verificable"
        return any(f["codigo_canonico"] == codigo for f in self.facts["language"])

    def cumple_license(self, codigo: str):
        """Cumple un requisito de licencia: 'cumple' | 'no_cumple' | 'no_verificable'.

        MISMA regla dura que los IDIOMAS (`cumple_idioma_del_aviso`):

        * el perfil NO registra ninguna licencia -> ``"no_verificable"``: no se
          puede afirmar que no la tenga. **Nunca se descarta por falta de
          informacion** (si no, todos los avisos con "licencia de conducir"
          quedarian fuera por un dato que el CV no menciona).
        * el perfil registra licencias -> cumple si alguna tiene ese codigo
          canonico; si no, ``False`` (falta de verdad).
        """
        if not self.facts["license"]:
            return "no_verificable"
        return any(f["codigo_canonico"] == codigo for f in self.facts["license"])

    def codigo_idioma_del_aviso(self, job_id: str) -> str | None:
        """Codigo canonico del idioma del aviso (``None`` si no se sabe)."""
        return idiomas.codigo_canonico_del_idioma(
            self.idioma_aviso_por_job.get(job_id) or ""
        )

    def requisitos_efectivos(self, job_id: str) -> list[Requisito]:
        """Requisitos del aviso con la REGLA DE IDIOMA aplicada.

        * Los idiomas que el aviso **pide** (nivel ``required``/``inferred``/
          ``ambiguous``) son los requisitos de idioma.
        * Un idioma solo ``preferred`` **no** es un requisito: no bloquea.
        * Si el aviso **no pide** ningun idioma, el requisito de idioma es **el
          idioma del aviso**: hay que poder trabajar en el idioma en que esta
          escrito.
        * Si el aviso no tiene NINGUN otro requisito, no se agrega el idioma
          implicito: el aviso se queda en ``sin_requisitos`` (no se puede
          calificar una oferta solo porque su idioma se cumple).
        """
        base = self.requisitos_por_job.get(job_id, [])
        idiomas_pedidos = [
            requisito
            for requisito in base
            if requisito.category == "language"
            and requisito.requirement_level != "preferred"
        ]
        otros = [requisito for requisito in base if requisito.category != "language"]
        efectivos = otros + idiomas_pedidos
        if otros and not idiomas_pedidos:
            codigo = self.codigo_idioma_del_aviso(job_id)
            if codigo:
                efectivos.append(
                    Requisito(
                        requirement_id=-1,
                        category="language",
                        value_code=codigo,
                        value_text=codigo,
                        qualifier=None,
                        requirement_level="required",
                        minimum=None,
                        codigo_canonico=codigo,
                        education_status=None,
                        evidence=EVIDENCIA_IDIOMA_DEL_AVISO,
                        implicito=True,
                    )
                )
        return efectivos

    def cumple_experience(self, minimum: float | None):
        if self.total_anos is None or minimum is None:
            return "no_verificable"
        return self.total_anos >= minimum

    # -- educacion --------------------------------------------------------
    def tiene_hechos_educativos(self) -> bool:
        """True si el perfil registra AL MENOS un hecho educativo."""
        return bool(self.facts["education"])

    def estado_educacion_en_curso(self, nivel_req: int) -> str:
        """'cumple' | 'no_cumple' | 'no_verificable' para ESTUDIANTE ACTIVO.

        Semantica acordada (2026-10-29):

        * El perfil registra hechos educativos y ALGUNO dice
          ``education_status='pursuing'``: se compara el nivel. Si alcanza el
          nivel pedido -> 'cumple'; si no -> 'no_cumple'.
        * El perfil registra hechos educativos y NINGUNO dice 'pursuing':
          se sabe que la persona NO esta registrada como estudiante activo ->
          'no_cumple' (MOTIVO_TITULO_EN_CURSO). Da igual que los hechos no
          traigan ``education_status``: lo que decide es que NO haya un
          'pursuing'.
        * El perfil NO registra ningun hecho educativo: no se puede afirmar
          que "no cumple" -> 'no_verificable' (MOTIVO_EDUCACION_NO_VERIFICABLE).

        OJO: aqui se compara el nivel NOMINAL del hecho (``nivel_concepto``),
        no el efectivo. Un requisito "currently pursuing a Bachelor's degree"
        pregunta QUE programa se cursa, no si el titulo esta terminado; por eso
        un hecho ``pursuing`` de nivel universitario SI lo cumple (aunque su
        nivel efectivo sea el de "estudiante avanzado").
        """
        hechos = self.facts["education"]
        if not hechos:
            return "no_verificable"
        pursuing = [f for f in hechos if f.get("education_status") == "pursuing"]
        if pursuing:
            niveles = [
                self.nivel_concepto(f["codigo_canonico"], "education") for f in pursuing
            ]
            niveles = [n for n in niveles if n is not None]
            if not niveles:
                return "no_verificable"
            return "cumple" if max(niveles) >= nivel_req else "no_cumple"
        # Hay hechos educativos pero ninguno dice 'pursuing' -> 'no_cumple'
        # (da igual que los hechos no traigan 'education_status').
        return "no_cumple"

    def candidato_universitario_en_curso(self, nivel_req: int) -> bool:
        """True si el perfil registra un hecho educativo 'pursuing' suficiente.

        Es lo que permite cumplir un requisito de ESTUDIANTE ACTIVO
        ("currently pursuing a Bachelor's degree"), que es un criterio
        DISTINTO del titulouniversitario completado.
        """
        return self.estado_educacion_en_curso(nivel_req) == "cumple"

    def evaluar_educacion(
        self, requisito: Requisito, texto: str, job_id: str | None = None
    ) -> tuple[str, ConfirmacionEducacion | None]:
        """Devuelve (estado_requisito, confirmacion).

        estado_requisito: 'cumple' | 'faltante' | 'bloqueante' | 'no_confirmado'
        | 'no_verificable'

        Si se pasa ``job_id`` y el aviso tiene una DECISION FIRMADA por una
        segunda persona (``job_match_decision``), la decision se aplica SOLO
        cuando el motor NO pudo decidir ('no_confirmado'):

        * 'bloqueo_real' -> 'bloqueante' (la vacante se descarta).
        * 'no_bloqueo'   -> 'faltante' (no bloquea, pero no se da por cumplido:
          la vacante sigue a revision manual).
        * 'dudoso'       -> sin cambio (falta una decision de negocio).

        La decision NUNCA pisa un veredicto del motor: solo cierra los casos
        que el motor dejo abiertos por prudencia.

        Regla (acordada 2026-10-29):

        * El TEXTO decide la obligatoriedad, no solo ``requirement_level``:
          "Required Qualifications: Bachelor's degree" bloquea aunque el
          extractor lo haya marcado ``ambiguous``/``inferred``.
        * ``bloqueante`` (descartada) solo si el texto CONFIRMA el titulo
          universitario sin negacion y sin alternativa.
        * Un requisito de ESTUDIANTE ACTIVO ("currently pursuing", "must be
          enrolled") es un criterio DISTINTO del titulo completado: se cumple
          solo si el perfil registra un hecho educativo 'pursuing'.
        * Si el perfil NO registra hechos educativos, la dimension educativa
          NO es verificable: nunca se descarta por falta de informacion.
        """
        estado, confirmacion = self._evaluar_educacion(requisito, texto)
        if estado != "no_confirmado" or not job_id:
            return estado, confirmacion
        decision = self.decisiones_por_job.get(job_id)
        if not decision:
            return estado, confirmacion
        veredicto = str(decision.get("veredicto") or "")
        if veredicto == decisiones.VEREDICTO_BLOQUEO_REAL:
            return "bloqueante", confirmacion
        if veredicto == decisiones.VEREDICTO_NO_BLOQUEO:
            return "faltante", confirmacion
        # 'dudoso' (o cualquier veredicto desconocido): el caso sigue ABIERTO.
        return estado, confirmacion

    def _evaluar_educacion(
        self, requisito: Requisito, texto: str
    ) -> tuple[str, ConfirmacionEducacion | None]:
        """Regla educativa del motor, sin aplicar decisiones firmadas."""
        nivel_req = self.nivel_efectivo_requisito(requisito, texto)
        if nivel_req is None:
            return "no_confirmado", None
        nivel_cand = self.nivel_candidato_educacion()
        if nivel_cand is None:
            # Sin hechos educativos (o sin nivel) NO se puede afirmar que el
            # perfil no cumple: es 'no verificable', no 'no cumple'.
            return "no_verificable", None
        if nivel_cand >= nivel_req:
            return "cumple", None
        # ESTUDIOS UNIVERSITARIOS PARCIALES ("80 % de completitud de un
        # bachelor"): el aviso acepta un avance parcial, asi que lo cumplen
        # los estudios universitarios en curso (escalon "estudiante
        # avanzado").
        if (
            es_estudios_parciales(requisito.evidence or texto or "")
            and self.tiene_nivel_educativo(NIVEL_ESTUDIANTE_AVANZADO)
        ):
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
        # --- VIA ALTERNATIVA ACADEMICA: esta DISPONIBLE para el perfil? ---
        # Una via solo desbloquea si el perfil tiene el nivel que la via
        # declara: "or advanced university studies" (posgrado) no es una via
        # para quien no tiene estudios universitarios.
        if confirmacion.vias and not confirmacion.suave:
            disponibles = [
                via for via in confirmacion.vias if self.tiene_nivel_educativo(via[0])
            ]
            if disponibles and obligatorio:
                # El perfil PUEDE tomar la via: el requisito no bloquea.
                return "cumple", confirmacion
            if not disponibles and obligatorio:
                # Hay vias, pero ninguna al alcance del perfil: la via no
                # rescata y el titulo principal sigue exigiendose.
                return "bloqueante", confirmacion
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
            estado_curso = self.estado_educacion_en_curso(nivel_req)
            if estado_curso == "cumple":
                return "cumple", confirmacion
            if estado_curso == "no_verificable":
                return "no_verificable", confirmacion
        return "bloqueante", confirmacion

    # -- evaluacion de una vacante ---------------------------------------
    def evaluar_job(self, job_id: str) -> Resultado:
        # Filtro por AREA de empleo: el usuario marco en su perfil las areas
        # que le interesan. Una oferta clasificada en otra area NO se evalua
        # (queda registrada con estado propio: la exclusion es auditable).
        if self.aplicar_filtro_areas and areas.es_fuera_de_area(
            self.area_por_job.get(job_id), self.areas_perfil
        ):
            return Resultado(
                job_id=job_id,
                estado=ESTADO_FUERA_DE_AREA,
                puntaje=None,
                cobertura=0.0,
                motivo=MOTIVO_FUERA_DE_AREA,
                cubiertos=[],
                faltantes=[],
                total_req=0,
                evaluables=0,
                cubiertos_count=0,
                faltantes_count=0,
                no_v_count=0,
                nc_count=0,
            )
        requisitos = self.requisitos_efectivos(job_id)
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
        no_verificable_educacion = False
        matched = faltante = no_v = nc = 0

        for req in requisitos:
            categoria = req.category
            if categoria == "skill":
                ok = self.cumple_skill(req.codigo_canonico)
            elif categoria == "language":
                if req.implicito:
                    # REGLA DE IDIOMA: el aviso esta escrito en ese idioma.
                    ok = self.cumple_idioma_del_aviso(req.codigo_canonico)
                else:
                    ok = self.cumple_language(req.codigo_canonico, req.qualifier)
            elif categoria == "education":
                estado_req, conf = self.evaluar_educacion(req, texto, job_id)
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
                elif estado_req == "no_verificable":
                    # El perfil no registra hechos educativos: no se puede
                    # afirmar que no cumple -> va a revision manual.
                    ok = "no_verificable"
                    no_verificable_educacion = True
                    motivos.append(MOTIVO_EDUCACION_NO_VERIFICABLE)
                else:
                    ok = False
                    motivos.append(MOTIVO_EDUCACION_NO_CUMPLE)
            elif categoria == "experience":
                ok = self.cumple_experience(req.minimum)
            elif categoria == "license":
                # Licencia: si el perfil no registra ninguna, NO se puede
                # afirmar que no la tenga -> 'no_verificable' (misma regla
                # dura que los idiomas: nunca se descarta por falta de dato).
                ok = self.cumple_license(req.codigo_canonico)
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
        elif no_confirmado_educacion or no_verificable_educacion:
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


def _nuevo_corrida_id(connection: sqlite3.Connection) -> str:
    """Identificador de una corrida NUEVA: timestamp (+ sufijo si ya existe).

    La regla del Paso 5 es "nunca se actualiza una corrida emitida": dos
    corridas en el MISMO segundo tienen que ser dos corridas distintas, y
    `guardar_resultados` BORRA las filas de la corrida que recibe. Con el
    timestamp solo, dos corridas seguidas (la UI hace fácil pulsar dos veces)
    se pisarian. Si el timestamp ya existe, se le anade un sufijo.
    """
    base = datetime.now().strftime("%Y%m%d_%H%M%S")
    existe = connection.execute(
        "SELECT 1 FROM job_match WHERE corrida_id = ? LIMIT 1", (base,)
    ).fetchone()
    if not existe:
        return base
    for sufijo in range(1, 1000):
        candidata = f"{base}_{sufijo:02d}"
        if not connection.execute(
            "SELECT 1 FROM job_match WHERE corrida_id = ? LIMIT 1", (candidata,)
        ).fetchone():
            return candidata
    return f"{base}_{datetime.now().microsecond}"


def ejecutar_paso5(
    connection: sqlite3.Connection,
    corrida_id: str | None = None,
    invalidar_previas: bool = True,
    aplicar_filtro_areas: bool = True,
) -> tuple[str, list[Resultado]]:
    """Corre el paso 5 completo y persiste una corrida nueva.

    ``aplicar_filtro_areas=False`` = "evaluar todo": ignora las areas que el
    usuario marco en el perfil y evalua todas las vacantes.
    """
    evaluador = EvaluadorPaso5(
        connection, aplicar_filtro_areas=aplicar_filtro_areas
    )
    resultados = [evaluador.evaluar_job(job_id) for job_id in evaluador.jobs_con_analisis]
    corrida = corrida_id or _nuevo_corrida_id(connection)
    guardar_resultados(connection, resultados, corrida, invalidar_previas)
    return corrida, resultados
