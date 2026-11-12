# -*- coding: utf-8 -*-
"""Tests del módulo de cachés (`jobpulse_v15.caches`).

Reglas que se comprueban:
- La caché de la IA solo cuenta/borra archivos `[0-9a-f]{32}.json`: los
  archivos ajenos del usuario se respetan.
- Los tamaños y conteos cuadran con lo que hay en disco.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import caches, ia_api

CLAVE_VALIDA = "a" * 32
CLAVE_VALIDA_2 = "0123456789abcdef0123456789abcdef"


class TestCacheIA(unittest.TestCase):
    """La caché de la IA (una respuesta por hash)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.carpeta = Path(self.temp_dir.name) / "ia_cache"
        self.carpeta.mkdir(parents=True)
        parche = unittest.mock.patch.object(ia_api, "CACHE_DIR", self.carpeta)
        parche.start()
        self.addCleanup(parche.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_cuenta_solo_los_archivos_del_sistema(self):
        (self.carpeta / f"{CLAVE_VALIDA}.json").write_text("{}", encoding="utf-8")
        (self.carpeta / f"{CLAVE_VALIDA_2}.json").write_text("{}", encoding="utf-8")
        # Archivo ajeno (NO es del sistema): no se cuenta ni se borra.
        (self.carpeta / "notas.txt").write_text("hola", encoding="utf-8")
        (self.carpeta / "subcarpeta").mkdir()
        estado = caches.estado_ia()
        self.assertEqual(estado.archivos_totales, 2)
        self.assertEqual(estado.bytes_totales, 4)  # dos "{}"
        self.assertIn("2 respuestas", estado.texto_resumen)

    def test_limpiar_borra_solo_los_archivos_del_sistema(self):
        (self.carpeta / f"{CLAVE_VALIDA}.json").write_text("{}", encoding="utf-8")
        ajeno = self.carpeta / "notas.txt"
        ajeno.write_text("hola", encoding="utf-8")
        resultado = caches.limpiar_ia()
        self.assertTrue(resultado.ok)
        self.assertEqual(resultado.archivos_borrados, 1)
        self.assertEqual(resultado.bytes_liberados, 2)
        self.assertFalse((self.carpeta / f"{CLAVE_VALIDA}.json").exists())
        # El archivo ajeno sigue ahí.
        self.assertTrue(ajeno.exists())

    def test_limpiar_una_carpeta_vacia_no_falla(self):
        resultado = caches.limpiar_ia()
        self.assertTrue(resultado.ok)
        self.assertEqual(resultado.archivos_borrados, 0)

    def test_limpiar_una_carpeta_inexistente_no_falla(self):
        import shutil

        shutil.rmtree(self.carpeta)
        resultado = caches.limpiar_ia()
        self.assertTrue(resultado.ok)
        self.assertEqual(resultado.archivos_borrados, 0)

    def test_los_huerfanos_se_listan_pero_no_se_borran(self):
        (self.carpeta / "notas.txt").write_text("hola", encoding="utf-8")
        (self.carpeta / f"{CLAVE_VALIDA}.json").write_text("{}", encoding="utf-8")
        huerfanos = list(caches.archivos_huerfanos_ia(self.carpeta))
        self.assertEqual([p.name for p in huerfanos], ["notas.txt"])

    def test_la_ubicacion_es_la_misma_que_usa_la_ia(self):
        """La UI muestra y borra EXACTAMENTE la carpeta que usa `ia_api`."""
        self.assertEqual(caches._ruta_ia(), Path(ia_api.CACHE_DIR))


class TestLimpiezaPorClave(unittest.TestCase):
    """`limpiar(clave)` y `estado_caches()`."""

    def test_clave_desconocida_devuelve_error(self):
        resultado = caches.limpiar("no-existe")
        self.assertFalse(resultado.ok)
        self.assertIn("no-existe", resultado.error)

    def test_estado_caches_devuelve_la_de_ia(self):
        estados = caches.estado_caches()
        self.assertIn(caches.CLAVE_IA, estados)
        self.assertEqual(list(estados), [caches.CLAVE_IA])

    def test_tamano_legible(self):
        self.assertEqual(caches._tamano_legible(512), "512 B")
        self.assertEqual(caches._tamano_legible(2048), "2.0 KB")
        self.assertEqual(caches._tamano_legible(5 * 1024 * 1024), "5.0 MB")


if __name__ == "__main__":
    unittest.main()
