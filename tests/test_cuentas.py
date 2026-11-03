# -*- coding: utf-8 -*-
"""Tests de las cuentas de login (credenciales) de la UI v2.

Nada de red, nada de keyring real, nada de archivos del usuario: las rutas
de `jobpulse_v15.credenciales` se apuntan a un directorio temporal y el
almacén seguro se simula.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import credenciales
from jobpulse_v15.ui_v2.data.cuentas import CuentasStore, SitioCuenta


class _AlmacenFalso:
    """Simula el Administrador de Credenciales (keyring)."""

    def __init__(self) -> None:
        self.claves: dict[str, str] = {}

    def guardar(self, empresa: str, password: str) -> bool:
        self.claves[credenciales._norm(empresa)] = password
        return True

    def leer(self, empresa: str) -> str | None:
        return self.claves.get(credenciales._norm(empresa))

    def borrar(self, empresa: str) -> None:
        self.claves.pop(credenciales._norm(empresa), None)


class TestCredencialesBase(unittest.TestCase):
    """Base: archivos temporales + keyring simulado."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.almacen = _AlmacenFalso()
        parches = [
            unittest.mock.patch.object(credenciales, "CRED_JSON",
                                       base / "credenciales.json"),
            unittest.mock.patch.object(credenciales, "REQ_JSON",
                                       base / "login_requerido.json"),
            unittest.mock.patch.object(credenciales, "PENDING_JSON",
                                       base / "pending_login.json"),
            unittest.mock.patch.object(credenciales, "LOGIN_SITES_JSON",
                                       base / "login_sites.json"),
            unittest.mock.patch.object(credenciales, "_password_guardar",
                                       self.almacen.guardar),
            unittest.mock.patch.object(credenciales, "_password_leer",
                                       self.almacen.leer),
            unittest.mock.patch.object(credenciales, "_password_borrar",
                                       self.almacen.borrar),
        ]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def _sitio(self, empresa: str) -> SitioCuenta:
        store = CuentasStore()
        return next(s for s in store.sitios() if s.empresa.casefold() == empresa.casefold())


class TestListaDeSitios(TestCredencialesBase):
    """LA LISTA: qué sitios piden login y con qué estado."""

    def test_los_seeds_aparecen_sin_credencial(self):
        sitios = CuentasStore().sitios()
        nombres = {s.empresa.casefold() for s in sitios}
        self.assertIn("ane", nombres)
        self.assertIn("indeed", nombres)
        self.assertIn("linkedin", nombres)
        ane = self._sitio("ANE")
        self.assertTrue(ane.obligatorio)
        self.assertFalse(ane.tiene_credencial)

    def test_una_credencial_con_password_aparece_con_credencial(self):
        CuentasStore().guardar("ANE", usuario="giova", password="secreta")
        ane = self._sitio("ANE")
        self.assertTrue(ane.tiene_credencial)
        self.assertEqual(ane.acceso, "password")
        self.assertEqual(ane.usuario, "giova")

    def test_indicador_con_la_password_en_el_keyring(self):
        """Regresión: con la clave en el keyring el indicador decía 'no'."""
        CuentasStore().guardar("ANE", usuario="giova", password="secreta")
        # El JSON NO tiene la contraseña (solo metadatos).
        import json

        datos = json.loads((Path(self.temp_dir.name) / "credenciales.json")
                           .read_text(encoding="utf-8"))
        self.assertEqual(datos["ane"]["password"], "")
        self.assertEqual(datos["ane"]["password_almacen"], "keyring")
        # Y aun así la cuenta aparece con credencial.
        self.assertTrue(self._sitio("ANE").tiene_credencial)
        self.assertEqual(self._sitio("ANE").almacen,
                         "Administrador de Credenciales")

    def test_sso_google_no_necesita_password(self):
        CuentasStore().guardar("Indeed", usuario="correo@gmail.com", sso="google")
        indeed = self._sitio("Indeed")
        self.assertTrue(indeed.tiene_credencial)
        self.assertEqual(indeed.acceso, "vía Google")

    def test_el_usuario_none_no_revienta(self):
        """La UI clásica pasaba `usuario=... or None` y reventaba."""
        reg = credenciales.upsert_credencial("PruebaX", usuario=None,
                                             password="x")
        self.assertEqual(reg["usuario"], "")
        reg = credenciales.upsert_credencial("PruebaX", usuario="  ",
                                             password="")
        self.assertEqual(reg["usuario"], "")

    def test_borrar_credencial_limpia_el_keyring(self):
        CuentasStore().guardar("ANE", usuario="giova", password="secreta")
        self.assertTrue(CuentasStore().borrar("ANE"))
        self.assertEqual(self.almacen.claves, {})
        self.assertFalse(self._sitio("ANE").tiene_credencial)

    def test_agregar_y_quitar_un_sitio(self):
        store = CuentasStore()
        store.agregar("Empresa Nueva", url="https://ejemplo.test/login")
        self.assertIsNotNone(self._sitio("Empresa Nueva"))
        store.quitar("Empresa Nueva")
        with self.assertRaises(StopIteration):
            self._sitio("Empresa Nueva")

    def test_el_resumen_cuadra(self):
        store = CuentasStore()
        store.guardar("ANE", usuario="giova", password="secreta")
        resumen = store.resumen()
        self.assertEqual(resumen["total"], len(store.sitios()))
        self.assertEqual(resumen["con_credencial"], 1)
        self.assertGreaterEqual(resumen["obligatorios"], 1)

    def test_guardar_sin_password_conserva_la_anterior(self):
        store = CuentasStore()
        store.guardar("ANE", usuario="giova", password="secreta")
        store.guardar("ANE", usuario="giova2", password="")
        self.assertEqual(self.almacen.leer("ANE"), "secreta")
        self.assertEqual(self._sitio("ANE").usuario, "giova2")


if __name__ == "__main__":
    unittest.main()
