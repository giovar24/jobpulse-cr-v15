# -*- coding: utf-8 -*-
"""Lectura de notificaciones de postulacion por CORREO (IMAP).

REGLA DE DISENO (acordada 2026-11-04): lo que se lee del correo es el
**estado del PROCESO** (postulaste, te contactaron, hubo entrevista, te
rechazaron), NO una medida de aptitud. **Ser rechazado NO significa que el
perfil no califique** para el puesto: el reclutador humano decide por
presupuesto, timing, competencia, sesgos y azar. Por eso estas señales:

1. evitan reprocesar lo ya postulado;
2. permiten medir el funnel propio (con el aviso de ruido humano);
3. señalan posibles falsos positivos del ranking -> revision manual.

NUNCA se usan para reentrenar el score de ajuste tecnico (`viabilidad.py`).

PRIVACIDAD: del mensaje solo se conservan DERIVADOS MINIMOS (estado, fecha,
remitente, asunto y la referencia del aviso). **El cuerpo del correo nunca
se guarda**: solo se usa en memoria para clasificar y se descarta.

CREDENCIALES: la app-password de Gmail se resuelve con
`credenciales.credencial("gmail")` (Administrador de Credenciales de
Windows). Nunca vive en el repo ni en un archivo de texto plano.
"""
from __future__ import annotations

import email
import email.header
import email.utils
import imaplib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Sequence

from jobpulse_v15.postulaciones import (
    DOMINIOS_PORTAL,
    Senal,
    clasificar,
    normalizar_texto,
)

logger = logging.getLogger("jobpulse.correo_postulaciones")

#: Host y puerto de IMAP sobre SSL (Gmail).
HOST_GMAIL = "imap.gmail.com"
PUERTO_GMAIL = 993

#: Nombre de la credencial en el almacen local (keyring de Windows).
CREDENCIAL_GMAIL = "gmail"

#: Dominios de los portales de empleo: el filtro por defecto del correo.
#: Viene de `postulaciones.DOMINIOS_PORTAL` (no esta hardcodeado el usuario).
DOMINIOS_POR_DEFECTO: tuple[str, ...] = tuple(
    dict.fromkeys(dominio for dominio, _portal in DOMINIOS_PORTAL)
)

#: Cuanto correo mira el colector por omision (dias).
DIAS_POR_DEFECTO = 90

_RE_ETIQUETAS_HTML = re.compile(r"<[^>]+>")
_RE_ESPACIOS = re.compile(r"[ \t\r\f\v]+")
_RE_SALTOS = re.compile(r"\n{3,}")


class ErrorCorreoPostulaciones(RuntimeError):
    """Fallo al leer el buzon (conexion, login o IMAP)."""


@dataclass(frozen=True)
class ConfigCorreo:
    """Parametros de la lectura (todo configurable, nada del usuario)."""

    host: str = HOST_GMAIL
    puerto: int = PUERTO_GMAIL
    usuario: str = ""
    carpeta: str = "INBOX"
    dias: int = DIAS_POR_DEFECTO
    dominios: tuple[str, ...] = DOMINIOS_POR_DEFECTO
    limite: int = 500

    def fecha_corte(self, hoy: datetime | None = None) -> datetime:
        base = hoy or datetime.now()
        return base - timedelta(days=max(1, int(self.dias)))


# --------------------------------------------------------------- consultas --
def consulta_gmail(dominios: Sequence[str], dias: int) -> str:
    """Consulta de Gmail (extension `X-GM-RAW`): remitentes + antiguedad."""
    partes = [f"newer_than:{max(1, int(dias))}d"]
    limpios = [str(d).strip().lstrip("@") for d in dominios if str(d).strip()]
    if limpios:
        partes.append("from:(" + " OR ".join(limpios) + ")")
    return " ".join(partes)


def consulta_imap_estandar(dias: int, fecha_corte: datetime | None = None) -> str:
    """Consulta IMAP estandar (fallback): `SINCE <fecha>`."""
    corte = fecha_corte or (datetime.now() - timedelta(days=max(1, int(dias))))
    return "SINCE " + corte.strftime("%d-%b-%Y")


def _buscar_gmail(imap: Any, consulta: str) -> list[bytes]:
    """Busca con `X-GM-RAW`; si el servidor no lo soporta, cae a `SINCE`."""
    try:
        estado, datos = imap.search(None, "X-GM-RAW", consulta)
    except Exception as exc:  # pragma: no cover - depende del servidor
        logger.warning("X-GM-RAW no disponible (%s); se usa SINCE.", exc)
        estado, datos = imap.search(None, "SINCE", consulta)
    if estado != "OK":
        raise ErrorCorreoPostulaciones(f"La busqueda IMAP fallo: {estado!r}.")
    return list(datos[0].split()) if datos and datos[0] else []


def _buscar_estandar(imap: Any, consulta: str) -> list[bytes]:
    estado, datos = imap.search(None, consulta)
    if estado != "OK":
        raise ErrorCorreoPostulaciones(f"La busqueda IMAP fallo: {estado!r}.")
    return list(datos[0].split()) if datos and datos[0] else []


# ------------------------------------------------------------- lectura -------
def _decodificar(valor: Any) -> str:
    """Decodifica cabeceras MIME (`=?utf-8?B?...?=`) a texto plano."""
    if valor is None:
        return ""
    if isinstance(valor, bytes):
        valor = valor.decode("utf-8", errors="replace")
    partes = email.header.decode_header(str(valor))
    texto: list[str] = []
    for contenido, codigo in partes:
        if isinstance(contenido, bytes):
            texto.append(contenido.decode(codigo or "utf-8", errors="replace"))
        else:
            texto.append(contenido)
    return "".join(texto)


def _cuerpo_texto(mensaje: email.message.Message) -> str:
    """Cuerpo en texto plano (si hay HTML, se le quitan las etiquetas).

    El cuerpo SOLO se usa para clasificar: nunca se guarda.
    """
    if not mensaje.is_multipart():
        payload = mensaje.get_payload(decode=True)
        if payload is None:
            return normalizar_texto(str(mensaje.get_payload()))
        return _decodificar_cuerpo(payload, mensaje.get_content_charset())
    partes: list[str] = []
    for parte in mensaje.walk():
        if parte.get_content_maintype() == "multipart":
            continue
        tipo = parte.get_content_type()
        if tipo not in ("text/plain", "text/html"):
            continue
        payload = parte.get_payload(decode=True)
        if payload is None:
            continue
        texto = _decodificar_cuerpo(payload, part.get_content_charset())
        if tipo == "text/html":
            texto = _RE_ETIQUETAS_HTML.sub(" ", texto)
        if texto.strip():
            partes.append(texto)
    return _limpiar_texto("\n".join(partes))


def _decodificar_cuerpo(payload: bytes, charset: str | None) -> str:
    for codigo in (charset, "utf-8", "latin-1"):
        if not codigo:
            continue
        try:
            return payload.decode(codigo, errors="replace")
        except (LookupError, UnicodeDecodeError):
            continue
    return payload.decode("utf-8", errors="replace")


def _limpiar_texto(texto: str) -> str:
    texto = _RE_ETIQUETAS_HTML.sub(" ", texto or "")
    texto = _RE_ESPACIOS.sub(" ", texto)
    texto = _RE_SALTOS.sub("\n\n", texto)
    return texto.strip()


def mensaje_a_diccionario(crudo: bytes | str) -> dict[str, str]:
    """Convierte un mensaje RFC822 en {remitente, asunto, cuerpo, fecha}.

    Es el punto de corte para los tests: se alimentan archivos .eml
    sinteticos, nunca la red.
    """
    if isinstance(crudo, str):
        crudo = crudo.encode("utf-8", errors="replace")
    mensaje = email.message_from_bytes(crudo)
    remitente = email.utils.parseaddr(mensaje.get("From", "") or "")[1]
    asunto = _decodificar(mensaje.get("Subject", ""))
    fecha = ""
    cabecera_fecha = mensaje.get("Date", "")
    if cabecera_fecha:
        try:
            fecha_dt = email.utils.parsedate_to_datetime(cabecera_fecha)
        except (TypeError, ValueError):
            fecha_dt = None
        if fecha_dt is not None:
            fecha = fecha_dt.strftime("%Y-%m-%d %H:%M:%S")
    return {
        "remitente": remitente,
        "asunto": asunto,
        "cuerpo": _cuerpo_texto(mensaje),
        "fecha": fecha,
    }


def mensaje_a_senal(crudo: bytes | str) -> Senal | None:
    """Clasifica un mensaje RFC822 (devuelve None si no es de postulacion)."""
    datos = mensaje_a_diccionario(crudo)
    return clasificar(
        datos["remitente"],
        datos["asunto"],
        datos["cuerpo"],
        fecha=datos["fecha"],
    )


def leer_mensajes(
    imap: Any,
    *,
    config: ConfigCorreo,
    usar_gmail: bool = True,
) -> list[bytes]:
    """Lista los mensajes crudos (RFC822) que cumplen el filtro."""
    if usar_gmail:
        consulta = consulta_gmail(config.dominios, config.dias)
        numeros = _buscar_gmail(imap, consulta)
    else:
        consulta = consulta_imap_estandar(config.dias, config.fecha_corte())
        numeros = _buscar_estandar(imap, consulta)
    if not numeros:
        return []
    numeros = numeros[-config.limite :] if config.limite > 0 else numeros
    mensajes: list[bytes] = []
    for numero in numeros:
        try:
            estado, datos = imap.fetch(numero, "(RFC822)")
        except Exception as exc:  # pragma: no cover - depende del servidor
            logger.warning("No se pudo leer el mensaje %s: %s", numero, exc)
            continue
        if estado != "OK" or not datos:
            continue
        for parte in datos:
            if isinstance(parte, tuple) and len(parte) >= 2 and parte[1]:
                mensajes.append(parte[1])
    return mensajes


def recolectar_senales(
    *,
    usuario: str,
    password: str,
    config: ConfigCorreo | None = None,
    fabrica_imap: Callable[..., Any] | None = None,
    usar_gmail: bool = True,
) -> list[Senal]:
    """Conecta al buzon, lee y clasifica las notificaciones de postulacion.

    `fabrica_imap` permite inyectar un doble en los tests (nunca red).
    """
    if not usuario or not password:
        raise ErrorCorreoPostulaciones(
            "Falta la credencial de Gmail (usuario y app-password)."
        )
    configuracion = config or ConfigCorreo(usuario=usuario)
    fabrica = fabrica_imap or imaplib.IMAP4_SSL
    try:
        imap = fabrica(configuracion.host, configuracion.puerto)
    except Exception as exc:
        raise ErrorCorreoPostulaciones(
            f"No se pudo conectar a {configuracion.host}:{configuracion.puerto}: {exc}"
        ) from exc
    senales: list[Senal] = []
    try:
        try:
            imap.login(usuario, password)
        except Exception as exc:
            raise ErrorCorreoPostulaciones(
                "El login IMAP fallo (revisa el usuario y la app-password)."
            ) from exc
        try:
            imap.select(configuracion.carpeta)
        except Exception as exc:
            raise ErrorCorreoPostulaciones(
                f"No se pudo abrir la carpeta {configuracion.carpeta!r}: {exc}"
            ) from exc
        for crudo in leer_mensajes(
            imap, config=configuracion, usar_gmail=usar_gmail
        ):
            senal = mensaje_a_senal(crudo)
            if senal is not None:
                senales.append(senal)
    finally:
        try:
            imap.logout()
        except Exception:  # pragma: no cover - cierre best effort
            pass
    return senales
