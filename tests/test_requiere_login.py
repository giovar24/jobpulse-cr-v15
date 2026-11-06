# -*- coding: utf-8 -*-
"""EL ESTADO `requiere_login` DE LA SALUD DE LOS SITIOS (O13 · Ola 3.3).

Un sitio que da 0 avisos porque PIDE INICIAR SESION no esta roto: es otra
cosa. Antes caia en `zero_results` y llenaba la racha de "sitio muerto"
(3 corridas con 0 avisos -> `review_required=1`) que el usuario tenia que
revisar a mano sin saber que lo que faltaba era la sesion.

REGLAS que estos tests fijan:

1. `requires_login` NO suma a la racha de ceros (`consecutive_zero_runs`).
2. El sitio queda con salud `requiere_login` y `review_required=1` (el
   usuario tiene que iniciar sesion).
3. `mark_site_reviewed` lo acknowledges (limpia la bandera) pero la salud
   sigue diciendo `requiere_login`.
4. Un barrido con avisos devuelve el sitio a `healthy`.
5. La corrida del sitio queda con estado `requires_login` (no `error`).
6. El barrido (UI v2 / scripts) lo muestra como estado propio, no como
   error.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.ingestion import IngestionService  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402
from jobpulse_v15.requiere_login import RequiereLoginError  # noqa: E402
from jobpulse_v15 import scraper  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "salud.db"
        self.database = Database(self.db_path)
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("ane", "ANE/Brete", "browser")
        self.repository.register_site(
            "ane-cr", "ane", "ANE Costa Rica", "https://www.ane.cr", company_name="ANE"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _sitio(self):
        return self.repository.get_site("ane-cr")

    def _estado(self):
        return self._sitio()["health_status"]


class TestSaludDelSitio(Base):
    def test_el_estado_requiere_login_se_acepta(self):
        self.assertEqual(self._estado(), "unknown")
        self.repository.record_site_result(
            self.repository.start_site_run("ane-cr", "ane"),
            "ane-cr",
            jobs_found=0, jobs_valid=0, jobs_new=0, jobs_duplicate=0,
            status="requires_login",
        )
        self.assertEqual(self._estado(), "requiere_login")

    def test_requiere_login_NO_suma_a_la_racha_de_ceros(self):
        # Primero se acquaintances con DOS ceros (todavia no es revision).
        for _ in range(2):
            self.repository.record_site_result(
                self.repository.start_site_run("ane-cr", "ane"),
                "ane-cr",
                jobs_found=0, jobs_valid=0, jobs_new=0, jobs_duplicate=0,
            )
        self.assertEqual(self._sitio()["consecutive_zero_runs"], 2)
        self.assertFalse(self._sitio()["review_required"])

        # Ahora el sitio pide login: la racha NO sigue creciendo.
        self.repository.record_site_result(
            self.repository.start_site_run("ane-cr", "ane"),
            "ane-cr",
            jobs_found=0, jobs_valid=0, jobs_new=0, jobs_duplicate=0,
            status="requires_login",
        )
        self.assertEqual(self._sitio()["consecutive_zero_runs"], 2)
        self.assertEqual(self._estado(), "requiere_login")
        # Y queda marcado para revision: el usuario tiene que iniciar sesion.
        self.assertTrue(self._sitio()["review_required"])

    def test_un_estado_invalido_es_error(self):
        with self.assertRaises(ValueError):
            self.repository.record_site_result(
                self.repository.start_site_run("ane-cr", "ane"),
                "ane-cr",
                jobs_found=0, jobs_valid=0, jobs_new=0, jobs_duplicate=0,
                status="inventado",
            )

    def test_mark_site_reviewed_acknowledges_pero_no_cambia_la_salud(self):
        self.repository.record_site_result(
            self.repository.start_site_run("ane-cr", "ane"),
            "ane-cr",
            jobs_found=0, jobs_valid=0, jobs_new=0, jobs_duplicate=0,
            status="requires_login",
        )
        self.assertTrue(self.repository.mark_site_reviewed("ane-cr"))
        sitio = self._sitio()
        self.assertFalse(sitio["review_required"])
        self.assertEqual(sitio["consecutive_zero_runs"], 0)
        # La sesion sigue haciendo falta: la salud no miente.
        self.assertEqual(sitio["health_status"], "requiere_login")

    def test_un_barrido_con_avisos_devuelve_el_sitio_a_healthy(self):
        self.repository.record_site_result(
            self.repository.start_site_run("ane-cr", "ane"),
            "ane-cr",
            jobs_found=0, jobs_valid=0, jobs_new=0, jobs_duplicate=0,
            status="requires_login",
        )
        self.repository.record_site_result(
            self.repository.start_site_run("ane-cr", "ane"),
            "ane-cr",
            jobs_found=3, jobs_valid=3, jobs_new=3, jobs_duplicate=0,
        )
        sitio = self._sitio()
        self.assertEqual(sitio["health_status"], "healthy")
        self.assertFalse(sitio["review_required"])
        self.assertEqual(sitio["consecutive_zero_runs"], 0)


class TestIngesta(Base):
    def test_un_muro_de_login_es_requires_login_y_no_error(self):
        service = IngestionService(self.repository)

        def fetch():
            raise RequiereLoginError("ane-cr: el sitio exige iniciar sesion.")

        resultado = service.fetch_and_import("ane-cr", fetch, run_kind="ane")
        self.assertTrue(resultado["requires_login"])
        self.assertEqual(resultado["site_status"], "requires_login")
        self.assertEqual(resultado["jobs_found"], 0)
        self.assertEqual(self._estado(), "requiere_login")

        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT status FROM source_run_sites WHERE site_id='ane-cr'"
            ).fetchone()
        self.assertEqual(fila["status"], "requires_login")

    def test_un_error_de_verdad_sigue_siendo_error(self):
        service = IngestionService(self.repository)

        def fetch():
            raise RuntimeError("se cayo la red")

        with self.assertRaises(Exception):
            service.fetch_and_import("ane-cr", fetch, run_kind="ane")
        self.assertEqual(self._estado(), "error")


class TestBarrido(Base):
    def test_el_barrido_muestra_el_estado_requiere_login(self):
        """El barrido de la UI v2 no lo reporta como error."""
        # Plataforma de API: el barrido NO abre el navegador (el test no
        # puede tocar el Brave del usuario).
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "wd-cr", "workday", "Workday CR", "https://example.test/jobs"
        )

        class FetcherFalso:
            def fetch(self, *args, **kwargs):
                raise RequiereLoginError("wd-cr: el sitio exige iniciar sesion.")

        with patch.object(scraper, "instanciar_fetcher", return_value=FetcherFalso()):
            resumen = scraper.ejecutar_barrido(
                ["wd-cr"], pages=1, port=9222, database_path=self.db_path,
            )

        self.assertEqual(len(resumen.resultados), 1)
        resultado = resumen.resultados[0]
        self.assertEqual(resultado.estado, scraper.ESTADO_REQUIERE_LOGIN)
        self.assertIn("sesion", resultado.mensaje)
        self.assertEqual(resumen.errores, 0)
        self.assertEqual(
            self.repository.get_site("wd-cr")["health_status"], "requiere_login"
        )


if __name__ == "__main__":
    unittest.main()
