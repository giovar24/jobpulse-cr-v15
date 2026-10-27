# -*- coding: utf-8 -*-
"""Tests del login ANE empaquetado (O7.4) — sin navegador: guardas y selectores."""
import unittest
from unittest.mock import patch

from jobpulse_v15 import ane_login


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


if __name__ == "__main__":
    unittest.main()
