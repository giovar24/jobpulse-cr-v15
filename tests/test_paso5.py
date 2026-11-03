# -*- coding: utf-8 -*-
"""Tests del Paso 5 persistido desde la UI v2 (`Paso5Store`).

La UI ahora puede correr el matching y dejar la corrida GUARDADA en
`job_match` (antes solo se podía por CLI: `run_paso5.py`).

Patrón: tempfile + Database (no toca la BD real).
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository
from jobpulse_v15.ui_v2.data.paso5 import Paso5Store


def _insertar_fact(connection: sqlite3.Connection, code: str, canon: str,
                   cat: str) -> None:
    connection.execute(
        """
        INSERT INTO candidate_profile_facts
            (category, value_code, value_text, codigo_canonico)
        VALUES (?, ?, ?, ?)
        """,
        (cat, code, code, canon),
    )


def _insertar_job(connection: sqlite3.Connection, job_id: str,
                   descripcion: str) -> None:
    connection.execute(
        """
        INSERT INTO jobs (job_id, title, company, description_raw, posting_language)
        VALUES (?, ?, ?, ?, 'undetermined')
        """,
        (job_id, "Puesto de prueba", "Acme CR", descripcion),
    )
    connection.execute(
        """
        INSERT INTO job_analysis
            (job_id, text_hash, extractor_version, analysis_status, is_current)
        VALUES (?, 'hash-test', 'test-v1', 'complete', 1)
        """,
        (job_id,),
    )


class TestPaso5Store(unittest.TestCase):
    """El store corre el matching y persiste la corrida."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "paso5.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.store = Paso5Store(self.repository)

        with self.database.connection() as connection:
            _insertar_fact(connection, "bachiller-en-educacion-media",
                           "educacion-secundaria", "education")
            _insertar_job(connection, "job-a", "Sin titulo reviewed.")
            _insertar_job(connection, "job-b", "Bachelor degree requerido.")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_la_corrida_queda_guardada_en_job_match(self):
        resumen = self.store.ejecutar()
        self.assertTrue(resumen.corrida_id)
        self.assertEqual(resumen.evaluadas, 2)
        with self.database.connection() as connection:
            filas = connection.execute(
                "SELECT COUNT(*) AS n FROM job_match WHERE valida = 1 "
                "AND corrida_id = ?", (resumen.corrida_id,)
            ).fetchone()
        self.assertEqual(filas["n"], 2)

    def test_el_resumen_trae_estado_y_motivo(self):
        resumen = self.store.ejecutar()
        self.assertTrue(resumen.conteo)
        estados = {estado for estado, _motivo, _n in resumen.conteo}
        self.assertTrue(estados)
        self.assertEqual(sum(resumen.por_estado.values()), resumen.evaluadas)
        self.assertIn("|", resumen.texto())

    def test_cada_corrida_es_nueva_e_invalida_la_anterior(self):
        primera = self.store.ejecutar()
        segunda = self.store.ejecutar()
        # Aunque caigan en el mismo segundo, son dos corridas distintas.
        self.assertNotEqual(primera.corrida_id, segunda.corrida_id)
        with self.database.connection() as connection:
            validas = connection.execute(
                "SELECT DISTINCT corrida_id FROM job_match WHERE valida = 1"
            ).fetchall()
        self.assertEqual([f["corrida_id"] for f in validas], [segunda.corrida_id])

    def test_corrida_vigente_y_estados(self):
        self.assertEqual(self.store.corrida_vigente(), "")
        self.assertEqual(self.store.estado_vigente(), {})
        resumen = self.store.ejecutar()
        self.assertEqual(self.store.corrida_vigente(), resumen.corrida_id)
        estados = self.store.estado_vigente()
        self.assertIn("job-a", estados)
        self.assertIn("job-b", estados)

    def test_el_progreso_avisa(self):
        mensajes: list[str] = []
        self.store.ejecutar(progreso=mensajes.append)
        self.assertTrue(mensajes)
        self.assertTrue(any("perfil" in m for m in mensajes))

    def test_sin_avisos_con_analisis_no_evalua_nada(self):
        with self.database.connection() as connection:
            connection.execute("DELETE FROM job_analysis")
        resumen = self.store.ejecutar()
        self.assertEqual(resumen.evaluadas, 0)
        self.assertIn("Sin evaluables", resumen.texto())


if __name__ == "__main__":
    unittest.main()
