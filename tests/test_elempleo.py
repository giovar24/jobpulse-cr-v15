# -*- coding: utf-8 -*-
"""ELEMPLEO: el muro de login, la empresa y el filtro de pais (O13 · Ola 3.2).

Contexto (verificado 2026-11-05 en vivo):

1. `.ee_list-item` NO son las ofertas: es el MENU LATERAL ("Todos los
   anuncios de empleo", filtros...). Las ofertas siguen en `.result-item`
   con `.js-area-bind.area-bind` dentro. El dato de `datalayertag` ya no
   viene: la empresa esta en `.js-offer-company`.
2. El encabezado trae SIEMPRE el boton "Inicia sesion" (el boton de
   entrar). La deteccion de muro de login lo tomaba por un muro y cortaba
   el barrido en la pagina 1: **0 avisos siempre**.
3. El filtro de pais miraba solo titulo + empresa + UBICACION, y la
   ubicacion es el CANTON ("San Jose"): "Costa Rica" no aparecia, asi que
   se descartaban todas las ofertas.
"""
import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.elempleo import ElempleoFetcher  # noqa: E402


class PaginaFalsa:
    """Playwright minimo: lo que usa `_es_login_wall`."""

    def __init__(self, *, url="https://www.elempleo.com/cr/ofertas-empleo/",
                 selectores=(), texto=""):
        self.url = url
        self._selectores = set(selectores)
        self._texto = texto

    async def query_selector(self, selector):
        # Playwright acepta una lista de selectores separada por comas.
        for parte in selector.split(","):
            if parte.strip() in self._selectores:
                return object()
        return None

    async def inner_text(self, _selector):
        return self._texto


class TestMuroDeLogin(unittest.TestCase):
    def setUp(self):
        self.fetcher = ElempleoFetcher()

    def test_el_boton_del_encabezado_NO_es_un_muro(self):
        """El encabezado siempre trae "Inicia sesion": NO es un muro."""
        pagina = PaginaFalsa(
            selectores=(".result-item",),
            texto="Inicia sesion Iniciar sesion Home elempleo VIP",
        )
        self.assertFalse(asyncio.run(self.fetcher._es_login_wall(pagina)))

    def test_el_boton_del_encabezado_sin_avisos_tampoco_es_un_muro(self):
        """Solo un FORMULARIO de acceso es un muro de verdad."""
        pagina = PaginaFalsa(
            selectores=(".result-item",),
            texto="Inicia sesion",
        )
        self.assertFalse(asyncio.run(self.fetcher._es_login_wall(pagina)))

    def test_un_formulario_de_password_es_un_muro(self):
        pagina = PaginaFalsa(
            selectores=('input[type="password"]',),
            texto="Correo electronico Contrasena",
        )
        self.assertTrue(asyncio.run(self.fetcher._es_login_wall(pagina)))

    def test_la_pagina_de_inicio_de_sesion_es_un_muro(self):
        pagina = PaginaFalsa(
            url="https://www.elempleo.com/cr/cross/iniciar-sesion",
            texto="",
        )
        self.assertTrue(asyncio.run(self.fetcher._es_login_wall(pagina)))

    def test_una_pagina_de_resultados_no_es_un_muro(self):
        pagina = PaginaFalsa(
            selectores=(".result-item",),
            texto="Anuncios de empleo 50 avisos encontrados",
        )
        self.assertFalse(asyncio.run(self.fetcher._es_login_wall(pagina)))


class TestFiltroDePais(unittest.TestCase):
    def test_el_pais_del_aviso_hace_pasar_el_filtro(self):
        """La ubicacion es el canton; el pais va aparte."""
        self.assertTrue(
            ElempleoFetcher._pasa_filtro_pais(
                "Tecnico en farmacia", "GFI", "San Jose", "Costa Rica", "Costa Rica"
            )
        )

    def test_un_aviso_de_otro_pais_no_pasa(self):
        self.assertFalse(
            ElempleoFetcher._pasa_filtro_pais(
                "Puesto", "Empresa", "Panama", "Panama", "Costa Rica"
            )
        )

    def test_sin_filtro_pasa_todo(self):
        self.assertTrue(
            ElempleoFetcher._pasa_filtro_pais("P", "E", "L", "C", "")
        )


class TestIdsDeOferta(unittest.TestCase):
    def test_el_id_sale_de_la_url_del_aviso(self):
        self.assertEqual(
            ElempleoFetcher._extract_job_id(
                "https://www.elempleo.com/cr/ofertas-trabajo/tecnico/880262"
            ),
            "880262",
        )

    def test_una_url_sin_id_no_inventa_numeros(self):
        self.assertIsNone(ElempleoFetcher._extract_job_id("https://www.elempleo.com/cr/"))


if __name__ == "__main__":
    unittest.main()
