# -*- coding: utf-8 -*-
"""Tests de ``clean_run.py``: la limpieza deja la BD usable.

Reglas que se comprueban:
- se borra TODO lo derivado del scraping (incluido ``job_match`` y
  ``job_area``, que cuelgan de ``jobs`` con FK NO ACTION);
- se conservan perfil, configuracion de fuentes y taxonomias del sistema;
- no quedan filas huerfanas (la FK de ``job_match`` sigue apuntando a jobs).
"""
import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402


def _carga_clean_run():
    ruta = RAIZ / "clean_run.py"
    spec = importlib.util.spec_from_file_location("clean_run_bajo_test", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class TestCleanRun(unittest.TestCase):
    def setUp(self):
        self.clean_run = _carga_clean_run()
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "prueba.db"
        database = Database(self.db_path)
        database.initialize()
        self.repo = Repository(database)

        # Perfil y configuracion: deben SOBREVIVIR.
        self.repo.save_candidate_profile_fact(
            "skill", "python", "Python"
        )
        self.repo.register_platform(
            "workday", "Workday", "api", default_language="en"
        )
        self.repo.register_site(
            "workday-demo", "workday", "Demo",
            "https://demo.wd1.myworkdayjobs.com/x",
            company_name="Demo", country="CR", site_config={},
        )

        # Vacante: debe BORRARSE (y con ella sus derivados).
        self.repo.save_job(
            {"job_id": "demo-1", "title": "Vacante de prueba"},
            site_id="workday-demo", source_job_id="S-1",
            source_url="https://demo.test/1",
        )
        self.con = sqlite3.connect(self.db_path)
        self.con.execute(
            "INSERT INTO job_match (job_id, corrida_id, estado, evaluado_at, valida)"
            " VALUES ('demo-1', '20260101_000000', 'revisar_a_mano', '2026-01-01', 1)"
        )
        self.con.execute(
            "INSERT INTO job_area (job_id, area_codigo, confianza, clasificado_at)"
            " VALUES ('demo-1', 'informatica', 'titulo', '2026-01-01')"
        )
        self.con.commit()
        self.con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def _limpia(self):
        original = self.clean_run.DB_PATH
        self.clean_run.DB_PATH = self.db_path
        argv = sys.argv
        sys.argv = ["clean_run.py", "SI"]
        try:
            codigo = self.clean_run.main()
        finally:
            sys.argv = argv
            self.clean_run.DB_PATH = original
        return codigo

    def test_borra_datos_de_scraping_y_sus_derivados(self):
        self.assertEqual(self._limpia(), 0)
        con = sqlite3.connect(self.db_path)
        for tabla in ("jobs", "job_analysis", "job_requirements",
                      "job_source_records", "source_runs", "source_job_memory",
                      "job_match", "job_area"):
            with self.subTest(tabla=tabla):
                self.assertEqual(
                    con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0], 0
                )
        con.close()

    def test_conserva_perfil_configuracion_y_taxonomias(self):
        self.assertEqual(self._limpia(), 0)
        con = sqlite3.connect(self.db_path)
        self.assertGreater(
            con.execute("SELECT COUNT(*) FROM candidate_profile_facts").fetchone()[0], 0
        )
        self.assertGreater(
            con.execute("SELECT COUNT(*) FROM source_sites").fetchone()[0], 0
        )
        self.assertGreater(
            con.execute("SELECT COUNT(*) FROM source_platforms").fetchone()[0], 0
        )
        # La taxonomia de conceptos (migracion 009) debe seguir viva: el
        # matching la necesita para resolver codigo_canonico.
        self.assertGreater(
            con.execute("SELECT COUNT(*) FROM concepto").fetchone()[0], 0
        )
        con.close()

    def test_no_deja_huerfanos_en_job_match(self):
        self._limpia()
        con = sqlite3.connect(self.db_path)
        huerfanos = con.execute(
            """SELECT COUNT(*) FROM job_match m
               WHERE NOT EXISTS (SELECT 1 FROM jobs j WHERE j.job_id = m.job_id)"""
        ).fetchone()[0]
        con.close()
        self.assertEqual(huerfanos, 0)

    def test_sin_confirmacion_no_borra_nada(self):
        original = self.clean_run.DB_PATH
        self.clean_run.DB_PATH = self.db_path
        argv = sys.argv
        sys.argv = ["clean_run.py"]
        try:
            self.assertEqual(self.clean_run.main(), 0)
        finally:
            sys.argv = argv
            self.clean_run.DB_PATH = original
        con = sqlite3.connect(self.db_path)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1)
        con.close()

    def test_db_check_sigue_ok_tras_limpiar(self):
        self._limpia()
        database = Database(self.db_path)
        estado = database.check_integrity()
        self.assertTrue(estado["ok"], estado)
        self.assertEqual(estado["integrity_check"], ["ok"])
        self.assertEqual(estado["foreign_key_violations"], [])

    def test_reinicia_la_salud_de_los_sitios_al_borrar_las_corridas(self):
        """La salud se deriva de las corridas: si se borran, se reinicia.

        Sin este reset, cada `clean_run` dejaba vivos los raches de ceros y
        las banderas de revision de corridas anteriores.
        """
        for _ in range(2):
            run_id = self.repo.start_run("full")
            self.repo.record_site_result(
                run_id,
                "workday-demo",
                jobs_found=0,
                jobs_valid=0,
                jobs_new=0,
                jobs_duplicate=0,
            )
            self.repo.finish_run(run_id)
        sitio = self.repo.list_sites()[0]
        self.assertEqual(sitio["consecutive_zero_runs"], 2)

        self.assertEqual(self._limpia(), 0)

        sitio = self.repo.list_sites()[0]
        self.assertEqual(sitio["consecutive_zero_runs"], 0)
        self.assertFalse(sitio["review_required"])
        self.assertEqual(sitio["health_status"], "unknown")


if __name__ == "__main__":
    unittest.main()
