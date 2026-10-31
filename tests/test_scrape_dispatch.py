# -*- coding: utf-8 -*-
"""Tests del dispatcher de scrape: cada fetcher se llama con SU firma.

Regresion de dos bugs reales:
- ``run_full_flow.py`` hacia ``await`` a los fetchers sync y NO hacia los
  async (cinde/procomer reventaban con "asyncio.run() cannot be called from
  a running event loop").
- la UI pasaba ``pages=`` a greenhouse/ashby/lever/recruitee/
  successfactors/harvie, que no aceptan ese parametro (TypeError).
"""
import unittest

from jobpulse_v15.scrape_dispatch import construir_llamada, necesita_navegador


class FetcherFalso:
    """Captura como se le llamo."""

    def __init__(self):
        self.llamadas = []

    def fetch(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        return ["oferta"]

    async def afetch(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        return ["oferta"]


class TestConstruirLlamada(unittest.TestCase):
    def setUp(self):
        self.site = {"site_id": "x", "base_url": "https://x.test"}
        self.fetcher = FetcherFalso()

    def _llama(self, platform, **kwargs):
        llamada = construir_llamada(
            platform, self.fetcher, self.site, pages=3, port=9222, dias=30
        )
        return llamada()

    def test_tableros_sin_pages(self):
        # No aceptan `pages`: pasarlo es TypeError.
        for platform in ("greenhouse", "ashby", "lever", "recruitee",
                         "successfactors", "harvie"):
            with self.subTest(platform=platform):
                self.fetcher.llamadas.clear()
                self._llama(platform)
                args, kwargs = self.fetcher.llamadas[0]
                self.assertNotIn("pages", kwargs)
                self.assertEqual(args, (self.site,))

    def test_tableros_con_pages(self):
        for platform in ("workday", "workable", "cinde", "procomer"):
            with self.subTest(platform=platform):
                self.fetcher.llamadas.clear()
                self._llama(platform)
                args, kwargs = self.fetcher.llamadas[0]
                self.assertEqual(kwargs["pages"], 3)
                self.assertNotIn("port", kwargs)

    def test_ane_recibe_paginas_puerto_y_dias(self):
        self._llama("ane")
        args, kwargs = self.fetcher.llamadas[0]
        self.assertEqual(kwargs["pages"], 3)
        self.assertEqual(kwargs["port"], 9222)
        self.assertEqual(kwargs["dias"], 30)

    def test_indeed_y_linkedin_reciben_puerto(self):
        for platform in ("indeed", "linkedin"):
            with self.subTest(platform=platform):
                self.fetcher.llamadas.clear()
                self._llama(platform)
                args, kwargs = self.fetcher.llamadas[0]
                self.assertEqual(kwargs["pages"], 3)
                self.assertEqual(kwargs["port"], 9222)

    def test_elempleo_recibe_puerto_sin_pages(self):
        self._llama("elempleo")
        args, kwargs = self.fetcher.llamadas[0]
        self.assertEqual(kwargs["port"], 9222)
        self.assertNotIn("pages", kwargs)

    def test_la_llamada_no_toma_argumentos(self):
        llamada = construir_llamada("workday", self.fetcher, self.site)
        self.assertEqual(llamada(), ["oferta"])

    def test_plataformas_de_navegador(self):
        self.assertEqual(
            {p for p in ("ane", "indeed", "linkedin", "elempleo", "workday",
                         "greenhouse", "harvie", "cinde")
             if necesita_navegador(p)},
            {"ane", "indeed", "linkedin", "elempleo"},
        )


if __name__ == "__main__":
    unittest.main()
