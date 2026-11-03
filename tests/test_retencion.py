# -*- coding: utf-8 -*-
"""Tests de la retención y vigencia (O8/O10) en la UI v2.

- `RetencionStore`: lee y guarda `retencion_puestos_meses` y
  `solo_vigentes` en `ui_config.json` (el archivo del sistema, compartido
  con la UI clásica).
- El efecto: `JobsStore` y `AtsStore` **ocultan** los avisos vencidos
  (nunca los borran).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import unittest.mock
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import ciclo_vida
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository
from jobpulse_v15.ui_v2 import configuracion as config_ui
from jobpulse_v15.ui_v2.data.jobs import JobsStore
from jobpulse_v15.ui_v2.data.retencion import (
    DEFAULT_SOLO_VIGENTES,
    RetencionStore,
)
from jobpulse_v15.ui_v2.data.vacantes import AtsStore


class TestRetencionStore(unittest.TestCase):
    """La política de retención (archivo de preferencias del sistema)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temp_dir.name) / "ui_config.json"
        parche = unittest.mock.patch.object(config_ui, "ARCHIVO", self.ruta)
        parche.start()
        self.addCleanup(parche.stop)
        self.addCleanup(self.temp_dir.cleanup)
        self.store = RetencionStore()

    def test_sin_archivo_usa_los_defectos(self):
        retencion = self.store.retencion()
        self.assertEqual(retencion.meses, ciclo_vida.DEFAULT_RETENCION_PUESTOS)
        self.assertEqual(retencion.ventana_republicaciones,
                         ciclo_vida.DEFAULT_VENTANA_REPUBLICACIONES)
        self.assertEqual(retencion.solo_vigentes, DEFAULT_SOLO_VIGENTES)

    def test_guarda_los_meses(self):
        self.store.guardar_meses(3)
        self.assertEqual(self.store.retencion().meses, 3)
        # Y quedan en el archivo del sistema (lo lee la UI clásica).
        self.assertEqual(
            config_ui.cargar()[ciclo_vida.CLAVE_RETENCION_PUESTOS], 3)

    def test_guardar_los_meses_no_pisa_las_claves_ajenas(self):
        config_ui.guardar({"paleta": "oscuro"})
        self.store.guardar_meses(12)
        datos = config_ui.cargar()
        self.assertEqual(datos["paleta"], "oscuro")
        self.assertEqual(datos[ciclo_vida.CLAVE_RETENCION_PUESTOS], 12)

    def test_un_mes_no_permitido_da_error(self):
        with self.assertRaises(ValueError):
            self.store.guardar_meses(5)

    def test_guarda_solo_vigentes(self):
        self.store.guardar_solo_vigentes(False)
        self.assertFalse(self.store.solo_vigentes())
        self.assertFalse(
            config_ui.cargar()["solo_vigentes"])

    def test_un_valor_invalido_cae_al_defecto(self):
        config_ui.guardar({ciclo_vida.CLAVE_RETENCION_PUESTOS: "siete"})
        self.assertEqual(self.store.retencion().meses,
                         ciclo_vida.DEFAULT_RETENCION_PUESTOS)

    def test_la_ventana_de_consulta(self):
        self.store.guardar_meses(2)
        self.store.guardar_solo_vigentes(True)
        solo, meses = self.store.ventana_consulta()
        self.assertTrue(solo)
        self.assertEqual(meses, 2)

    def test_el_corte_es_la_fecha_de_hoy_menos_los_meses(self):
        self.store.guardar_meses(6)
        retencion = self.store.retencion()
        esperado = (date.today() - timedelta(days=30 * 6)).isoformat()
        self.assertEqual(retencion.corte, esperado)


class TestRetencionEnLosStores(unittest.TestCase):
    """El efecto: los stores ocultan los avisos vencidos."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.ruta_cfg = base / "ui_config.json"
        parche = unittest.mock.patch.object(config_ui, "ARCHIVO", self.ruta_cfg)
        parche.start()
        self.addCleanup(parche.stop)

        self.database = Database(base / "retencion.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.store = RetencionStore()

        # Un aviso de ayer (vigente) y otro de hace ~200 días (fuera de la
        # ventana de 6 meses, dentro de la de 12).
        with self.database.connection() as connection:
            connection.execute(
                "INSERT INTO jobs (job_id, title, company, date_published, "
                "posting_language, description_raw) VALUES "
                "('job-vigente', 'Puesto actual', 'Acme', ?, 'es', 'texto')",
                ((date.today() - timedelta(days=10)).isoformat(),),
            )
            connection.execute(
                "INSERT INTO jobs (job_id, title, company, date_published, "
                "posting_language, description_raw) VALUES "
                "('job-viejo', 'Puesto viejo', 'Acme', ?, 'es', 'texto')",
                ((date.today() - timedelta(days=200)).isoformat(),),
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_jobs_store_oculta_los_vencidos(self):
        store = JobsStore(self.repository, self.store)
        ids = {fila.job_id for fila in store.load()}
        self.assertIn("job-vigente", ids)
        self.assertNotIn("job-viejo", ids)

    def test_con_solo_vigentes_apagado_se_ven_todos(self):
        self.store.guardar_solo_vigentes(False)
        store = JobsStore(self.repository, self.store)
        ids = {fila.job_id for fila in store.load()}
        self.assertIn("job-vigente", ids)
        self.assertIn("job-viejo", ids)

    def test_la_ventana_menor_amplia_el_corte(self):
        self.store.guardar_meses(12)
        store = JobsStore(self.repository, self.store)
        ids = {fila.job_id for fila in store.load()}
        self.assertIn("job-viejo", ids)

    def test_ats_store_usa_la_misma_politica(self):
        store = AtsStore(self.repository, self.store)
        ids = {str(aviso.get("job_id")) for aviso in store.avisos()}
        self.assertIn("job-vigente", ids)
        self.assertNotIn("job-viejo", ids)

    def test_ocultar_no_borra_nada_de_la_bd(self):
        JobsStore(self.repository, self.store).load()
        with self.database.connection() as connection:
            total = connection.execute("SELECT COUNT(*) n FROM jobs").fetchone()["n"]
        self.assertEqual(total, 2)


if __name__ == "__main__":
    unittest.main()
