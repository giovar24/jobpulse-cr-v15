# -*- coding: utf-8 -*-
"""Tests del barrido de scraping (dominio, SIN Tk).

`scraper.ejecutar_barrido` es lo que permite lanzar un barrido desde la UI:
se prueba con un fetcher FALSO (nada de red) y una BD temporal.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import scraper
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository


class FetcherFalso:
    """Fetcher de mentira: devuelve ofertas fijas y registra lo que le pidieron."""

    def __init__(self, ofertas=None, error=None):
        self.ofertas = list(ofertas or [])
        self.error = error
        self.llamadas: list[dict] = []

    def fetch(self, site, **kwargs):
        self.llamadas.append({"site": dict(site), **kwargs})
        if self.error is not None:
            raise self.error
        return list(self.ofertas)


def _oferta(source_job_id: str, titulo: str = "Puesto de prueba") -> dict:
    return {
        "source_job_id": source_job_id,
        "source_url": f"https://ejemplo.test/{source_job_id}",
        "job": {"title": titulo, "company": "Empresa Test", "country": "CR"},
        "raw_payload": {},
    }


class TestEjecutarBarrido(unittest.TestCase):
    """El barrido ingiere, respeta lo pausado y no se cae por un error."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ruta_db = Path(self.temp_dir.name) / "barrido.db"
        self.database = Database(self.ruta_db)
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_platform("greenhouse", "Greenhouse", "api")
        self.repository.register_site(
            "intel-cr", "workday", "Intel Careers CR",
            "https://intel.example.test", company_name="Intel", country="CR",
            run_groups=("directos",), site_config={"pages": 5},
        )
        self.repository.register_site(
            "acme-cr", "greenhouse", "Acme CR",
            "https://acme.example.test", company_name="Acme", country="CR",
            run_groups=("cr-gov",),
        )
        self.repository.set_site_enabled("acme-cr", False)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _barrer(self, ids, fetcher=None, **kwargs):
        fetcher = fetcher or FetcherFalso([_oferta("REQ-1")])
        with unittest.mock.patch.object(scraper, "instanciar_fetcher",
                                        return_value=fetcher):
            return scraper.ejecutar_barrido(
                ids, database_path=self.ruta_db, **kwargs), fetcher

    def test_ingerta_las_ofertas_y_cuenta_el_resumen(self):
        resumen, fetcher = self._barrer(["intel-cr"])
        self.assertEqual(len(resumen.resultados), 1)
        resultado = resumen.resultados[0]
        self.assertEqual(resultado.estado, scraper.ESTADO_OK)
        self.assertEqual(resultado.jobs_found, 1)
        self.assertEqual(resultado.jobs_new, 1)
        self.assertEqual(resumen.jobs_new, 1)
        self.assertEqual(resumen.errores, 0)
        # La oferta quedó en la BD.
        self.assertIsNotNone(self.repository.get_job("intel-cr:REQ-1"))

    def test_los_sitios_pausados_no_entran(self):
        resumen, fetcher = self._barrer(["acme-cr"])
        self.assertEqual(resumen.resultados[0].estado, scraper.ESTADO_PAUSADO)
        self.assertEqual(fetcher.llamadas, [])

    def test_un_error_no_tumba_la_corrida(self):
        resumen, _ = self._barrer(["intel-cr"],
                                  fetcher=FetcherFalso(error=RuntimeError("boom")))
        self.assertEqual(resumen.resultados[0].estado, scraper.ESTADO_ERROR)
        self.assertIn("boom", resumen.resultados[0].mensaje)
        self.assertEqual(resumen.errores, 1)

    def test_usa_las_paginas_del_site_config(self):
        _resumen, fetcher = self._barrer(["intel-cr"])
        self.assertEqual(fetcher.llamadas[0]["pages"], 5)

    def test_pasa_las_ofertas_descartadas_a_mano(self):
        """Lo que el usuario descartó no se vuelve a ofrecer."""
        _resumen, _fetcher = self._barrer(["intel-cr"])
        self.repository.set_user_job_state("intel-cr:REQ-1", "reviewed",
                                           skip_automatic=True)
        _resumen, fetcher = self._barrer(["intel-cr"])
        omitidos = fetcher.llamadas[0]["skip_source_job_ids"]
        self.assertIn("REQ-1", omitidos)

    def test_sitio_inexistente_y_plataforma_sin_fetcher(self):
        resumen, _ = self._barrer(["no-existe"])
        self.assertEqual(resumen.resultados[0].estado, scraper.ESTADO_NO_EXISTE)

    def test_cancela_despues_del_sitio_en_curso(self):
        """La cancelación corta DESPUÉS del sitio en curso (no a medias)."""
        llamadas = {"n": 0}

        def should_stop() -> bool:
            llamadas["n"] += 1
            return llamadas["n"] > 1  # el primer sitio sí se barre

        resumen, _ = self._barrer(["intel-cr", "intel-cr"], should_stop=should_stop)
        self.assertTrue(resumen.cancelado)
        self.assertEqual(len(resumen.resultados), 1)

    def test_el_progreso_avisa_de_cada_sitio(self):
        eventos: list[scraper.Progreso] = []
        self._barrer(["intel-cr"], on_progress=eventos.append)
        etapas = [e.etapa for e in eventos]
        self.assertIn("inicio", etapas)
        self.assertIn("fin", etapas)


class TestHelpers(unittest.TestCase):
    """Ayudantes puros del módulo de barrido."""

    def test_instanciar_fetcher_desconocido_devuelve_none(self):
        self.assertIsNone(scraper.instanciar_fetcher("plataforma-fantasma"))

    def test_plataforma_de_sitio_usa_el_adapter_como_respaldo(self):
        sitio = {"platform_id": "", "site_config": {"adapter": "workday"}}
        self.assertEqual(scraper.plataforma_de_sitio(sitio), "workday")
        sitio = {"platform_id": "greenhouse", "site_config": {}}
        self.assertEqual(scraper.plataforma_de_sitio(sitio), "greenhouse")

    def test_todos_los_fetchers_aceptan_skip_source_job_ids(self):
        """El dispatcher pasa los descartados: TODOS deben aceptarlos."""
        import importlib
        import inspect

        for platform_id in scraper.FETCHERS:
            with self.subTest(plataforma=platform_id):
                modulo, _, clase = scraper.FETCHERS[platform_id].partition(":")
                mod = importlib.import_module(modulo)
                firma = inspect.signature(getattr(mod, clase).fetch)
                self.assertIn("skip_source_job_ids", firma.parameters)


if __name__ == "__main__":
    unittest.main()
