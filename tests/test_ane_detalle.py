# -*- coding: utf-8 -*-
"""ANE: la ficha de detalle tiene campos que el parser DELEGABA (O13 · Ola 4.1).

Medido en vivo 2026-11-06: la vacante trae, en la caja de "Información
general del empleo":

    Ocupación : Asesor de ventas
    Nivel académico : Secundaria académica incompleta (7º y 8º)
    Experiencia laboral : De 1 a menos de 2 años
    Plazas disponibles: 1
    Correo : reclutamientoventas708@gmail.com
    Ubicaciones del empleo : San José / Escazú / Escazú

y en "Detalles del empleo": Horario, Tipo contratación, Fecha de vencimiento,
Salario, Detalles del salario, Estudio técnico, Detalle del horario,
Funciones principales del empleo y las listas de requisitos/beneficios.

El parser solo leía "Funciones principales", "Salario", "Fecha de
vencimiento" y las listas de requisitos: **"Nivel académico" y "Experiencia
laboral" se perdían** (lo que la empresa PIDE) y con ellos el motor no podía
evaluar la dimensión educativa ni la de experiencia.

Estos tests usan el HTML real (recortado) de la ficha de ANE.
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.ane import AneFetcher  # noqa: E402
from jobpulse_v15.requiere_login import RequiereLoginError  # noqa: E402

HTML_DETALLE = """
<html><body>
<div class="dashboard-content-inner">
  <div class="row">
    <div class="col-xl-6">
      <div class="dashboard-box">
        <div class="content with-padding">
          <p>OPTICAS MUNKEL</p>
          <p><strong>Ocupación</strong> : Asesor de ventas</p>
          <p><strong>Nivel académico</strong> : Secundaria académica incompleta (7º y 8º)</p>
          <p><strong>Experiencia laboral</strong> : De 1 a menos de 2 años</p>
          <p><strong>Plazas disponibles: 1</strong></p>
          <p><strong>Correo</strong> : reclutamientoventas708@gmail.com</p>
          <strong>Ubicaciones del empleo</strong>
          <ul class="list-3"><li>San José / Escazú / Escazú</li></ul>
        </div>
      </div>
    </div>
    <div class="col-xl-6">
      <div class="dashboard-box">
        <div class="content with-padding">
          <h2 class="text-center">Asesor de Ventas</h2>
          <p class="text-center"><small>OPTICAS MUNKEL</small></p>
          <p><strong>Horario</strong> : Tiempo completo (Jornada diurna)</p>
          <p><strong>Tipo contratación</strong> : Permanente</p>
          <p><strong>Fecha de vencimiento de la vacante</strong> : viernes, 04 de diciembre del 2026</p>
          <p><strong>Salario</strong> : ₡406000 - ₡420000</p>
          <p><strong>Detalles del salario</strong> : Salario de pago quincenal</p>
          <p><strong>Estudio técnico</strong> : "No se especifica estudios técnicos"</p>
          <p><strong>Detalle del horario</strong> : Horario 9-6 pm</p>
          <p><strong>Funciones principales del empleo</strong> : Asesorar al paciente en la compra, apertura y cierre de cajas, control de inventarios, depositos bancarios</p>
          <strong>Requisitos adicionales:</strong>
          <ul class="list-3">
            <li>Licencias de conducir: B1</li>
            <li>Experiencia en atención al cliente</li>
          </ul>
          <strong>Beneficios incluidos para el empleo:</strong>
          <ul class="list-3">
            <li>Médico de empresa</li>
            <li>Bonificaciones</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</div>
</body></html>
"""


class TestDetalleDeAne(unittest.TestCase):
    def setUp(self):
        self.fetcher = AneFetcher()
        self.card = {"titulo": "Asesor de Ventas", "empresa": "OPTICAS MUNKEL",
                     "ubicacion": ""}
        self.detalle = self.fetcher._parse_detalle(HTML_DETALLE, self.card)

    def test_lee_el_nivel_academico(self):
        """Lo que la empresa PIDE: sin esto no hay dimension educativa."""
        self.assertIn("Nivel académico: Secundaria académica incompleta (7º y 8º)",
                      self.detalle["requisitos"])

    def test_lee_la_experiencia_laboral(self):
        self.assertIn("Experiencia laboral: De 1 a menos de 2 años",
                      self.detalle["requisitos"])

    def test_el_estudio_tecnico_negado_NO_copia(self):
        """"No se especifica estudios técnicos" NO es un requisito."""
        self.assertNotIn("Estudio técnico", self.detalle["requisitos"])

    def test_los_beneficios_no_son_requisitos(self):
        self.assertNotIn("Médico de empresa", self.detalle["requisitos"])
        self.assertNotIn("Bonificaciones", self.detalle["requisitos"])

    def test_los_requisitos_de_la_lista_siguen_estando(self):
        self.assertIn("Licencias de conducir: B1", self.detalle["requisitos"])

    def test_la_descripcion_trae_el_contexto(self):
        desc = self.detalle["descripcion"]
        self.assertIn("Asesorar al paciente", desc)
        self.assertIn("Ocupación: Asesor de ventas", desc)
        self.assertIn("Horario: Tiempo completo", desc)
        self.assertIn("Tipo de contratación: Permanente", desc)

    def test_el_correo_del_empleador_NO_se_guarda(self):
        """Dato personal de un tercero: no va al corpus."""
        todo = " ".join(self.detalle.values())
        self.assertNotIn("reclutamientoventas708@gmail.com", todo)

    def test_los_datos_generales_no_se_pierden(self):
        self.assertEqual(self.detalle["ubicacion"], "San José / Escazú / Escazú")
        self.assertEqual(self.detalle["salario"], "₡406000 - ₡420000")
        self.assertIn("2026-12-04", self.detalle["vence"])

    def test_un_muro_de_login_no_devuelve_campos(self):
        self.assertEqual(self.fetcher._parse_detalle("<html></html>", self.card), {})

    def test_la_oferta_usa_el_mismo_molde_que_el_barrido(self):
        """UNA sola implementacion del guardado (barrido y re-barrido)."""
        oferta = AneFetcher._oferta(
            "121858", "https://www.ane.cr/Puesto/Detalles?Puesto=121858",
            self.card, self.detalle, "2026-11-01",
        )
        self.assertEqual(oferta["source_job_id"], "121858")
        self.assertEqual(oferta["job"]["job_id"], "ane-121858")
        self.assertEqual(oferta["source_updated_at"], "2026-11-01")
        self.assertIn("Nivel académico", oferta["job"]["requirements_raw"])
        self.assertEqual(oferta["job"]["country"], "CR")


class _PaginaFalsa:
    """Página de Playwright mínima (solo ``close``)."""

    def __init__(self):
        self.cerrada = False

    async def close(self):
        self.cerrada = True


class _ContextoFalso:
    def __init__(self):
        self.paginas = []

    async def new_page(self):
        pagina = _PaginaFalsa()
        self.paginas.append(pagina)
        return pagina


class TestReBarridoDeDetalle(unittest.TestCase):
    """Ola 4.1 · O5.3: volver a bajar el detalle de avisos YA guardados.

    Por que: el listado de ANE solo muestra las vacantas recientes, asi que
    un aviso viejo guardado con un parser viejo NUNCA vuelve a pasar por el
    listado: su texto se queda para siempre con los campos que el parser de
    entonces no leia.
    """

    def setUp(self):
        self.fetcher = AneFetcher(request_delay=0)
        self.ctx = _ContextoFalso()

    def _registros(self):
        return [
            {
                "source_job_id": "121858",
                "job_id": "ane-121858",
                "source_url": "https://www.ane.cr/Puesto/Detalles?Puesto=121858",
                "title": "Asesor de Ventas",
                "company": "OPTICAS MUNKEL",
                "location_raw": "San José",
            },
            {
                "source_job_id": "121899",
                "job_id": "ane-121899",
                "source_url": "https://www.ane.cr/Puesto/Detalles?Puesto=121899",
                "title": "Vacante que ya no existe",
                "company": "X",
                "location_raw": "",
            },
        ]

    def test_sin_sesion_no_hace_nada_y_lo_dice(self):
        with patch.object(self.fetcher, "_asegurar_sesion",
                          return_value=False):
            with self.assertRaises(RequiereLoginError):
                asyncio.run(self.fetcher._revisitar(self.ctx, {}, self._registros()))

    def test_revisa_los_avisos_guardados_y_salta_los_caidos(self):
        htmls = {
            "121858": HTML_DETALLE,
            "121899": "<html><body>no existe</body></html>",
        }

        async def _obtener(page, url, requiere_sesion=False):
            pid = url.rsplit("=", 1)[-1]
            return htmls.get(pid)

        with patch.object(self.fetcher, "_asegurar_sesion", return_value=True), \
             patch.object(self.fetcher, "_obtener", side_effect=_obtener):
            ofertas = asyncio.run(
                self.fetcher._revisitar(self.ctx, {}, self._registros())
            )

        # El que sigue en la web vuelve con el texto nuevo.
        self.assertEqual(len(ofertas), 1)
        self.assertEqual(ofertas[0]["source_job_id"], "121858")
        self.assertIn("Nivel académico",
                      ofertas[0]["job"]["requirements_raw"])
        # El que ya no esta se omite (no se borra lo que habia).
        self.assertEqual(ofertas.jobs_skipped, 1)

    def test_cierra_la_pagina_al_terminar(self):
        async def _obtener(page, url, requiere_sesion=False):
            return HTML_DETALLE

        with patch.object(self.fetcher, "_asegurar_sesion", return_value=True), \
             patch.object(self.fetcher, "_obtener", side_effect=_obtener):
            asyncio.run(
                self.fetcher._revisitar(self.ctx, {}, self._registros()[:1])
            )

        self.assertTrue(self.ctx.paginas[0].cerrada)

    def test_sin_url_arma_la_url_del_detalle(self):
        """Si el registro no trae URL, se arma la de ANE por su id."""
        registro = {
            "source_job_id": "121858",
            "source_url": "",
            "title": "Asesor de Ventas",
            "company": "OPTICAS MUNKEL",
            "location_raw": "",
        }
        vistas = []

        async def _obtener(page, url, requiere_sesion=False):
            vistas.append(url)
            return HTML_DETALLE

        with patch.object(self.fetcher, "_asegurar_sesion", return_value=True), \
             patch.object(self.fetcher, "_obtener", side_effect=_obtener):
            ofertas = asyncio.run(self.fetcher._revisitar(self.ctx, {}, [registro]))

        self.assertEqual(vistas, ["https://www.ane.cr/Puesto/Detalles?Puesto=121858"])
        self.assertEqual(len(ofertas), 1)


if __name__ == "__main__":
    unittest.main()
