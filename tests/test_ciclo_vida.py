# -*- coding: utf-8 -*-
"""Tests O8 ciclo de vida: herencia de republicaciones + vigencia.

Patron de tests/test_repository.py (tempdir + Database + Repository).
NO instancia ConfigurationWindow (patron test_configuration_window.py).
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import ciclo_vida
from jobpulse_v15.db import Database
from jobpulse_v15.ingestion import IngestionService
from jobpulse_v15.repository import Repository

DESCRIPCION_ORIGINAL = (
    "Se requiere ingeniero de soporte con 2 anos de experiencia en Windows "
    "Server, redes TCP/IP y atencion a usuarios. Office 365 avanzado. "
    "Trabajo presencial en Heredia."
)

DESCRIPCION_REPUBLICADA_RATIO = (
    "Se requiere ingeniero de soporte con 2 anos de experiencia en Windows "
    "Server, redes TCP/IP y atencion a usuarios. Office 365 avanzado. "
    "Trabajo presencial en Heredia. Se ofrece beneficios de ley."
)


def job_minimo(job_id, title="Soporte Tecnico", company="Acme CR",
               description=DESCRIPCION_ORIGINAL, **extra):
    data = {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location_raw": "Heredia, Costa Rica",
        "description_raw": description,
    }
    data.update(extra)
    return data


class TestNormalizacion(unittest.TestCase):
    def test_huella_descripcion_solo_alfanumericos_lowercase(self):
        huella = ciclo_vida.huella_descripcion("  Hola, Se\u00f1or\u00ae!\n 2026-A ")
        self.assertEqual(huella, "holasenor2026a")

    def test_huella_descripcion_vacia(self):
        self.assertEqual(ciclo_vida.huella_descripcion(None), "")
        self.assertEqual(ciclo_vida.huella_descripcion("   "), "")

    def test_clave_exacta_orden_insensible_y_acentos(self):
        clave_a = ciclo_vida.clave_exacta("Kuehne + Nagel", "Engineer, Senior", "San Jose")
        clave_b = ciclo_vida.clave_exacta("kuehne nagel", "senior engineer", "san jos\u00e9")
        self.assertIsNotNone(clave_a)
        self.assertEqual(clave_a, clave_b)

    def test_clave_exacta_requiere_ubicacion(self):
        self.assertIsNone(ciclo_vida.clave_exacta("Acme", "Dev", ""))
        self.assertIsNone(ciclo_vida.clave_exacta("Acme", "", "Heredia"))
        self.assertIsNone(ciclo_vida.clave_exacta("", "Dev", "Heredia"))

    def test_ratio_descripcion(self):
        huella = ciclo_vida.huella_descripcion(DESCRIPCION_ORIGINAL)
        self.assertEqual(ciclo_vida.ratio_descripcion(huella, huella), 1.0)
        self.assertEqual(ciclo_vida.ratio_descripcion(huella, ""), 0.0)
        otro = ciclo_vida.huella_descripcion("Completamente distinto a la anterior")
        self.assertLess(ciclo_vida.ratio_descripcion(huella, otro), 0.5)


class TestHerencia(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform(
            "workday", "Workday", "api", default_language="en"
        )
        self.repository.register_site(
            "intel-cr",
            "workday",
            "Intel Careers Costa Rica",
            "https://example.test/jobs",
            company_name="Intel",
            country="CR",
        )
        self.original_id = "job-original-1"
        self.repository.save_job(
            job_minimo(self.original_id),
            site_id="intel-cr",
            source_job_id="src-1",
        )
        self.repository.set_user_job_state(
            self.original_id, "reviewed", skip_automatic=True
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _guardar_republicacion(self, job_id="job-rep-1",
                               description=DESCRIPCION_ORIGINAL,
                               company="Acme CR"):
        return self.repository.save_job(
            job_minimo(job_id, description=description, company=company),
            site_id="intel-cr",
            source_job_id=job_id,
        )

    def test_herencia_exacta_clona_estado_y_oculta(self):
        self._guardar_republicacion()
        original = ciclo_vida.evaluar_herencia(
            self.repository, job_minimo("job-rep-1")
        )
        self.assertEqual(original, self.original_id)

        estado = self.repository.get_user_job_state("job-rep-1")
        self.assertIsNotNone(estado)
        self.assertEqual(estado["user_status"], "reviewed")
        self.assertTrue(estado["skip_automatic"])
        self.assertIn("job-original-1", estado["notes"])

        with self.database.connection() as connection:
            dup_of = connection.execute(
                "SELECT dup_of FROM jobs WHERE job_id = 'job-rep-1'"
            ).fetchone()[0]
        self.assertEqual(dup_of, self.original_id)

        visibles = self.repository.search_jobs(include_manually_skipped=False)
        self.assertNotIn("job-rep-1", {j["job_id"] for j in visibles})

    def test_herencia_por_ratio_sobre_umbral(self):
        self._guardar_republicacion(description=DESCRIPCION_REPUBLICADA_RATIO)
        original = ciclo_vida.evaluar_herencia(
            self.repository, job_minimo("job-rep-1",
                                        description=DESCRIPCION_REPUBLICADA_RATIO)
        )
        self.assertEqual(original, self.original_id)

    def test_ratio_bajo_no_hereda(self):
        otra = (
            "Se busca vendedor de piso para tienda comercial. Experiencia en "
            "atencion al cliente, caja y inventario. Turnos rotativos."
        )
        self._guardar_republicacion(description=otra)
        self.assertIsNone(
            ciclo_vida.evaluar_herencia(
                self.repository, job_minimo("job-rep-1", description=otra)
            )
        )
        self.assertIsNone(self.repository.get_user_job_state("job-rep-1"))

    def test_fuera_de_ventana_no_hereda(self):
        self._guardar_republicacion()
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE user_job_state SET updated_at = ? WHERE job_id = ?",
                ("2020-01-01 00:00:00", self.original_id),
            )
        self.assertIsNone(
            ciclo_vida.evaluar_herencia(
                self.repository, job_minimo("job-rep-1")
            )
        )
        self.assertIsNone(self.repository.get_user_job_state("job-rep-1"))
        with self.database.connection() as connection:
            dup_of = connection.execute(
                "SELECT dup_of FROM jobs WHERE job_id = 'job-rep-1'"
            ).fetchone()[0]
        self.assertIsNone(dup_of)

    def test_estados_no_herendables_dismissed_y_archived(self):
        for estado_no_herendable in ("dismissed", "archived"):
            with self.subTest(estado=estado_no_herendable):
                self.repository.set_user_job_state(
                    self.original_id, estado_no_herendable
                )
                self._guardar_republicacion(f"job-rep-{estado_no_herendable}")
                self.assertIsNone(
                    ciclo_vida.evaluar_herencia(
                        self.repository,
                        job_minimo(f"job-rep-{estado_no_herendable}"),
                    )
                )
                self.assertIsNone(
                    self.repository.get_user_job_state(
                        f"job-rep-{estado_no_herendable}"
                    )
                )
                # restaurar el estado original para el siguiente subTest
                self.repository.set_user_job_state(
                    self.original_id, "reviewed"
                )

    def test_empresa_distinta_no_hereda(self):
        self._guardar_republicacion(company="Otra Sociedad SA")
        self.assertIsNone(
            ciclo_vida.evaluar_herencia(
                self.repository, job_minimo("job-rep-1", company="Otra Sociedad SA")
            )
        )
        self.assertIsNone(self.repository.get_user_job_state("job-rep-1"))

    def test_no_sobrereescribe_estado_manual_existente(self):
        self._guardar_republicacion()
        self.repository.set_user_job_state("job-rep-1", "applied")
        self.assertIsNone(
            ciclo_vida.evaluar_herencia(
                self.repository, job_minimo("job-rep-1")
            )
        )
        estado = self.repository.get_user_job_state("job-rep-1")
        self.assertEqual(estado["user_status"], "applied")
        self.assertNotIn("job-original-1", estado["notes"] or "")

    def test_ingestion_hereda_best_effort(self):
        servicio = IngestionService(self.repository)
        resultado = servicio.import_offers(
            "intel-cr",
            [
                {
                    "job": job_minimo("job-rep-1"),
                    "source_job_id": "job-rep-1",
                    "source_url": None,
                    "raw_payload": None,
                    "source_updated_at": None,
                    "content_hash": None,
                }
            ],
        )
        self.assertEqual(resultado["jobs_new"], 1)
        estado = self.repository.get_user_job_state("job-rep-1")
        self.assertIsNotNone(estado)
        self.assertEqual(estado["user_status"], "reviewed")


class TestVigencia(unittest.TestCase):
    """solo_vigentes: port de purge_expired como ocultacion."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform(
            "workday", "Workday", "api", default_language="en"
        )
        self.repository.register_site(
            "intel-cr", "workday", "Intel", "https://example.test/jobs"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _guardar(self, job_id, **kwargs):
        self.repository.save_job(
            job_minimo(job_id, **kwargs),
            site_id="intel-cr",
            source_job_id=job_id,
        )

    def test_solo_vigentes_filtra_vencida_vieja_y_fresca(self):
        self._guardar(
            "job-vencida", expires_at="2020-01-01",
        )
        self._guardar(
            "job-vieja", date_published="2020-01-01",
        )
        self._guardar(
            "job-sin-fechas", date_published=None,
            description="Trabajo sin fecha de publicacion legible.",
        )
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE jobs SET first_seen_at = ? WHERE job_id = ?",
                ("2020-01-01 00:00:00", "job-sin-fechas"),
            )
        self._guardar(
            "job-fresca", expires_at="2099-01-01",
        )
        # Caso test_ui: sin expires_at NI date_published, first_seen fresco
        # -> VISIBLE (el NULL de las ramas no debe ocultarlo).
        self._guardar(
            "job-fresco-sin-fechas", date_published=None,
            description="Publicacion sin fechas legibles de ningun tipo.",
        )

        visibles = {
            j["job_id"]
            for j in self.repository.search_jobs(
                solo_vigentes=True, ventana_retencion_meses=6, limit=100
            )
        }
        self.assertNotIn("job-vencida", visibles)
        self.assertNotIn("job-vieja", visibles)
        self.assertNotIn("job-sin-fechas", visibles)
        self.assertIn("job-fresca", visibles)
        self.assertIn("job-fresco-sin-fechas", visibles)

        # Sin solo_vigentes, nada se oculta (nunca se borra nada).
        todas = {
            j["job_id"]
            for j in self.repository.search_jobs(limit=100)
        }
        self.assertEqual(
            todas,
            {"job-vencida", "job-vieja", "job-sin-fechas", "job-fresca",
             "job-fresco-sin-fechas"},
        )

    def test_expires_at_ilegible_deja_el_puesto_vigente(self):
        self._guardar("job-raro", expires_at="pronto")
        visibles = {
            j["job_id"]
            for j in self.repository.search_jobs(
                solo_vigentes=True, ventana_retencion_meses=6, limit=100
            )
        }
        self.assertIn("job-raro", visibles)

    def test_ventana_invalida_rechazada(self):
        with self.assertRaises(ValueError):
            self.repository.search_jobs(
                solo_vigentes=True, ventana_retencion_meses=0
            )


class TestPreferencias(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ruta = str(Path(self.temp_dir.name) / "ui_config.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_defaults_sin_archivo(self):
        prefs = ciclo_vida.preferencias(self.ruta)
        self.assertEqual(
            prefs[ciclo_vida.CLAVE_VENTANA_REPUBLICACIONES],
            ciclo_vida.DEFAULT_VENTANA_REPUBLICACIONES,
        )
        self.assertEqual(
            prefs[ciclo_vida.CLAVE_RETENCION_PUESTOS],
            ciclo_vida.DEFAULT_RETENCION_PUESTOS,
        )

    def test_round_trip_manteniendo_otras_claves(self):
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump({"theme": "oscuro", "font_size": 12}, f)
        ciclo_vida.guardar_preferencias(6, 12, config_file=self.ruta)
        with open(self.ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["theme"], "oscuro")
        self.assertEqual(data["font_size"], 12)
        prefs = ciclo_vida.preferencias(self.ruta)
        self.assertEqual(prefs[ciclo_vida.CLAVE_VENTANA_REPUBLICACIONES], 6)
        self.assertEqual(prefs[ciclo_vida.CLAVE_RETENCION_PUESTOS], 12)

    def test_valor_invalido_cae_al_default(self):
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump({ciclo_vida.CLAVE_VENTANA_REPUBLICACIONES: 7}, f)
        prefs = ciclo_vida.preferencias(self.ruta)
        self.assertEqual(
            prefs[ciclo_vida.CLAVE_VENTANA_REPUBLICACIONES],
            ciclo_vida.DEFAULT_VENTANA_REPUBLICACIONES,
        )

    def test_meses_fuera_de_catalogo_rechazados(self):
        with self.assertRaises(ValueError):
            ciclo_vida.guardar_preferencias(5, 6, config_file=self.ruta)
        with self.assertRaises(ValueError):
            ciclo_vida.corte_de_ventana(5)
        with self.assertRaises(ValueError):
            ciclo_vida.corte_de_retencion(0)


if __name__ == "__main__":
    unittest.main()
