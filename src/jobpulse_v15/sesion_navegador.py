# -*- coding: utf-8 -*-
"""Sesiones del navegador: guardar y restaurar la cookie de un sitio.

PROBLEMA (medido en vivo 2026-11-06): ANE usa la cookie ``ASP.NET_SessionId``,
que es una **cookie de SESIÓN** (``expires = -1``). Chromium **no** escribe las
cookies de sesión en disco al salir: da igual que el cierre sea ordenado
(``Browser.close`` por CDP). Al reabrir Brave, la sesión de ANE se había
perdido y el barrido decía "ANE: sin sesión de detalle" → 0 avisos.

O sea: el cierre ordenado de la Ola 1.5 arregla el caso "el script abrió
Brave, lo mató y luego se raspa", pero **NO** arregla "se raspa en un
arranque nuevo de Brave". La sesión de ANE vive en la memoria del proceso.

SOLUCIÓN: después de un login exitoso se guarda la sesión (las cookies del
sitio) en ``data/usuario/sesiones/<sitio>.json`` y, cuando el scraper
detecta que falta la sesión, la restaura en el contexto del navegador.

REGLA DE SEGURIDAD: el archivo contiene un token de sesión (es un SECRET).
Vive en ``data/usuario/`` (ignorado por git a propósito) y nunca se sube al
repo. Se puede borrar a mano sin consecuencias: lo único que se pierde es la
sesión guardada y hay que volver a iniciar sesión.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger("jobpulse.sesion_navegador")

RAIZ = Path(__file__).resolve().parents[2]
SESIONES_DIR = RAIZ / "data" / "usuario" / "sesiones"

# Campos de cookie que Playwright acepta en ``add_cookies``.
_CAMPOS = ("name", "value", "domain", "path", "expires", "httpOnly",
           "secure", "sameSite")
_PATRON_NOMBRE = re.compile(r"[^A-Za-z0-9_.-]+")


def _nombre_seguro(nombre: str) -> str:
    """Nombre de archivo seguro (nada de rutas ni separadores)."""
    limpio = _PATRON_NOMBRE.sub("_", (nombre or "").strip()).strip("._")
    if not limpio:
        raise ValueError("El nombre de la sesión no puede estar vacío.")
    return limpio


def ruta_sesion(nombre: str) -> Path:
    """Ruta del archivo donde vive la sesión guardada."""
    return SESIONES_DIR / f"{_nombre_seguro(nombre)}.json"


def _cookies_del_dominio(
    cookies: Iterable[Dict[str, Any]], dominio: str
) -> List[Dict[str, Any]]:
    """Cookies del dominio (o sus subdominios), ya depuradas para Playwright."""
    base = (dominio or "").lstrip(".").lower()
    salida: List[Dict[str, Any]] = []
    for cookie in cookies or []:
        if not isinstance(cookie, dict):
            continue
        dom = str(cookie.get("domain") or "").lstrip(".").lower()
        if base and not (dom == base or dom.endswith("." + base)):
            continue
        limpio: Dict[str, Any] = {}
        for campo in _CAMPOS:
            if campo not in cookie:
                continue
            valor = cookie[campo]
            if campo == "expires":
                try:
                    valor = float(valor)
                except (TypeError, ValueError):
                    continue
                if valor <= 0:
                    # Cookie de sesión: se omite `expires` para que el
                    # navegador la trate como temporal (igual que el origen).
                    continue
                valor = int(valor)
            if campo == "sameSite" and valor == "None" and not limpio.get("secure"):
                # Playwright rechaza SameSite=None sin Secure: se quita el
                # atributo (el navegador vuelve al valor por defecto).
                continue
            limpio[campo] = valor
        if limpio.get("name") and "value" in limpio:
            salida.append(limpio)
    return salida


def guardar_cookies(
    nombre: str,
    cookies: Iterable[Dict[str, Any]],
    dominio: str,
) -> bool:
    """Guarda las cookies del dominio en ``data/usuario/sesiones/``.

    Devuelve True si se escribió el archivo.
    """
    selected = _cookies_del_dominio(cookies, dominio)
    if not selected:
        logger.info("Sesión %s: no hay cookies de %s para guardar.", nombre, dominio)
        return False
    ruta = ruta_sesion(nombre)
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sitio": nombre,
            "dominio": dominio,
            "guardado_en": datetime.now().isoformat(timespec="seconds"),
            "cookies": selected,
        }
        ruta.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as e:
        logger.warning("Sesión %s: no se pudo guardar (%s).", nombre, e)
        return False
    logger.info(
        "Sesión %s guardada (%d cookie(s) de %s) en %s.",
        nombre, len(selected), dominio, ruta,
    )
    return True


def leer_cookies(nombre: str) -> List[Dict[str, Any]]:
    """Cookies guardadas de la sesión (lista vacía si no hay archivo)."""
    ruta = ruta_sesion(nombre)
    if not ruta.is_file():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning("Sesión %s: archivo ilegible (%s).", nombre, e)
        return []
    cookies = datos.get("cookies") if isinstance(datos, dict) else None
    return [c for c in (cookies or []) if isinstance(c, dict)]


def hay_sesion(nombre: str) -> bool:
    """¿Hay una sesión guardada para ese sitio?"""
    return bool(leer_cookies(nombre))


def borrar_sesion(nombre: str) -> bool:
    """Borra la sesión guardada (la sesión guardada caduca sola en el servidor)."""
    ruta = ruta_sesion(nombre)
    try:
        if ruta.is_file():
            ruta.unlink()
            return True
    except OSError as e:
        logger.warning("Sesión %s: no se pudo borrar (%s).", nombre, e)
    return False


# ---------------------------------------------------------------------------
# Adaptadores de Playwright (API sync y async)
# ---------------------------------------------------------------------------

def guardar_sesion_sync(ctx: Any, nombre: str, dominio: str) -> bool:
    """Guarda la sesión de un contexto de Playwright (API síncrona)."""
    try:
        cookies = ctx.cookies()
    except Exception as e:  # pragma: no cover - depende del navegador
        logger.warning("Sesión %s: no se pudieron leer las cookies (%s).", nombre, e)
        return False
    return guardar_cookies(nombre, cookies, dominio)


def restaurar_sesion_sync(ctx: Any, nombre: str) -> bool:
    """Restaura la sesión guardada en un contexto (API síncrona)."""
    cookies = leer_cookies(nombre)
    if not cookies:
        return False
    try:
        ctx.add_cookies(cookies)
    except Exception as e:
        logger.warning("Sesión %s: no se pudo restaurar (%s).", nombre, e)
        return False
    logger.info("Sesión %s restaurada (%d cookie(s)).", nombre, len(cookies))
    return True


async def guardar_sesion_async(ctx: Any, nombre: str, dominio: str) -> bool:
    """Guarda la sesión de un contexto de Playwright (API asíncrona)."""
    try:
        cookies = await ctx.cookies()
    except Exception as e:  # pragma: no cover - depende del navegador
        logger.warning("Sesión %s: no se pudieron leer las cookies (%s).", nombre, e)
        return False
    return guardar_cookies(nombre, cookies, dominio)


async def restaurar_sesion_async(ctx: Any, nombre: str) -> bool:
    """Restaura la sesión guardada en un contexto (API asíncrona)."""
    cookies = leer_cookies(nombre)
    if not cookies:
        return False
    try:
        await ctx.add_cookies(cookies)
    except Exception as e:
        logger.warning("Sesión %s: no se pudo restaurar (%s).", nombre, e)
        return False
    logger.info("Sesión %s restaurada (%d cookie(s)).", nombre, len(cookies))
    return True


def resumen_sesion(nombre: str) -> Optional[str]:
    """Fecha de guardado de la sesión (None si no hay)."""
    ruta = ruta_sesion(nombre)
    if not ruta.is_file():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(datos, dict):
        return str(datos.get("guardado_en") or "")
    return None
