# -*- coding: utf-8 -*-
"""Tests del login ANE empaquetado (O7.4) y del cierre ordenado (O12 · 1.5).

Sin navegador: guardas, selectores y la lógica del wrapper ``login_ane.py``.

Contexto de 1.5 (verificado 2026-11-05): el wrapper cerraba con
``process.terminate()``/``kill()`` el Brave que había abierto, Chromium no
volcaba las cookies al perfil y el barrido siguiente daba 0 avisos ("ANE: sin
sesión de detalle"). Ahora el cierre es ordenado (``Browser.close`` por CDP) y
se puede conservar el navegador vivo para raspar de inmediato.
"""
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from jobpulse_v15 import ane_login

RAIZ = Path(__file__).resolve().parents[1]


class TestGuardasLoginAne(unittest.TestCase):
    def test_sin_credencial_error_claro(self):
        with patch.object(ane_login, "credencial", lambda empresa: None):
            with self.assertRaisesRegex(RuntimeError, "credencial ANE"):
                ane_login.login_ane(9222)

    def test_credencial_incompleta_error_claro(self):
        with patch.object(ane_login, "credencial", lambda empresa: {"usuario": "x"}):
            with self.assertRaisesRegex(RuntimeError, "credencial ANE"):
                ane_login.login_ane(9222)

    def test_selectores_y_url_estables(self):
        # Selectores probados en producción (login_ane.py original,
        # 2026-10-26): si ane.cr cambia el DOM, el login fallará en runtime
        # con estado "error" y detalle del título de la página.
        self.assertEqual(ane_login.LOGIN_URL, "https://www.ane.cr/Cuenta/Login")
        self.assertIn("input[name='UserName']", ane_login.CFG["user_sel"])
        self.assertIn("input[type=password]", ane_login.CFG["pass_sel"])
        self.assertIn("input[type=submit]", ane_login.CFG["submit_sel"])
        self.assertEqual(ane_login.CFG["espera"], 5000)


class _Sesion:
    def __init__(self):
        self.enviados = []

    def send(self, metodo):
        self.enviados.append(metodo)


class _PlaywrightFalso:
    """``sync_playwright()`` mínimo: connect_over_cdp -> browser falso."""

    def __init__(self, browser=None, error=None):
        self._browser = browser
        self._error = error
        self.url = None

    def __call__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    @property
    def chromium(self):
        return self

    def connect_over_cdp(self, url):
        self.url = url
        if self._error:
            raise self._error
        return self._browser


def _browser_falso(sesion):
    pagina = SimpleNamespace(
        context=SimpleNamespace(new_cdp_session=lambda _page: sesion)
    )
    return SimpleNamespace(contexts=[SimpleNamespace(pages=[pagina])])


class TestCierreOrdenado(unittest.TestCase):
    def test_envia_browser_close_por_cdp(self):
        sesion = _Sesion()
        falso = _PlaywrightFalso(_browser_falso(sesion))
        with patch.object(ane_login, "sync_playwright", falso):
            ok = ane_login.cerrar_brave_ordenado(9333)

        self.assertTrue(ok)
        self.assertEqual(sesion.enviados, ["Browser.close"])
        self.assertEqual(falso.url, "http://127.0.0.1:9333")

    def test_sin_conexion_devuelve_false(self):
        falso = _PlaywrightFalso(error=OSError("CDP muerto"))
        with patch.object(ane_login, "sync_playwright", falso):
            self.assertFalse(ane_login.cerrar_brave_ordenado(9222))

    def test_contexto_sin_paginas_crea_una(self):
        sesion = _Sesion()
        creada = SimpleNamespace(
            context=SimpleNamespace(new_cdp_session=lambda _page: sesion)
        )
        contexto = SimpleNamespace(pages=[], new_page=lambda: creada)
        browser = SimpleNamespace(contexts=[contexto])
        falso = _PlaywrightFalso(browser)
        with patch.object(ane_login, "sync_playwright", falso):
            self.assertTrue(ane_login.cerrar_brave_ordenado(9222))
        self.assertEqual(sesion.enviados, ["Browser.close"])


class TestWrapperCli(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "login_ane_script", RAIZ / "login_ane.py"
        )
        self.script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.script)

    def test_brave_ajeno_no_se_toca(self):
        cerrar = MagicMock(return_value=True)
        with patch.object(self.script, "asegurar_brave", return_value=None), \
                patch.object(self.script, "login_ane",
                             return_value={"estado": "ok", "detalle": "sesión"}), \
                patch.object(self.script, "cerrar_brave_ordenado", cerrar):
            codigo = self.script.main([])

        self.assertEqual(codigo, 0)
        cerrar.assert_not_called()

    def test_brave_que_abrimos_se_cierra_ordenado(self):
        mgr = MagicMock()
        cerrar = MagicMock(return_value=True)
        with patch.object(self.script, "asegurar_brave", return_value=mgr), \
                patch.object(self.script, "login_ane",
                             return_value={"estado": "ok", "detalle": "sesión"}), \
                patch.object(self.script, "cerrar_brave_ordenado", cerrar), \
                patch.object(self.script, "cdp_vivo", return_value=False), \
                patch.object(self.script.time, "sleep", lambda _s: None):
            codigo = self.script.main([])

        self.assertEqual(codigo, 0)
        cerrar.assert_called_once_with(9222)
        mgr.stop_brave_sync.assert_not_called()

    def test_mantener_abierto_no_cierra_ni_mata(self):
        mgr = MagicMock()
        cerrar = MagicMock(return_value=True)
        with patch.object(self.script, "asegurar_brave", return_value=mgr), \
                patch.object(self.script, "login_ane",
                             return_value={"estado": "ok", "detalle": "sesión"}), \
                patch.object(self.script, "cerrar_brave_ordenado", cerrar):
            codigo = self.script.main(["--mantener-abierto"])

        self.assertEqual(codigo, 0)
        cerrar.assert_not_called()
        mgr.stop_brave_sync.assert_not_called()

    def test_si_browser_close_falla_se_mata_el_proceso(self):
        mgr = MagicMock()
        with patch.object(self.script, "asegurar_brave", return_value=mgr), \
                patch.object(self.script, "login_ane",
                             return_value={"estado": "fallo", "detalle": "x"}), \
                patch.object(self.script, "cerrar_brave_ordenado",
                             return_value=False):
            codigo = self.script.main([])

        self.assertEqual(codigo, 1)
        mgr.stop_brave_sync.assert_called_once_with()

    def test_login_fallido_devuelve_1(self):
        with patch.object(self.script, "asegurar_brave", return_value=None), \
                patch.object(self.script, "login_ane",
                             return_value={"estado": "fallo", "detalle": "x"}):
            self.assertEqual(self.script.main([]), 1)

    def test_puerto_configurable(self):
        visto = {}

        def _login(port):
            visto["port"] = port
            return {"estado": "ok", "detalle": "sesión"}

        with patch.object(self.script, "asegurar_brave", return_value=None), \
                patch.object(self.script, "login_ane", _login):
            self.assertEqual(self.script.main(["--port", "9333"]), 0)
        self.assertEqual(visto["port"], 9333)


if __name__ == "__main__":
    unittest.main()
