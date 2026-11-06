# -*- coding: utf-8 -*-
"""SESIÓN DEL NAVEGADOR: guardar/restaurar la cookie de sesión (O13).

Contexto (medido en vivo 2026-11-06): ANE usa la cookie ``ASP.NET_SessionId``,
que es de SESIÓN (``expires = -1``). Chromium **no** escribe las cookies de
sesión en disco al salir: da igual que el cierre sea ordenado. Al reabrir
Brave, la sesión de ANE se perdía y el barrido decía "sin sesión de detalle".

Estos tests fijan el contrato del módulo `sesion_navegador`:

* solo se guardan las cookies del sitio (no todo el tarro de cookies);
* las cookies de sesión se guardan SIN `expires` (siguen siendo de sesión);
* el archivo vive en `data/usuario/sesiones/` (¡fuera del repo!);
* restaurar sin archivo no hace nada (y no inventa cookies);
* si la sesión guardada caducó en el servidor, se borra (no se reintenta
  para siempre).
"""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import ane  # noqa: E402
from jobpulse_v15 import sesion_navegador as sn  # noqa: E402

COOKIES_ANE = [
    {
        "name": "ASP.NET_SessionId",
        "value": "abc123",
        "domain": "www.ane.cr",
        "path": "/",
        "expires": -1,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None",
    },
    {
        "name": "ApplicationGatewayAffinity",
        "value": "xyz",
        "domain": "www.ane.cr",
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": False,
        "sameSite": "Lax",
    },
]

COOKIES_OTRO_SITIO = [
    {
        "name": "OTRO",
        "value": "no",
        "domain": ".example.com",
        "path": "/",
        "expires": -1,
    },
]

# La ruta REAL (antes de parchearla a un temporal) tiene que estar bajo
# `data/usuario/`: la sesión es un secret y el repo no la lleva.
SESIONES_DIR_REAL = sn.SESIONES_DIR


class BaseSesion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp_dir.name)
        # Las rutas del módulo apuntan a `data/usuario/sesiones/`; en el
        # test se redirigen a un temporal (el repo nunca se toca).
        patcher = patch.object(sn, "SESIONES_DIR", self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)


class TestGuardarCookies(BaseSesion):
    def test_guarda_solo_las_cookies_del_dominio(self):
        ok = sn.guardar_cookies(
            "ane", COOKIES_ANE + COOKIES_OTRO_SITIO, "ane.cr"
        )
        self.assertTrue(ok)
        guardadas = sn.leer_cookies("ane")
        nombres = {c["name"] for c in guardadas}
        self.assertEqual(nombres, {"ASP.NET_SessionId", "ApplicationGatewayAffinity"})
        self.assertNotIn("OTRO", nombres)

    def test_la_cookie_de_sesion_se_guarda_sin_expires(self):
        sn.guardar_cookies("ane", COOKIES_ANE, "ane.cr")
        cookie = next(c for c in sn.leer_cookies("ane")
                      if c["name"] == "ASP.NET_SessionId")
        # Sin `expires` el navegador la trata como cookie de sesión.
        self.assertNotIn("expires", cookie)
        self.assertEqual(cookie["value"], "abc123")
        self.assertTrue(cookie["httpOnly"])

    def test_una_cookie_persistente_conserva_su_vencimiento(self):
        cookies = [dict(COOKIES_ANE[0], expires=13380000000000000)]
        sn.guardar_cookies("ane", cookies, "ane.cr")
        cookie = sn.leer_cookies("ane")[0]
        self.assertEqual(cookie["expires"], 13380000000000000)

    def test_sin_cookies_del_dominio_no_escribe_nada(self):
        ok = sn.guardar_cookies("ane", COOKIES_OTRO_SITIO, "ane.cr")
        self.assertFalse(ok)
        self.assertFalse(sn.hay_sesion("ane"))

    def test_el_archivo_queda_fuera_del_repo(self):
        """La sesión es un SECRET: vive en data/usuario/ (gitignoreado)."""
        self.assertTrue(
            str(SESIONES_DIR_REAL).replace("\\", "/").endswith("data/usuario/sesiones"),
            SESIONES_DIR_REAL,
        )
        sn.guardar_cookies("ane", COOKIES_ANE, "ane.cr")
        self.assertTrue(sn.ruta_sesion("ane").is_file())

    def test_el_nombre_no_puede_escapar_del_directorio(self):
        ruta = sn.ruta_sesion("../../evil")
        self.assertEqual(ruta.parent, self.dir)


class TestLeerYBorrar(BaseSesion):
    def test_leer_sin_archivo_devuelve_vacio(self):
        self.assertEqual(sn.leer_cookies("ane"), [])
        self.assertFalse(sn.hay_sesion("ane"))

    def test_borrar_quita_el_archivo(self):
        sn.guardar_cookies("ane", COOKIES_ANE, "ane.cr")
        self.assertTrue(sn.borrar_sesion("ane"))
        self.assertFalse(sn.hay_sesion("ane"))
        # Borrar dos veces no es un error.
        self.assertFalse(sn.borrar_sesion("ane"))

    def test_un_archivo_ilegible_no_revienta(self):
        sn.ruta_sesion("ane").write_text("{no es json", encoding="utf-8")
        self.assertEqual(sn.leer_cookies("ane"), [])


class ContextoFalso:
    """Contexto de Playwright mínimo (API sync)."""

    def __init__(self, cookies=()):
        self._cookies = list(cookies)
        self.agregadas = []

    def cookies(self):
        return list(self._cookies)

    def add_cookies(self, cookies):
        self.agregadas.extend(cookies)


class ContextoFalsoAsync:
    """Contexto de Playwright mínimo (API async)."""

    def __init__(self, cookies=()):
        self._cookies = list(cookies)
        self.agregadas = []

    async def cookies(self):
        return list(self._cookies)

    async def add_cookies(self, cookies):
        self.agregadas.extend(cookies)


class TestAdaptadores(BaseSesion):
    def test_guardar_desde_un_contexto_sync(self):
        ctx = ContextoFalso(COOKIES_ANE + COOKIES_OTRO_SITIO)
        self.assertTrue(sn.guardar_sesion_sync(ctx, "ane", "ane.cr"))
        self.assertEqual(len(sn.leer_cookies("ane")), 2)

    def test_restaurar_desde_un_contexto_sync(self):
        sn.guardar_cookies("ane", COOKIES_ANE, "ane.cr")
        ctx = ContextoFalso()
        self.assertTrue(sn.restaurar_sesion_sync(ctx, "ane"))
        self.assertEqual(len(ctx.agregadas), 2)

    def test_restaurar_sin_archivo_no_hace_nada(self):
        ctx = ContextoFalso()
        self.assertFalse(sn.restaurar_sesion_sync(ctx, "ane"))
        self.assertEqual(ctx.agregadas, [])

    def test_restaurar_desde_un_contexto_async(self):
        sn.guardar_cookies("ane", COOKIES_ANE, "ane.cr")
        ctx = ContextoFalsoAsync()
        self.assertTrue(asyncio.run(sn.restaurar_sesion_async(ctx, "ane")))
        self.assertEqual(len(ctx.agregadas), 2)

    def test_guardar_desde_un_contexto_async(self):
        ctx = ContextoFalsoAsync(COOKIES_ANE)
        self.assertTrue(asyncio.run(sn.guardar_sesion_async(ctx, "ane", "ane.cr")))
        self.assertTrue(sn.hay_sesion("ane"))


class TestAneRestauraLaSesion(unittest.TestCase):
    """ANE: si no hay sesión, se restaura la guardada; si caducó, se borra."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp_dir.name)
        patcher = patch.object(sn, "SESIONES_DIR", self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)
        self.fetcher = ane.AneFetcher()

    def test_sin_sesion_guardada_no_hay_que_restaurar(self):
        ctx = ContextoFalsoAsync()
        with patch.object(ane, "restaurar_sesion_async", return_value=False) as rest:
            async def _sesion(ctx):
                return False
            with patch.object(self.fetcher, "_sesion_activa", side_effect=_sesion):
                ok = asyncio.run(self.fetcher._asegurar_sesion(ctx))
        self.assertFalse(ok)
        rest.assert_not_called()

    def test_la_sesion_guardada_se_restaura_y_sirve(self):
        sn.guardar_cookies("ane", COOKIES_ANE, "ane.cr")
        llamadas = []

        async def _sesion_activa(ctx):
            # La primera comprobación falla (navegador recién abierto),
            # la segunda (tras restaurar) da la sesión.
            llamadas.append(1)
            return len(llamadas) > 1

        with patch.object(self.fetcher, "_sesion_activa", side_effect=_sesion_activa):
            ok = asyncio.run(self.fetcher._asegurar_sesion(ContextoFalsoAsync()))
        self.assertTrue(ok)
        self.assertEqual(len(llamadas), 2)

    def test_si_la_sesion_guardada_caduca_se_borra(self):
        sn.guardar_cookies("ane", COOKIES_ANE, "ane.cr")
        with patch.object(self.fetcher, "_sesion_activa", return_value=False):
            ok = asyncio.run(self.fetcher._asegurar_sesion(ContextoFalsoAsync()))
        self.assertFalse(ok)
        self.assertFalse(sn.hay_sesion("ane"))

    def test_el_archivo_guardado_es_json_legible(self):
        sn.guardar_cookies("ane", COOKIES_ANE, "ane.cr")
        datos = json.loads(sn.ruta_sesion("ane").read_text(encoding="utf-8"))
        self.assertEqual(datos["dominio"], "ane.cr")
        self.assertTrue(datos["guardado_en"])
        self.assertEqual(datos["cookies"][0]["name"], "ASP.NET_SessionId")


if __name__ == "__main__":
    unittest.main()
