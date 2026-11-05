# -*- coding: utf-8 -*-
"""REGISTRO de postulaciones del usuario: bitacora, NO aptitud.

REGLA DE DISENO (acordada 2026-11-04): **ser rechazado NO significa que el
perfil no califique para el puesto**. El reclutador humano rechaza por
presupuesto, timing, competencia, sesgos o azar: es el veredicto de una
persona sobre un contexto, NO una medida de aptitud tecnica.

Ademas, los criterios por los que un equipo de RH aprueba o rechaza varian
**de empresa a empresa y de persona a persona** (decision del usuario,
2026-11-04): por eso el resultado de la postulacion **no es comparable ni
verificable** y NO se puede usar para calibrar, validar ni reentrenar nada
del motor de ajuste. Es **inviable** como senal de aptitud.

Por eso este modulo NO calcula ni entrena el score de ajuste (eso vive en
`viabilidad.py` y se deriva de los REQUISITOS DEL AVISO contra los HECHOS DEL
PERFIL). Aqui solo se modela el **REGISTRO** del proceso de postulacion:

* leer notificaciones (correo) y "Mis postulaciones" (Workday),
* clasificar cada aviso como `applied` / `recruiter_contact` / `interview` /
  `offer` / `rejected` / `withdrawn`,
* casar cada aviso con el corpus (`job_id`) por su referencia en la URL.

Usos legitimos de estos datos (TODOS de bookkeeping):
1. **REGISTRO**: saber a que vacantes se postulo (incluidas las rechazadas)
   y conservar el historial del proceso.
2. no reprocesar lo ya postulado;
3. conteo del propio funnel (cuantas postulaciones, cuantas rechazadas
   explicitamente, cuantas siguen sin respuesta).

LO QUE NO SE HACE (regla dura):
- NO se calibran pesos ni bandas contra el resultado de la postulacion.
- NO se reentrenan pesos con los rechazos.
- NO se usa el rechazo como etiqueta de "no apto".
- **El silencio de RH NO es un rechazo**: muchos sistemas de RRHH nunca
  responden. La ausencia de aviso deja el estado en `applied` (postulada, sin
  cierre registrado) y NO se infiere `rejected` por ausencia de senal. El
  rechazo solo se registra cuando el portal o el correo lo dicen
  explicitamente.

Este modulo es PURO (sin red): recibe remitente/asunto/cuerpo y devuelve
senales. La lectura de IMAP vive en `correo_postulaciones.py` y la del
portal de Workday en `workday_postulaciones.py`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

# --------------------------------------------------------------- estados ---
# Alineados con `applications.application_status` (migracion 001).
ESTADO_APPLIED = "applied"
ESTADO_RECRUITER = "recruiter_contact"
ESTADO_INTERVIEW = "interview"
ESTADO_OFFER = "offer"
ESTADO_REJECTED = "rejected"
ESTADO_WITHDRAWN = "withdrawn"

ESTADOS_POSTULACION: tuple[str, ...] = (
    ESTADO_APPLIED,
    ESTADO_RECRUITER,
    ESTADO_INTERVIEW,
    ESTADO_OFFER,
    ESTADO_REJECTED,
    ESTADO_WITHDRAWN,
)

#: Estados que significan "el proceso avanzo" (senal positiva).
ESTADOS_AVANCE: tuple[str, ...] = (ESTADO_RECRUITER, ESTADO_INTERVIEW, ESTADO_OFFER)
#: Estados que terminan el proceso sin avance.
ESTADOS_CIERRE: tuple[str, ...] = (ESTADO_REJECTED, ESTADO_WITHDRAWN)

#: Etiquetas legibles del REGISTRO (no son evaluacion del puesto).
#:
#: `applied` NO es "pendiente de juicio": muchos sistemas de RRHH nunca
#: responden, y ese silencio **no** es un rechazo. El registro lo dice asi:
#: "postulada, sin respuesta o en proceso".
ETIQUETA_ESTADO: dict[str, str] = {
    ESTADO_APPLIED: "Postulada (sin respuesta o en proceso)",
    ESTADO_RECRUITER: "Contacto del reclutador",
    ESTADO_INTERVIEW: "Entrevista",
    ESTADO_OFFER: "Oferta",
    ESTADO_REJECTED: "Rechazada",
    ESTADO_WITHDRAWN: "Retirada",
}

# --------------------------------------------------------------- portales ---
PORTAL_WORKDAY = "workday"
PORTAL_GREENHOUSE = "greenhouse"
PORTAL_LINKEDIN = "linkedin"
PORTAL_OTRO = "otro"

#: Dominios que identifican al portal que envio la notificacion.
DOMINIOS_PORTAL: tuple[tuple[str, str], ...] = (
    ("myworkdayjobs.com", PORTAL_WORKDAY),
    ("workday.com", PORTAL_WORKDAY),
    ("greenhouse.io", PORTAL_GREENHOUSE),
    ("linkedin.com", PORTAL_LINKEDIN),
)

# ------------------------------------------------- patrones de clasificacion -
# El orden importa: primero lo mas especifico (una entrevista NO es un
# rechazo). Cada patron: (portal, regex, estado, prioridad).
_PATRONES: tuple[tuple[str | None, str, str, int], ...] = (
    # -- avance (prioridad alta) --
    (None, r"\binterview\b|\bentrevista\b|\bscreening call\b|"
          r"\bphone (?:call|screen)\b|\btechnical (?:screen|assessment)\b|"
          r"\bschedule (?:an? )?(?:interview|call)\b|"
          r"\bnext steps\b|\bnext round\b|"
          r"\bhiring (?:manager|team) (?:wants|would like) to (?:speak|meet)\b",
     ESTADO_INTERVIEW, 90),
    (None, r"\bjob offer\b|\boffer letter\b|\boffer of employment\b|"
          r"\bwe(?:'re| are) (?:pleased|happy) to offer\b|"
          r"\bwe(?:'d| would) like to (?:hire|welcome)\b|"
          r"\bemployment contract\b|\bonboarding (?:instructions|details)\b",
     ESTADO_OFFER, 95),
    (None, r"\brecruiter\b|\btalent acquisition\b|\bwill be in touch\b|"
          r"\bget back to you\b|\bmore information about your application\b",
     ESTADO_RECRUITER, 60),
    # -- cierre --
    (None, r"\bnot (?:be )?(?:been )?(?:selected|chosen|advance|advancing)\b|"
          r"\bnot (?:been )?moving forward\b|\bnot to move forward\b|"
          r"\bdecided not to\b|\bno longer (?:be )?(?:under consideration|considering|proceeding)\b|"
          r"\bnot been selected\b|\bunsuccessful\b|\bunfortunately\b|"
          r"\bwe (?:have )?(?:decided|will not|won'?t) (?:to )?(?:proceed|continue|advance)\b|"
          r"\bother (?:candidates|applicants)\b|\bposition (?:has been|was) filled\b|"
          r"\bapplication (?:was )?(?:closed|declined)\b",
     ESTADO_REJECTED, 80),
    (None, r"\bwithdrew?n\b|\bwithdrawn\b|\bI(?:'ve| have) withdrawn\b",
     ESTADO_WITHDRAWN, 70),
    # -- aplicacion (prioridad baja: "thank you for applying" no es rechazo) --
    (None, r"\bapplication (?:was )?(?:received|submitted|successful)\b|"
          r"\bwe(?:'ve| have) received your application\b|"
          r"\bthank you for (?:applying|your (?:interest|application))\b|"
          r"\bwe(?:'ve| have) received your interest\b|"
          r"\byour application (?:has been|was) (?:received|submitted)\b",
     ESTADO_APPLIED, 40),
)

_RE_TITULO_TRIM = re.compile(r"\s+")
_RE_URL = re.compile(r"https?://[^\s<>\"')\]]+")
#: Los correos PARTEN las URLs largas en varias lineas: se pega el salto
#: cuando el caracter antes y el despues son "de URL" (no se junta prosa).
_RE_URL_PARTIDA = re.compile(r"(?<=[\w/?&=._~:%-])\s*\n\s*(?=[\w/?&=._~:%-])")
#: Workday: .../job/<pais>/<Titulo>_<REQID>  (el REQID es el identificador)
_RE_WORKDAY_REQID = re.compile(r"/job/[^?#]*/([^/?#]+)$")
#: Greenhouse: /jobs/<id numerico>
_RE_GREENHOUSE_ID = re.compile(r"greenhouse\.io/[^/]+/jobs/(\d+)")
#: LinkedIn: /jobs/view/<id>
_RE_LINKEDIN_ID = re.compile(r"linkedin\.com/jobs/view/[^/?#]*?-?(\d{6,})")


@dataclass(frozen=True)
class Senal:
    """Una notificacion de postulacion, ya clasificada y sin texto crudo.

    Es lo UNICO que se guarda del correo: nunca el cuerpo del mensaje.
    """

    estado: str
    portal: str = PORTAL_OTRO
    url: str = ""
    source_job_id: str = ""
    titulo: str = ""
    empresa: str = ""
    remitente: str = ""
    asunto: str = ""
    fecha: str = ""
    detalles: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_POSTULACION:
            raise ValueError(f"Estado de postulacion no valido: {self.estado!r}")

    @property
    def es_avance(self) -> bool:
        return self.estado in ESTADOS_AVANCE

    @property
    def es_cierre(self) -> bool:
        return self.estado in ESTADOS_CIERRE


# ------------------------------------------------------------- extraccion ---
def portal_del_remitente(remitente: str) -> str:
    """Portal que envio la notificacion (workday/greenhouse/linkedin/otro)."""
    correo = (remitente or "").strip().lower()
    for dominio, portal in DOMINIOS_PORTAL:
        if dominio in correo:
            return portal
    return PORTAL_OTRO


def normalizar_texto(texto: str) -> str:
    return _RE_TITULO_TRIM.sub(" ", (texto or "").replace("­", "")).strip()


def primera_url(texto: str) -> str:
    """Primera URL del texto (los portales ponen el link al aviso).

    Las URLs partidas en varias lineas (los correos las parten) se pegan
    antes de buscar: el aviso se identifica por el REQID del final.
    """
    unido = _RE_URL_PARTIDA.sub("", texto or "")
    encontradas = _RE_URL.findall(unido)
    return encontradas[0] if encontradas else ""


def referencia_de_url(url: str) -> tuple[str, str]:
    """(portal, source_job_id) de la URL de un aviso.

    * Workday: el REQID del final de la ruta (`.../job/<pais>/<Titulo>_JR123`).
    * Greenhouse: el id numerico (`.../jobs/12345`).
    * LinkedIn: el id numerico (`.../jobs/view/...-123456`).

    El `source_job_id` conserva las MAYUSCULAS originales: el REQID de
    Workday es case-sensitive (`R38059` != `r38059`) y es la clave con la
    que el corpus identifica el aviso.
    """
    if not url:
        return PORTAL_OTRO, ""
    limpia = url.split("?")[0].split("#")[0]
    baja = limpia.lower()
    if "myworkdayjobs.com" in baja or "workday.com" in baja:
        m = _RE_WORKDAY_REQID.search(limpia)
        return PORTAL_WORKDAY, (m.group(1) if m else "")
    m = _RE_GREENHOUSE_ID.search(baja)
    if m:
        return PORTAL_GREENHOUSE, m.group(1)
    m = _RE_LINKEDIN_ID.search(baja)
    if m:
        return PORTAL_LINKEDIN, m.group(1)
    return PORTAL_OTRO, ""


def titulo_del_asunto(asunto: str) -> str:
    """Titulo del aviso en el asunto, si el portal lo pone entre parentesis."""
    texto = normalizar_texto(asunto)
    m = re.search(r"[:\-–]\s*(.+)$", texto)
    return m.group(1).strip() if m else texto


# ----------------------------------------------------------- clasificacion --
def clasificar(
    remitente: str,
    asunto: str,
    cuerpo: str = "",
    *,
    fecha: str = "",
) -> Senal | None:
    """Clasifica una notificacion en un estado de postulacion.

    Devuelve `None` si el mensaje NO es una notificacion de postulacion
    (publicidad, newsletters, etc.): es mas honesto que inventar un estado.
    """
    portal = portal_del_remitente(remitente)
    texto = normalizar_texto(f"{asunto or ''}. {cuerpo or ''}").lower()

    estado = ""
    prioridad = -1
    for _patron, regex, candidato, peso in _PATRONES:
        if not re.search(regex, texto, flags=re.IGNORECASE):
            continue
        if peso > prioridad:
            estado = candidato
            prioridad = peso

    if not estado:
        return None

    url = primera_url(cuerpo) or primera_url(asunto)
    portal_url, source_job_id = referencia_de_url(url)
    if portal_url != PORTAL_OTRO:
        portal = portal_url

    return Senal(
        estado=estado,
        portal=portal,
        url=url,
        source_job_id=source_job_id,
        titulo=titulo_del_asunto(asunto),
        remitente=(remitente or "").strip(),
        asunto=normalizar_texto(asunto),
        fecha=fecha,
    )


def clasificar_mensajes(
    mensajes: Iterable[Mapping[str, Any]],
) -> list[Senal]:
    """Clasifica un lote de mensajes (dicts con remitente/asunto/cuerpo/fecha)."""
    senales: list[Senal] = []
    for mensaje in mensajes:
        senal = clasificar(
            str(mensaje.get("remitente") or mensaje.get("from") or ""),
            str(mensaje.get("asunto") or mensaje.get("subject") or ""),
            str(mensaje.get("cuerpo") or mensaje.get("body") or ""),
            fecha=str(mensaje.get("fecha") or mensaje.get("date") or ""),
        )
        if senal is not None:
            senales.append(senal)
    return senales


def estado_mas_avanzado(estados: Sequence[str]) -> str:
    """Estado final de un puesto a partir de su historial de eventos.

    El avance gana siempre: un `interview` posterior NO se degrada a
    `rejected` (pasa a `withdrawn` solo si el usuario la retiro).

    Si no hay ningun cierre registrado, el estado queda en `applied`: es la
    postulacion **sin respuesta del portal** (o en proceso). El silencio de
    RH **no** se convierte en `rejected`.
    """
    if not estados:
        return ""
    if ESTADO_OFFER in estados:
        return ESTADO_OFFER
    if ESTADO_INTERVIEW in estados:
        return ESTADO_INTERVIEW
    if ESTADO_RECRUITER in estados:
        return ESTADO_RECRUITER
    if ESTADO_REJECTED in estados:
        return ESTADO_REJECTED
    if ESTADO_WITHDRAWN in estados:
        return ESTADO_WITHDRAWN
    return ESTADO_APPLIED


def etiqueta_estado(estado: str) -> str:
    """Etiqueta legible del estado (para el registro, no para evaluar)."""
    return ETIQUETA_ESTADO.get(estado, estado or "")


def sin_respuesta(estado: str) -> bool:
    """True si la postulacion quedo sin respuesta explicita del portal.

    O sea: se postulo y el sistema de RRHH **no dijo nada** (o sigue en
    proceso). Esto **NO** es un rechazo: muchos portales de empleo nunca
    contestan.
    """
    return estado == ESTADO_APPLIED


def formatear_fecha(fecha: datetime) -> str:
    """Fecha ISO (segundos) para guardar en la BD."""
    return fecha.strftime("%Y-%m-%d %H:%M:%S")
