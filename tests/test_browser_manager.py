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


def _puerto_libre() -> int:
    """Puerto TCP libre en localhost."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


def _listener() -> socket.socket:
    """Socket que escucha (simula un navegador con CDP)."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    return srv


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
        return _puerto_libre()

    def _listener(self) -> socket.socket:
        return _listener()

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


class TestPuertoCDPConfigurable(unittest.TestCase):
    """BRAVE_CDP_PORT: el puerto CDP se configura (antes estaba fijo en 9222)."""

    def test_lee_el_puerto_del_entorno(self):
        with patch.dict(os.environ, {"BRAVE_CDP_PORT": "9333"}):
            self.assertEqual(bm.puerto_cdp_configurado(), 9333)

    def test_sin_variable_usa_el_predeterminado(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BRAVE_CDP_PORT", None)
            self.assertEqual(bm.puerto_cdp_configurado(), bm.PUERTO_CDP_DEFECTO)

    def test_valor_invalido_cae_al_predeterminado(self):
        for valor in ("abc", "80", "70000", ""):
            with self.subTest(valor=valor):
                with patch.dict(os.environ, {"BRAVE_CDP_PORT": valor}):
                    self.assertEqual(bm.puerto_cdp_configurado(),
                                     bm.PUERTO_CDP_DEFECTO)

    def test_brave_manager_toma_el_puerto_del_entorno(self):
        with patch.dict(os.environ, {"BRAVE_CDP_PORT": "9444"}):
            mgr = bm.BraveManager(brave_bin="x")
            self.assertEqual(mgr.cdp_port, 9444)
            self.assertIn("--remote-debugging-port=9444", mgr._build_args())

    def test_el_puerto_explícito_manda_sobre_el_entorno(self):
        with patch.dict(os.environ, {"BRAVE_CDP_PORT": "9444"}):
            mgr = bm.BraveManager(brave_bin="x", cdp_port=9555)
            self.assertEqual(mgr.cdp_port, 9555)

    def test_cdp_vivo_sin_puerto_usa_el_configurado(self):
        srv = _listener()
        try:
            puerto = srv.getsockname()[1]
            with patch.dict(os.environ, {"BRAVE_CDP_PORT": str(puerto)}):
                self.assertTrue(bm.cdp_vivo())
        finally:
            srv.close()
        # Puerto cerrado → False.
        with patch.dict(os.environ, {"BRAVE_CDP_PORT": str(puerto)}):
            self.assertFalse(bm.cdp_vivo())

    def test_asegurar_brave_sin_puerto_usa_el_configurado(self):
        puerto = _puerto_libre()
        visto = {}

        class _MgrFake:
            def __init__(self, *, cdp_port, **kw):
                self.cdp_port = cdp_port
                visto["puerto"] = cdp_port

            def start_brave(self):
                return self.cdp_port

        with patch.dict(os.environ, {"BRAVE_CDP_PORT": str(puerto)}):
            with patch.object(bm, "BraveManager", _MgrFake):
                bm.asegurar_brave()
        self.assertEqual(visto["puerto"], puerto)


class TestHelpersBrave(unittest.TestCase):
    """Ayudantes para la tarjeta de navegador de la UI v2."""

    def test_detectar_brave_devuelve_none_si_no_encuentra(self):
        with patch.object(bm.BraveManager, "_detect_brave",
                          side_effect=RuntimeError("no")):
            self.assertIsNone(bm.detectar_brave())

    def test_detectar_brave_devuelve_la_ruta(self):
        with patch.object(bm.BraveManager, "_detect_brave",
                          return_value="C:/brave.exe"):
            self.assertEqual(bm.detectar_brave(), "C:/brave.exe")

    def test_perfiles_disponibles_lista_las_carpetas(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            user_data = base / "BraveSoftware" / "Brave-Browser" / "User Data"
            (user_data / "Default").mkdir(parents=True)
            (user_data / "Default" / "Preferences").write_text("{}",
                                                               encoding="utf-8")
            (user_data / "Profile 1").mkdir()
            (user_data / "Profile 1" / "Preferences").write_text("{}",
                                                                  encoding="utf-8")
            # Carpeta de componente de Brave: NO es un perfil.
            (user_data / "GPUPersistentCache").mkdir()
            with patch.dict(os.environ, {"LOCALAPPDATA": str(base)}):
                self.assertEqual(bm.perfiles_disponibles(),
                                 ["Default", "Profile 1"])

    def test_perfiles_disponibles_vacio_si_no_hay_brave(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LOCALAPPDATA": str(Path(tmp))}):
                self.assertEqual(bm.perfiles_disponibles(), [])


if __name__ == "__main__":
    unittest.main()
