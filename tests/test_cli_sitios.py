# -*- coding: utf-8 -*-
"""Tests del CLI para O2.2 (filtro de requisitos obligatorios) y O3 (salud
de los sitios).

El CLI y la UI deben dar el MISMO dato: estos tests fijan el contrato de la
linea de comandos (flags, salida y efectos) para que no diverjan.
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.cli import main
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository


class TestCliSitios(unittest.TestCase):
    """O3: listar los sitios pendientes y resolver la revision manual."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        for site_id in ("sitio-ok", "sitio-cero"):
            self.repository.register_site(
                site_id,
                "workday",
                site_id,
                f"https://example.test/{site_id}",
                run_groups=("directos",),
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _corrida_con_ceros(self, site_id: str, veces: int = 1) -> None:
        for _ in range(veces):
            run_id = self.repository.start_run("full", "directos")
            for sitio in ("sitio-ok", "sitio-cero"):
                self.repository.record_site_result(
                    run_id,
                    sitio,
                    jobs_found=0 if sitio == site_id else 1,
                    jobs_valid=0 if sitio == site_id else 1,
                    jobs_new=0 if sitio == site_id else 1,
                    jobs_duplicate=0,
                )
            self.repository.finish_run(run_id)

    def _cli(self, *argumentos: str) -> str:
        salida = io.StringIO()
        with patch(
            "sys.argv",
            ["jobpulse-v15", "--db", str(self.database.path), *argumentos],
        ), redirect_stdout(salida):
            self.assertEqual(main(), 0)
        return salida.getvalue()

    def test_site_list_needs_review_muestra_solo_los_marcados(self):
        self._corrida_con_ceros("sitio-cero", veces=3)

        salida = self._cli("site", "list", "--needs-review")
        sitios = json.loads(salida)

        self.assertEqual([s["site_id"] for s in sitios], ["sitio-cero"])
        self.assertTrue(sitios[0]["review_required"])

    def test_mark_reviewed_de_un_sitio_reinicia_su_rache(self):
        self._corrida_con_ceros("sitio-cero", veces=3)
        self.assertEqual(
            self.repository.list_sites(needs_review_only=True)[0][
                "consecutive_zero_runs"
            ],
            3,
        )

        salida = self._cli("site", "mark-reviewed", "--id", "sitio-cero")

        self.assertIn("sitio-cero", salida)
        sitios = {s["site_id"]: s for s in self.repository.list_sites()}
        self.assertFalse(sitios["sitio-cero"]["review_required"])
        self.assertEqual(sitios["sitio-cero"]["consecutive_zero_runs"], 0)
        # El sitio sano no se toca.
        self.assertEqual(sitios["sitio-ok"]["consecutive_zero_runs"], 0)

    def test_mark_reviewed_all_needs_review_resuelve_todos(self):
        self._corrida_con_ceros("sitio-cero", veces=3)

        salida = self._cli("site", "mark-reviewed", "--all-needs-review")

        self.assertIn("1 sitio(s)", salida)
        self.assertIn("sitio-cero", salida)
        self.assertEqual(self.repository.list_sites(needs_review_only=True), [])
        self.assertEqual(
            self.repository.list_sites()[0]["consecutive_zero_runs"], 0
        )

    def test_mark_reviewed_exige_un_destino(self):
        with self.assertRaises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "jobpulse-v15",
                    "--db",
                    str(self.database.path),
                    "site",
                    "mark-reviewed",
                ],
            ):
                main()


class TestCliBusqueda(unittest.TestCase):
    """O2.2: el flag de busqueda que deja solo avisos con obligatorios."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "sitio-1",
            "workday",
            "Sitio 1",
            "https://example.test/jobs",
        )
        for job_id in ("job-ok", "job-sin-req"):
            self.repository.save_job(
                {
                    "job_id": job_id,
                    "title": "Puesto",
                    "company": "Example",
                    "country": "CR",
                    "city": "San Jose",
                    "posting_language": "en",
                },
                site_id="sitio-1",
                source_job_id=job_id,
            )
        self.repository.save_analysis(
            "job-ok",
            text_hash="hash-ok",
            extractor_version="rules-1",
            analysis_status="complete",
            field_statuses={"language": "found"},
            requirements=[
                {
                    "category": "language",
                    "value_code": "en",
                    "value_text": "English",
                    "requirement_level": "required",
                    "evidence": "Fluent English required.",
                    "origin": "rule",
                    "confidence": 0.9,
                }
            ],
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _cli(self, *argumentos: str) -> str:
        salida = io.StringIO()
        with patch(
            "sys.argv",
            ["jobpulse-v15", "--db", str(self.database.path), *argumentos],
        ), redirect_stdout(salida):
            self.assertEqual(main(), 0)
        return salida.getvalue()

    def test_search_solo_requisitos_obligatorios_filtra_en_el_cli(self):
        salida = self._cli(
            "search", "--solo-requisitos-obligatorios", "--limit", "50"
        )
        resultados = json.loads(salida)

        self.assertEqual([r["job_id"] for r in resultados], ["job-ok"])
        self.assertEqual(resultados[0]["req_obligatorios"], 1)

    def test_search_sin_el_filtro_devuelve_todo_con_el_conteo(self):
        salida = self._cli("search", "--limit", "50")
        resultados = json.loads(salida)

        conteos = {r["job_id"]: r["req_obligatorios"] for r in resultados}
        self.assertEqual(conteos, {"job-ok": 1, "job-sin-req": 0})


if __name__ == "__main__":
    unittest.main()
