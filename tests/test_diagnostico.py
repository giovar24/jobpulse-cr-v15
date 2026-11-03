# -*- coding: utf-8 -*-
"""Tests del diagnóstico (`jobpulse_v15.diagnostico`).

El informe es de SOLO LECTURA: mide la integridad de la BD, los huecos del
enriquecimiento y la calidad de los datos.

Patrón: tempfile + Database (nunca toca la BD real).
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import diagnostico as modulo
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository


def _insertar_job(connection: sqlite3.Connection, job_id: str,
                   company: str = "Acme CR") -> None:
    connection.execute(
        """
        INSERT INTO jobs (job_id, title, company, description_raw, posting_language)
        VALUES (?, 'Puesto de prueba', ?, 'Descripción de prueba', 'es')
        """,
        (job_id, company),
    )


class TestDiagnostico(unittest.TestCase):
    """El informe sobre una BD temporal."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "diag.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        with self.database.connection() as connection:
            _insertar_job(connection, "job-a")
            _insertar_job(connection, "job-b")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_una_bd_sana_da_ok(self):
        reporte = modulo.diagnostico(self.repository)
        self.assertTrue(reporte.ok)
        self.assertEqual(reporte.integridad, "ok")
        self.assertEqual(reporte.fk, 0)
        self.assertIn("sana", reporte.estado_integridad)

    def test_mide_los_avisos_de_la_bd_abierta(self):
        """No debe leer la BD del proyecto: la que se le da."""
        reporte = modulo.diagnostico(self.repository)
        self.assertEqual(reporte.total_jobs, 2)

    def test_detecta_una_clave_foranea_rota(self):
        conexion = sqlite3.connect(self.database.path)
        try:
            conexion.execute(
                "INSERT INTO job_match (job_id, estado, corrida_id) "
                "VALUES ('job-inexistente', 'calificada', '20260101_000000')"
            )
            conexion.commit()
        finally:
            conexion.close()
        reporte = modulo.diagnostico(self.repository)
        self.assertFalse(reporte.ok)
        self.assertEqual(reporte.fk, 1)
        self.assertIn("foránea", reporte.estado_integridad)

    def test_el_informe_tiene_lineas_legibles(self):
        reporte = modulo.diagnostico(self.repository)
        texto = reporte.texto()
        self.assertIn("Base de datos:", texto)
        self.assertIn("Avisos: 2", texto)
        self.assertIn("Integridad: ok", texto)
        self.assertIn("Todo: OK", texto)

    def test_una_bd_inexistente_reporta_error(self):
        otro = Database(Path(self.temp_dir.name) / "no-existe.db")
        reporte = modulo.diagnostico(Repository(otro))
        self.assertFalse(reporte.ok)
        self.assertTrue(reporte.error)
        self.assertIn("NO SE PUDO DIAGNOSTICAR", reporte.texto())

    def test_el_resumen_corto(self):
        resumen = modulo.resumen_corto(self.repository)
        self.assertTrue(resumen["ok"])
        self.assertEqual(resumen["total_jobs"], 2)
        self.assertGreater(resumen["esquema"], 0)


if __name__ == "__main__":
    unittest.main()
