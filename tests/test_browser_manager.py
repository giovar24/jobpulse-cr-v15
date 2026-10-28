# -*- coding: utf-8 -*-
"""Tests de BraveManager: perfil raíz User Data (fix O7.1), args, CDP y ciclo
asegurar_brave/stop_brave_sync (O7.2). Sin navegador real: sockets y fakes."""
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jobpulse_v15 import browser_manager as bm


def _arbol_brave(base: Path) -> Path:
    """Crea LOCALAPPDATA falso con User Data y perfiles Default/Profile 1."""
    user_data = base / "BraveSoftware" / "Brave-Browser" / "User Data"
    (user_data / "Default").mkdir(parents=True)
    (user_data / "Profile 1").mkdir()
    return user_data


class _ProcFake:
    """Popen de mentira: poll/terminate/wait/kill como el real."""

    def __init__(self):
        self.vivo = True

    def poll(self):
        return None if self.vivo else 0

    def terminate(self):
        self.vivo = False

    def kill(self):
        self.vivo = False

    def wait(self, timeout=None):
        return None


class TestUserDataDirRaiz(unittest.TestCase):
    """O7.1: --user-data-dir debe apuntar a la RAÍZ, no a User Data\\Default."""

    def test_apunta_a_la_raiz_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raiz = _arbol_brave(base)
            with patch.dict(os.environ, {"LOCALAPPDATA": str(base)}):
                mgr = bm.BraveManager(brave_bin="x")
                self.assertEqual(mgr._get_user_data_dir(), raiz)
                self.assertEqual(mgr._get_user_data_dir().name, "User Data")

    def test_perfil_inexistente_error_claro(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _arbol_brave(base)
            with patch.dict(os.environ, {"LOCALAPPDATA": str(base)}):
                mgr = bm.BraveManager(brave_bin="x", brave_perfil="PerfilX")
                with self.assertRaisesRegex(RuntimeError, "PerfilX"):
                    mgr._get_user_data_dir()

    def test_build_args_incluye_profile_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LOCALAPPDATA": str(Path(tmp))}):
                mgr = bm.BraveManager(brave_bin="x", cdp_port=9333, brave_perfil="Default")
                args = mgr._build_args()
                self.assertIn("--remote-debugging-port=9333", args)
                self.assertIn("--profile-directory=Default", args)


class TestCdpYAsegurar(unittest.TestCase):
    def _puerto_libre(self) -> int:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
        s.close()
        return puerto

    def _listener(self) -> socket.socket:
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        return srv

    def test_cdp_vivo_falso_en_puerto_cerrado(self):
        self.assertFalse(bm.cdp_vivo(self._puerto_libre()))

    def test_cdp_vivo_verdadero_con_listener(self):
        srv = self._listener()
        try:
            self.assertTrue(bm.cdp_vivo(srv.getsockname()[1]))
        finally:
            srv.close()

    def test_asegurar_brave_none_si_cdp_vivo(self):
        srv = self._listener()
        try:
            self.assertIsNone(bm.asegurar_brave(srv.getsockname()[1]))
        finally:
            srv.close()

    def test_asegurar_brave_arranca_y_devuelve_manager(self):
        puerto = self._puerto_libre()

        class _MgrFake:
            def __init__(self, *, cdp_port, **kw):
                self.cdp_port = cdp_port

            def start_brave(self):
                return self.cdp_port

        with patch.object(bm, "BraveManager", _MgrFake):
            mgr = bm.asegurar_brave(puerto)
        self.assertIsInstance(mgr, _MgrFake)
        self.assertEqual(mgr.cdp_port, puerto)

    def test_stop_brave_sync_termina_proceso(self):
        mgr = bm.BraveManager(brave_bin="x")
        proc = _ProcFake()
        mgr._process = proc
        mgr.stop_brave_sync()
        self.assertFalse(proc.vivo)
        self.assertIsNone(mgr._process)

    def test_stop_brave_sync_idempotente(self):
        mgr = bm.BraveManager(brave_bin="x")
        mgr.stop_brave_sync()  # sin proceso: no debe fallar

    def test_plataformas_navegador_conocidas(self):
        self.assertEqual(set(bm.PLATAFORMAS_NAVEGADOR), {"ane", "indeed", "linkedin", "elempleo"})


if __name__ == "__main__":
    unittest.main()
