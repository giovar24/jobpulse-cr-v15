# -*- coding: utf-8 -*-
"""LINKEDIN: los selectores del listado (O13 · Ola 3.1).

Contexto (verificado 2026-11-05 en vivo): el listado publico
``https://www.linkedin.com/jobs/search/?keywords=..&location=..`` responde
200 por HTTP simple y trae:

- las tarjetas en ``div.base-card`` con
  ``data-entity-urn="urn:li:jobPosting:<id>"``,
  ``h3.base-search-card__title``, ``h4.base-search-card__subtitle``,
  ``span.job-search-card__location``, ``time.job-search-card__listdate``
  y ``a.base-card__full-link`` (enlace ``/jobs/view/<slug>-<id>``);
- ademas un ``script[type="application/ld+json"]`` de tipo ``ItemList``.

Antes el scraper buscaba ``[data-occludable-job-id]``, ``li[data-job-id]``,
``div[data-job-id]`` y ``.job-card-container``: NINGUNO existe en el HTML
actual, y el barrido daba 0 avisos.

Estos tests usan el HTML REAL (recortado) del sitio: verifican que el
parseo saca los avisos correctos y que los caminos de respaldo funcionan.
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.linkedin import (  # noqa: E402
    LISTADO_URL,
    LinkedInFetcher,
    _id_de_url,
    _id_de_urn,
    _json_ld,
    _listado_desde_html,
    _tarjetas_html,
)
from jobpulse_v15.requiere_login import RequiereLoginError  # noqa: E402

# --- HTML real del listado (recortado a dos tarjetas) ----------------------
HTML_LISTADO = """
<html><head>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"ItemList","itemListElement":[
{"@type":"ListItem","position":1,"url":"https://cr.linkedin.com/jobs/view/it-support-technician-ii-at-korn-ferry-4474290121","name":"IT Support Technician II","disambiguatingDescription":"Korn Ferry","description":"Heredia, Costa Rica"},
{"@type":"ListItem","position":2,"url":"https://cr.linkedin.com/jobs/view/analista-de-soporte-de-ti-trabajo-remoto-ref%23258081-at-bairesdev-4192198814","name":"Analista de Soporte de TI - Trabajo Remoto | REF#258081","disambiguatingDescription":"BairesDev LLC","description":"San Jos&#xE9;"}]}</script>
</head><body>
<ul class="jobs-search__results-list">
  <li>
    <div class="base-card relative w-full base-search-card base-search-card--link job-search-card"
         data-entity-urn="urn:li:jobPosting:4474290121" data-column="1" data-row="1">
      <a class="base-card__full-link" href="https://cr.linkedin.com/jobs/view/it-support-technician-ii-at-korn-ferry-4474290121?position=1&pageNum=0">
        <span class="sr-only">IT Support Technician II</span>
      </a>
      <div class="base-search-card__info">
        <h3 class="base-search-card__title">IT Support Technician II</h3>
        <h4 class="base-search-card__subtitle">
          <a class="hidden-nested-link" href="https://www.linkedin.com/company/kornferry">Korn Ferry</a>
        </h4>
        <div class="base-search-card__metadata">
          <span class="job-search-card__location">Heredia, Costa Rica</span>
          <time class="job-search-card__listdate" datetime="2026-11-03">2 days ago</time>
        </div>
      </div>
    </div>
  </li>
  <li>
    <div class="base-card relative w-full base-search-card job-search-card"
         data-entity-urn="urn:li:jobPosting:4192198814" data-column="1" data-row="2">
      <a class="base-card__full-link" href="https://cr.linkedin.com/jobs/view/analista-de-soporte-de-ti-trabajo-remoto-ref%23258081-at-bairesdev-4192198814?position=2">
        <span class="sr-only">Analista de Soporte de TI - Trabajo Remoto | REF#258081</span>
      </a>
      <div class="base-search-card__info">
        <h3 class="base-search-card__title">Analista de Soporte de TI - Trabajo Remoto | REF#258081</h3>
        <h4 class="base-search-card__subtitle">
          <a class="hidden-nested-link" href="https://www.linkedin.com/company/bairesdev">BairesDev LLC</a>
        </h4>
        <div class="base-search-card__metadata">
          <span class="job-search-card__location">San Jos&#xE9;, Costa Rica</span>
          <time class="job-search-card__listdate" datetime="2025-03-28">1 year ago</time>
        </div>
      </div>
    </div>
  </li>
</ul>
</body></html>
"""


class TestParseoDelListado(unittest.TestCase):
    """El HTML real tiene que dar los avisos completos."""

    def test_una_tarjeta_base_card_da_titulo_empresa_ubicacion_y_fecha(self):
        tarjetas = _tarjetas_html(HTML_LISTADO)
        self.assertEqual(len(tarjetas), 2)
        primera = tarjetas[0]
        self.assertEqual(primera["job_id"], "4474290121")
        self.assertEqual(primera["titulo"], "IT Support Technician II")
        self.assertEqual(primera["empresa"], "Korn Ferry")
        self.assertEqual(primera["ubicacion_oferta"], "Heredia, Costa Rica")
        self.assertEqual(primera["fecha_publicacion"], "2026-11-03")
        self.assertTrue(primera["link"].endswith("-4474290121"))
        self.assertNotIn("?", primera["link"])

    def test_el_id_sale_del_urn_y_no_de_la_url(self):
        tarjetas = _tarjetas_html(HTML_LISTADO)
        self.assertEqual(tarjetas[1]["job_id"], "4192198814")
        self.assertEqual(tarjetas[1]["titulo"].startswith("Analista de Soporte"), True)

    def test_el_json_ld_saca_los_mismos_avisos(self):
        items = _json_ld(HTML_LISTADO)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["job_id"], "4474290121")
        self.assertEqual(items[0]["titulo"], "IT Support Technician II")
        self.assertEqual(items[0]["empresa"], "Korn Ferry")
        self.assertEqual(items[0]["ubicacion_oferta"], "Heredia, Costa Rica")

    def test_el_dom_manda_y_el_json_ld_es_el_respaldo(self):
        self.assertEqual(len(_listado_desde_html(HTML_LISTADO)), 2)
        # Sin tarjetas: el JSON-LD rescata el listado.
        solo_json = """
        <html><head><script type="application/ld+json">
        {"@type":"ItemList","itemListElement":[
        {"@type":"ListItem","url":"https://www.linkedin.com/jobs/view/x-4474290121",
         "name":"Puesto","disambiguatingDescription":"Empresa",
         "description":"Costa Rica"}]}
        </script></head><body></body></html>
        """
        self.assertEqual(len(_listado_desde_html(solo_json)), 1)
        self.assertEqual(_listado_desde_html(solo_json)[0]["empresa"], "Empresa")

    def test_un_html_sin_avisos_no_inventa_nada(self):
        self.assertEqual(_listado_desde_html("<html><body></body></html>"), [])


class TestIds(unittest.TestCase):
    def test_el_id_es_el_ultimo_grupo_de_digitos(self):
        # El slug trae numeros ("ref%23258081"): el ID es el final.
        self.assertEqual(
            _id_de_url(
                "https://cr.linkedin.com/jobs/view/analista-de-soporte-de-ti-"
                "trabajo-remoto-ref%23258081-at-bairesdev-4192198814"
            ),
            "4192198814",
        )

    def test_el_id_de_una_url_sin_slug(self):
        self.assertEqual(
            _id_de_url("https://www.linkedin.com/jobs/view/4474290121"),
            "4474290121",
        )

    def test_el_id_del_urn(self):
        self.assertEqual(_id_de_urn("urn:li:jobPosting:4474290121"), "4474290121")
        self.assertEqual(_id_de_urn(""), "")

    def test_una_url_sin_id_no_inventa_numeros(self):
        self.assertEqual(_id_de_url("https://www.linkedin.com/jobs/view/x"), "")


class TestPaginacion(unittest.TestCase):
    def test_la_pagina_2_empieza_en_el_siguiente_tramo(self):
        url = LinkedInFetcher._url_listado("Soporte Técnico", "Costa Rica", 2)
        self.assertTrue(url.startswith(LISTADO_URL))
        self.assertIn("keywords=Soporte+T%C3%A9cnico", url)
        self.assertIn("location=Costa+Rica", url)
        self.assertIn("start=25", url)

    def test_la_pagina_1_no_lleva_start(self):
        url = LinkedInFetcher._url_listado("Soporte Técnico", "Costa Rica", 1)
        self.assertNotIn("start=", url)


class TestFetch(unittest.TestCase):
    """El fetch une listado + detalle y respeta lo descartado a mano."""

    def setUp(self):
        self.fetcher = LinkedInFetcher(request_delay=0)
        self.site = {
            "site_id": "linkedin-cr",
            "country": "Costa Rica",
            "site_config": {"search_text": "Soporte Técnico"},
        }

    def _patch(self, http_items, navegador_items=(), muro=False, cookies=None):
        return (
            patch.object(self.fetcher, "_listar_http", return_value=list(http_items)),
            patch.object(
                self.fetcher, "_listar_navegador",
                return_value=(list(navegador_items), dict(cookies or {}), muro),
            ),
            patch.object(
                self.fetcher, "_fetch_details_guest",
                return_value=({"description": "Descripcion del aviso."}, False),
            ),
        )

    def test_el_fetch_devuelve_las_ofertas_del_listado(self):
        tarjetas = _listado_desde_html(HTML_LISTADO)
        http_mock, nav_mock, det_mock = self._patch(tarjetas)
        with http_mock, nav_mock, det_mock:
            ofertas = asyncio.run(self.fetcher.fetch(self.site, pages=1))
        self.assertEqual(len(ofertas), 2)
        self.assertEqual(ofertas[0]["source_job_id"], "4474290121")
        self.assertEqual(ofertas[0]["job"]["title"], "IT Support Technician II")
        self.assertEqual(ofertas[0]["job"]["company"], "Korn Ferry")
        self.assertEqual(ofertas[0]["job"]["date_published"], "2026-11-03")
        self.assertEqual(ofertas[0]["job"]["description_raw"], "Descripcion del aviso.")

    def test_lo_que_el_usuario_descarto_no_vuelve(self):
        tarjetas = _listado_desde_html(HTML_LISTADO)
        http_mock, nav_mock, det_mock = self._patch(tarjetas)
        with http_mock, nav_mock, det_mock:
            ofertas = asyncio.run(
                self.fetcher.fetch(
                    self.site, pages=1, skip_source_job_ids={"4474290121"}
                )
            )
        self.assertEqual(len(ofertas), 1)
        self.assertEqual(ofertas[0]["source_job_id"], "4192198814")

    def test_el_navegador_suma_lo_que_el_http_no_trajo(self):
        tarjetas = _listado_desde_html(HTML_LISTADO)
        extra = {
            "job_id": "9999999999",
            "titulo": "Puesto del navegador",
            "empresa": "Empresa",
            "ubicacion_oferta": "Costa Rica",
            "fecha_publicacion": "2026-11-01",
            "link": "https://www.linkedin.com/jobs/view/puesto-9999999999",
        }
        http_mock, nav_mock, det_mock = self._patch(tarjetas, [extra])
        with http_mock, nav_mock, det_mock:
            ofertas = asyncio.run(self.fetcher.fetch(self.site, pages=1))
        self.assertEqual(len(ofertas), 3)
        ids = {o["source_job_id"] for o in ofertas}
        self.assertIn("9999999999", ids)

    def test_sin_avisos_no_hay_ofertas(self):
        http_mock, nav_mock, det_mock = self._patch([])
        with http_mock, nav_mock, det_mock:
            ofertas = asyncio.run(self.fetcher.fetch(self.site, pages=1))
        self.assertEqual(len(ofertas), 0)

    def test_un_muro_de_login_sin_avisos_es_el_estado_requiere_login(self):
        http_mock, nav_mock, det_mock = self._patch([], muro=True)
        with http_mock, nav_mock, det_mock:
            with self.assertRaises(RequiereLoginError):
                asyncio.run(self.fetcher.fetch(self.site, pages=1))


if __name__ == "__main__":
    unittest.main()
