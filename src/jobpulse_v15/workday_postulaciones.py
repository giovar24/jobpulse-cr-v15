# -*- coding: utf-8 -*-
""""Mis postulaciones" de Workday: estado del PROCESO, no de aptitud.

REGLA DE DISENO (acordada 2026-11-04): el estado que devuelve el portal
(APPLIED / SCREENING / INTERVIEW / OFFER / REJECTED) describe el **proceso
de seleccion**, NO si el perfil califica. **Ser rechazado NO significa que el
perfil no sea apto para el puesto**: el reclutador humano decide por
presupuesto, timing, competencia, sesgos y azar. Estas señales se usan para
lo operativo (no reprocesar lo postulado, medir el funnel propio, revisar
posibles falsos positivos del ranking) y NUNCA para reentrenar el score de
ajuste tecnico (`viabilidad.py`).

El modulo tiene dos capas, como el resto de los scrapers del proyecto:

* **PURE** (`parsear_json_aplicaciones`, `parsear_html_aplicaciones`,
  `mapear_estado`): no toca la red y se prueba con HTML/JSON sinteticos.
* **RED** (`recolectar_aplicaciones`): reutiliza la sesion del navegador del
  usuario via CDP (el fetcher NUNCA crea un navegador: recibe el puerto).

PRIVACIDAD: del portal solo se guardan derivados minimos (estado, fecha,
referencia del aviso, titulo y empresa). Nunca la pagina completa.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit

from jobpulse_v15.postulaciones import (
    ESTADO_APPLIED,
    ESTADO_INTERVIEW,
    ESTADO_OFFER,
    ESTADO_RECRUITER,
    ESTADO_REJECTED,
    ESTADO_WITHDRAWN,
    PORTAL_WORKDAY,
    Senal,
)

logger = logging.getLogger("jobpulse.workday_postulaciones")


class ErrorWorkdayPostulaciones(RuntimeError):
    """Fallo al leer "Mis postulaciones" (portal, CDP o sesion)."""


# ------------------------------------------------------------- estados ------
#: Estados de Workday -> estados de `postulaciones`.
MAPA_ESTADOS: dict[str, str] = {
    "APPLIED": ESTADO_APPLIED,
    "SUBMITTED": ESTADO_APPLIED,
    "IN_PROGRESS": ESTADO_APPLIED,
    "SCREENING": ESTADO_RECRUITER,
    "IN_REVIEW": ESTADO_RECRUITER,
    "UNDER_REVIEW": ESTADO_RECRUITER,
    "RECRUITER": ESTADO_RECRUITER,
    "RECRUITER_CONTACT": ESTADO_RECRUITER,
    "PRE_INTERVIEW": ESTADO_INTERVIEW,
    "INTERVIEW": ESTADO_INTERVIEW,
    "PHONE_SCREEN": ESTADO_INTERVIEW,
    "TECHNICAL_INTERVIEW": ESTADO_INTERVIEW,
    "ASSESSMENT": ESTADO_INTERVIEW,
    "OFFER": ESTADO_OFFER,
    "OFFER_EXTENDED": ESTADO_OFFER,
    "HIRED": ESTADO_OFFER,
    "REJECTED": ESTADO_REJECTED,
    "NOT_SELECTED": ESTADO_REJECTED,
    "DECLINED": ESTADO_REJECTED,
    "WITHDRAWN": ESTADO_WITHDRAWN,
    "CANCELED": ESTADO_WITHDRAWN,
    "CANCELLED": ESTADO_WITHDRAWN,
}


def mapear_estado(estado: str) -> str:
    """Estado de Workday -> estado de postulacion ('' si no se conoce)."""
    clave = (estado or "").strip().upper().replace(" ", "_").replace("-", "_")
    if not clave:
        return ""
    if clave in MAPA_ESTADOS:
        return MAPA_ESTADOS[clave]
    for prefijo, destino in (
        ("INTERVIEW", ESTADO_INTERVIEW),
        ("SCREEN", ESTADO_RECRUITER),
        ("RECRUIT", ESTADO_RECRUITER),
        ("OFFER", ESTADO_OFFER),
        ("REJECT", ESTADO_REJECTED),
        ("DECLIN", ESTADO_REJECTED),
        ("WITHDRAW", ESTADO_WITHDRAWN),
        ("CANCEL", ESTADO_WITHDRAWN),
        ("APPL", ESTADO_APPLIED),
    ):
        if clave.startswith(prefijo):
            return destino
    return ""


@dataclass(frozen=True)
class AplicacionPortal:
    """Una postulacion vista en "Mis postulaciones" (derivados minimos)."""

    estado: str
    source_job_id: str = ""
    titulo: str = ""
    empresa: str = ""
    url: str = ""
    fecha: str = ""

    def a_senal(self) -> Senal:
        return Senal(
            estado=self.estado,
            portal=PORTAL_WORKDAY,
            url=self.url,
            source_job_id=self.source_job_id,
            titulo=self.titulo,
            empresa=self.empresa,
            fecha=self.fecha,
        )


def a_senales(aplicaciones: Iterable[AplicacionPortal]) -> list[Senal]:
    return [aplicacion.a_senal() for aplicacion in aplicaciones]


# --------------------------------------------------------------- referencias --
_RE_REQUISITION = re.compile(r"/job/[^?#]*/([^/?#]+)")
_RE_BASENAME = re.compile(r"([^/?#]+)/?$")


def referencia_de_url_workday(url: str) -> str:
    """El REQID del aviso a partir de la URL de Workday.

    `.../job/Heredia-Costa-Rica/Analyst_JR12345` -> `Analyst_JR12345`
    (es el `source_job_id` con el que el corpus identifica la vacante).
    """
    if not url:
        return ""
    limpia = url.split("?")[0].split("#")[0]
    coincidencia = _RE_REQUISITION.search(limpia)
    if coincidencia:
        return coincidencia.group(1)
    base = _RE_BASENAME.search(limpia)
    return base.group(1) if base else ""


# --------------------------------------------------------------- JSON --------
_CLAVES_REQUISITO = (
    "jobReqId",
    "jobPostingId",
    "jobRequisitionId",
    "externalPath",
    "jobId",
    "requisitionId",
)
_CLAVES_ESTADO = (
    "applicationStatus",
    "status",
    "jobApplicationStatus",
    "currentStatus",
    "statusLabel",
)
_CLAVES_TITULO = ("title", "jobTitle", "jobTitleText", "name")
_CLAVES_EMPRESA = ("companyName", "company", "companyText", "employerName")
_CLAVES_FECHA = ("dateApplied", "appliedDate", "datePosted", "appliedOn", "date")


def _buscar_clave(datos: dict[str, Any], claves: Sequence[str]) -> Any:
    for clave in claves:
        valor = datos.get(clave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
        if isinstance(valor, (int, float)):
            return str(valor)
    return None


def _recorrer(payload: Any) -> Iterable[dict[str, Any]]:
    """Recorre el JSON buscando objetos que parezcan una postulacion."""
    if isinstance(payload, dict):
        yield payload
        for valor in payload.values():
            yield from _recorrer(valor)
    elif isinstance(payload, list):
        for valor in payload:
            yield from _recorrer(valor)


def _aplicacion_de(datos: dict[str, Any]) -> AplicacionPortal | None:
    """Convierte un objeto JSON en postulacion (si trae estado y aviso)."""
    estado_crudo = _buscar_clave(datos, _CLAVES_ESTADO)
    if not estado_crudo:
        return None
    estado = mapear_estado(str(estado_crudo))
    if not estado:
        return None

    referencia = _buscar_clave(datos, _CLAVES_REQUISITO)
    url = ""
    if referencia and str(referencia).startswith("/"):
        url = str(referencia)
        referencia = referencia_de_url_workday(url)
    titulo = _buscar_clave(datos, _CLAVES_TITULO) or ""
    empresa = _buscar_clave(datos, _CLAVES_EMPRESA) or ""
    fecha = _buscar_clave(datos, _CLAVES_FECHA) or ""

    # Los datos anidados (`jobPostingInfo`) traen el aviso real.
    anidado = datos.get("jobPostingInfo")
    if isinstance(anidado, dict):
        referencia = referencia or _buscar_clave(anidado, _CLAVES_REQUISITO)
        titulo = titulo or _buscar_clave(anidado, _CLAVES_TITULO) or ""
        empresa = empresa or _buscar_clave(anidado, _CLAVES_EMPRESA) or ""
        fecha = fecha or _buscar_clave(anidado, _CLAVES_FECHA) or ""

    if not referencia and not titulo:
        return None
    return AplicacionPortal(
        estado=estado,
        source_job_id=str(referencia or ""),
        titulo=str(titulo or ""),
        empresa=str(empresa or ""),
        url=str(url or ""),
        fecha=str(fecha or ""),
    )


def parsear_json_aplicaciones(payload: Any) -> list[AplicacionPortal]:
    """Extrae las postulaciones de un JSON de Workday (o de su portal)."""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            return []
    vistas: set[tuple[str, str]] = set()
    aplicaciones: list[AplicacionPortal] = []
    for datos in _recorrer(payload):
        aplicacion = _aplicacion_de(datos)
        if aplicacion is None:
            continue
        clave = (aplicacion.estado, aplicacion.source_job_id or aplicacion.titulo)
        if clave in vistas:
            continue
        vistas.add(clave)
        aplicaciones.append(aplicacion)
    return aplicaciones


# --------------------------------------------------------------- HTML --------
class _ExtractorAplicaciones(HTMLParser):
    """Extrae filas de "Mis postulaciones" del HTML renderizado."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.aplicaciones: list[AplicacionPortal] = []
        self._en_fila = False
        self._fila: dict[str, Any] = {}
        self._capturando: str | None = None
        self._texto: list[str] = []

    # -- helpers
    @staticmethod
    def _automation_id(atributos: dict[str, str]) -> str:
        return (atributos.get("data-automation-id") or "").lower()

    def _cerrar_fila(self) -> None:
        if not self._en_fila:
            return
        self._en_fila = False
        fila = self._fila
        self._fila = {}
        estado = mapear_estado(str(fila.get("estado") or ""))
        if not estado:
            return
        url = str(fila.get("url") or "")
        referencia = str(fila.get("referencia") or "") or referencia_de_url_workday(url)
        titulo = str(fila.get("titulo") or "").strip()
        empresa = str(fila.get("empresa") or "").strip()
        if not referencia and not titulo:
            return
        self.aplicaciones.append(
            AplicacionPortal(
                estado=estado,
                source_job_id=referencia,
                titulo=titulo,
                empresa=empresa,
                url=url,
                fecha=str(fila.get("fecha") or ""),
            )
        )

    # -- HTMLParser
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        atributos = {clave: (valor or "") for clave, valor in attrs}
        automation = self._automation_id(atributos)
        if automation and ("application" in automation) and (
            "row" in automation or "item" in automation or "card" in automation
        ):
            self._cerrar_fila()
            self._en_fila = True
            self._fila = {}
        if not self._en_fila:
            return
        if tag == "a" and "/job/" in atributos.get("href", ""):
            self._fila["url"] = atributos["href"]
            self._fila.setdefault("referencia", referencia_de_url_workday(atributos["href"]))
            self._capturando = "titulo"
            self._texto = []
        elif "status" in automation or "estado" in automation:
            self._capturando = "estado"
            self._texto = []
        elif "company" in automation or "empresa" in automation:
            self._capturando = "empresa"
            self._texto = []
        elif "date" in automation or "fecha" in automation:
            self._capturando = "fecha"
            self._texto = []

    def handle_endtag(self, tag: str) -> None:
        if self._capturando is None:
            return
        if self._capturando == "titulo" and tag != "a":
            return
        texto = " ".join("".join(self._texto).split())
        if texto:
            self._fila[self._capturando] = texto
        self._capturando = None
        self._texto = []

    def handle_data(self, data: str) -> None:
        if self._capturando is not None:
            self._texto.append(data)

    def close(self) -> None:  # pragma: no cover - cierre del parser
        super().close()
        self._cerrar_fila()


def parsear_html_aplicaciones(html: str) -> list[AplicacionPortal]:
    """Extrae las postulaciones del HTML de "Mis postulaciones"."""
    if not html:
        return []
    extractor = _ExtractorAplicaciones()
    try:
        extractor.feed(html)
        extractor.close()
    except Exception as exc:  # pragma: no cover - HTML roto
        logger.warning("No se pudo parsear el HTML de postulaciones: %s", exc)
    return extractor.aplicaciones


# ----------------------------------------------------------------- URLs ------
def patrones_candidato(base_url: str) -> list[str]:
    """URLs candidatas del portal de "Mis postulaciones" de Workday.

    Se derivan de la URL base del sitio (`site_config` / `source_sites`): no
    hay ningun tenant hardcodeado. La sesion es la del navegador del usuario
    (CDP), asi que hace falta haber iniciado sesion en ese portal.
    """
    if not base_url:
        return []
    partes = urlsplit(base_url.strip())
    origen = f"{partes.scheme}://{partes.netloc}"
    camino = partes.path.strip("/")
    segmentos = [s for s in camino.split("/") if s]
    tenant = segmentos[0] if segmentos else ""
    tablero = segmentos[-1] if len(segmentos) > 1 else ""
    patrones: list[str] = []
    for sufijo in (
        f"{tablero}/candidate" if tablero else "",
        f"{tenant}/candidate" if tenant else "",
        f"{tenant}_candidate" if tenant else "",
        "candidate",
    ):
        if not sufijo:
            continue
        url = f"{origen}/{sufijo}"
        if url not in patrones:
            patrones.append(url)
    return patrones


# ------------------------------------------------------------------ RED ------
async def recolectar_aplicaciones(
    base_url: str,
    *,
    port: int,
    patrones: Sequence[str] | None = None,
    espera_ms: int = 4000,
) -> list[AplicacionPortal]:
    """Lee "Mis postulaciones" con la sesion del navegador (CDP).

    El fetcher NUNCA crea un navegador: se conecta al que ya esta abierto
    (el puerto lo pasa el caller).
    """
    urls = list(patrones or patrones_candidato(base_url))
    if not urls:
        raise ErrorWorkdayPostulaciones(
            "No se pudo deducir la URL del portal de postulaciones."
        )
    from playwright.async_api import async_playwright

    encontrados: list[AplicacionPortal] = []
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
        contexto = browser.contexts[0] if browser.contexts else await browser.new_context()
        pagina = await contexto.new_page()
        payloads: list[str] = []

        async def _capturar(respuesta: Any) -> None:
            url = str(getattr(respuesta, "url", ""))
            if "/wday/cxs/" not in url:
                return
            try:
                cuerpo = await respuesta.text()
            except Exception:  # pragma: no cover - depende de la pagina
                return
            if cuerpo:
                payloads.append(cuerpo)

        pagina.on("response", _capturar)
        try:
            for url in urls:
                payloads.clear()
                try:
                    await pagina.goto(url, wait_until="domcontentloaded")
                    await pagina.wait_for_timeout(espera_ms)
                except Exception as exc:
                    logger.info("Portal de postulaciones no disponible en %s: %s", url, exc)
                    continue
                html = ""
                try:
                    html = await pagina.content()
                except Exception:  # pragma: no cover
                    html = ""
                aplicaciones = []
                for cuerpo in payloads:
                    aplicaciones.extend(parsear_json_aplicaciones(cuerpo))
                if not aplicaciones:
                    aplicaciones = parsear_html_aplicaciones(html)
                if aplicaciones:
                    encontrados = aplicaciones
                    break
        finally:
            try:
                await pagina.close()
            except Exception:  # pragma: no cover
                pass
    return encontrados
