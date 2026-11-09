# -*- coding: utf-8 -*-
"""Tests del módulo de cachés (`jobpulse_v15.caches`).

Reglas que se comprueban:
- La caché de la IA solo cuenta/borrra archivos `[0-9a-f]{32}.json`: los
  archivos ajenos del usuario se respetan.
- La caché de embeddings son los 4 archivos conocidos.
- Los tamaños y conteos cuadran con lo que hay en disco.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import caches, ia_api, search_engine

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


class TestCacheEmbeddings(unittest.TestCase):
    """La caché de embeddings (4 archivos)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.embeddings = base / "embeddings_cache.npy"
        self.meta = base / "embeddings_meta.json"
        self.titulos = base / "embeddings_titulos.npy"
        self.tit_meta = base / "embeddings_titulos_meta.json"
        parches = [
            unittest.mock.patch.object(search_engine, "EMB_CACHE_FILE",
                                       self.embeddings),
            unittest.mock.patch.object(search_engine, "EMB_META_FILE", self.meta),
            unittest.mock.patch.object(search_engine, "EMB_TIT_CACHE_FILE",
                                       self.titulos),
            unittest.mock.patch.object(search_engine, "EMB_TIT_META_FILE",
                                       self.tit_meta),
        ]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_muestra_los_cuatro_archivos(self):
        estado = caches.estado_embeddings()
        self.assertEqual(len(estado.archivos), 4)
        self.assertEqual(estado.archivos_totales, 0)
        self.assertIn("Vacía", estado.texto_resumen)

    def test_cuenta_los_que_existen(self):
        self.embeddings.write_bytes(b"x" * 100)
        self.meta.write_text("{}", encoding="utf-8")
        estado = caches.estado_embeddings()
        self.assertEqual(estado.archivos_totales, 2)
        self.assertEqual(estado.bytes_totales, 102)

    def test_limpiar_borra_los_cuatro(self):
        for ruta in (self.embeddings, self.meta, self.titulos, self.tit_meta):
            ruta.write_text("x", encoding="utf-8")
        resultado = caches.limpiar_embeddings()
        self.assertTrue(resultado.ok)
        self.assertEqual(resultado.archivos_borrados, 4)
        for ruta in (self.embeddings, self.meta, self.titulos, self.tit_meta):
            self.assertFalse(ruta.exists())


class TestLimpiezaPorClave(unittest.TestCase):
    """`limpiar(clave)` y `estado_caches()`."""

    def test_clave_desconocida_devuelve_error(self):
        resultado = caches.limpiar("no-existe")
        self.assertFalse(resultado.ok)
        self.assertIn("no-existe", resultado.error)

    def test_estado_caches_devuelve_las_dos(self):
        estados = caches.estado_caches()
        self.assertIn(caches.CLAVE_IA, estados)
        self.assertIn(caches.CLAVE_EMBEDDINGS, estados)

    def test_tamano_legible(self):
        self.assertEqual(caches._tamano_legible(512), "512 B")
        self.assertEqual(caches._tamano_legible(2048), "2.0 KB")
        self.assertEqual(caches._tamano_legible(5 * 1024 * 1024), "5.0 MB")


class TestDisponibilidadDeEmbeddings(unittest.TestCase):
    """Ola 5 · 5.2: ¿se puede usar el componente semantico SIN trabajo extra?

    Un comando de solo lectura (la CLI de viabilidad) solo activa el
    componente semantico si el modelo ya esta en la cache local de Hugging
    Face y la cache de embeddings cubre el corpus (asi no descarga ~500 MB
    ni re-vectoriza nada).
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.embeddings = base / "embeddings_cache.npy"
        self.meta = base / "embeddings_meta.json"
        self.titulos = base / "embeddings_titulos.npy"
        self.tit_meta = base / "embeddings_titulos_meta.json"
        parches = [
            unittest.mock.patch.object(search_engine, "EMB_CACHE_FILE",
                                       self.embeddings),
            unittest.mock.patch.object(search_engine, "EMB_META_FILE", self.meta),
            unittest.mock.patch.object(search_engine, "EMB_TIT_CACHE_FILE",
                                       self.titulos),
            unittest.mock.patch.object(search_engine, "EMB_TIT_META_FILE",
                                       self.tit_meta),
        ]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def _escribir_meta(self, items, version=None):
        contenido = {
            "model": "modelo-de-prueba",
            "version": search_engine.CACHE_VERSION if version is None else version,
            "dim": 768,
            "items": items,
        }
        self.meta.write_text(json.dumps(contenido), encoding="utf-8")
        self.tit_meta.write_text(json.dumps(contenido), encoding="utf-8")
        # Los .npy tambien tienen que existir (la cache son los 4 archivos).
        self.embeddings.write_bytes(b"x")
        self.titulos.write_bytes(b"x")

    def test_sin_cache_la_cobertura_es_falsa(self):
        self.assertFalse(search_engine.embeddings_cache_cubren(["job-1"]))

    def test_la_cache_cubre_solo_los_avisos_que_conoce(self):
        self._escribir_meta({"job-1": {"hash": "h", "idx": 0}})
        self.assertTrue(search_engine.embeddings_cache_cubren(["job-1"]))
        self.assertFalse(
            search_engine.embeddings_cache_cubren(["job-1", "job-2"])
        )

    def test_una_cache_de_otra_version_no_cubre(self):
        self._escribir_meta({"job-1": {"hash": "h", "idx": 0}}, version=999)
        self.assertFalse(search_engine.embeddings_cache_cubren(["job-1"]))

    def test_sin_ids_no_cubre(self):
        self._escribir_meta({})
        self.assertFalse(search_engine.embeddings_cache_cubren([]))

    def test_el_modelo_se_busca_en_la_cache_local_de_huggingface(self):
        hub = Path(self.temp_dir.name) / "hub"
        carpeta = (
            hub
            / ("models--" + search_engine.MODELO_PRIMARY.replace("/", "--"))
        )
        carpeta.mkdir(parents=True)
        with unittest.mock.patch.dict(
            os.environ, {"HF_HUB_CACHE": str(hub)}, clear=False
        ):
            self.assertTrue(search_engine.modelo_embeddings_disponible())
        # Sin ningun modelo en la cache: no se puede usar (ni descargar).
        with unittest.mock.patch.dict(
            os.environ, {"HF_HUB_CACHE": str(hub / "vacio")}, clear=False
        ):
            self.assertFalse(search_engine.modelo_embeddings_disponible())


if __name__ == "__main__":
    unittest.main()
