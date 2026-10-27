# -*- coding: utf-8 -*-
"""Login de ANE (ane.cr) sobre el Brave con CDP, con credenciales del almacén.

O7.4 (2026-10-27): mismo flujo que tenía el script ``login_ane.py`` de raíz
(selectores probados en producción), ahora como módulo del paquete para que
la UI pueda invocarlo. El script de raíz quedó como wrapper CLI.

Regla del proyecto: nada de secretos en el repo. La credencial sale de
``credencial("ANE")`` (keyring de Windows + data/empresas/credenciales.json,
fallback .env ANE_USER/ANE_PASSWORD).

El caller garantiza que hay CDP vivo (p. ej. ``asegurar_brave``); esta función
solo abre una pestaña, llena el formulario y reporta::

    login_ane(port=9222) -> {"estado": "ok"|"fallo"|"incierto"|"error", "detalle": str}

- ``ok``: sesión activa (el HTML ya muestra Puesto/Detalles o dashboard).
- ``fallo``: sigue en el formulario de login (credencial rechazada).
- ``incierto``: navegó a algo no reconocido — revisar a mano.
- ``error``: no se pudo ni intentar (DOM cambió). Sin credencial lanza
  RuntimeError con instrucciones.
"""
from __future__ import annotations

from typing import Any, Dict

from playwright.sync_api import sync_playwright

from jobpulse_v15.credenciales import credencial

LOGIN_URL = "https://www.ane.cr/Cuenta/Login"

# Selectores probados en producción (login_ane.py original, 2026-10-26).
CFG: Dict[str, Any] = {
    "login_url": LOGIN_URL,
    "user_sel": (
        "input[name='UserName'], input#UserName, input[name='username'], "
        "input[type=text], input[type=email]"
    ),
    "pass_sel": "input[type=password]",
    "submit_sel": "button[type=submit], input[type=submit], button:has-text('Ingresar')",
    "espera": 5000,
}


def login_ane(port: int = 9222) -> Dict[str, str]:
    """Hace login en ANE con la credencial del almacén y reporta el resultado."""
    cred = credencial("ANE")
    if not cred or not cred.get("usuario") or not cred.get("password"):
        raise RuntimeError(
            "No hay credencial ANE usable (usuario + password). Guárdala con: "
            "python -m jobpulse_v15 credenciales set --empresa ANE "
            "--usuario <usuario> --password <password> (o define "
            "ANE_USER/ANE_PASSWORD en .env)."
        )

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_timeout(2_000)

            u = page.query_selector(CFG["user_sel"])
            if u is None:
                return {
                    "estado": "error",
                    "detalle": (
                        f"No encontré campo usuario. Título: {page.title()} — "
                        "¿cambió el formulario de ane.cr?"
                    ),
                }
            u.fill(cred["usuario"])

            pw = page.query_selector(CFG["pass_sel"])
            if pw is None:
                return {"estado": "error", "detalle": "No encontré campo password"}
            pw.fill(cred["password"])

            btn = page.query_selector(CFG["submit_sel"])
            if btn is None:
                return {"estado": "error", "detalle": "No encontré botón submit"}
            btn.click()
            page.wait_for_timeout(CFG["espera"])

            html = page.content()
            if "Puesto/Detalles" in html or "dashboard" in html.lower():
                return {"estado": "ok", "detalle": "Sesión ANE activa"}
            if "loginForm" in html or "Cuenta/RegistroUsuario" in html:
                return {
                    "estado": "fallo",
                    "detalle": (
                        f"Siguió en login (título: {page.title()}) — revisa "
                        "usuario/password o el sitio"
                    ),
                }
            return {"estado": "incierto", "detalle": f"Título: {page.title()} — URL: {page.url}"}
        finally:
            page.close()
