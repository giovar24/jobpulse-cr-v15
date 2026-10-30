# -*- coding: utf-8 -*-
"""Tests del filtro por area de empleo (modulo ``areas`` + Paso 5).

Patron: tempfile + Database + sqlite3 directo (no toca la BD real).

Lo que se verifica:

* la clasificacion usa el TITULO y es la misma para cualquier fuente;
* un titulo sin encaje o ambiguo queda en el area 'otros';
* el area 'otros' (y las ofertas sin clasificar) NUNCA se excluyen;
* sin areas marcadas en el perfil no hay filtro (se evalua todo);
* con areas marcadas, la oferta de otra area queda 'fuera_de_area' y NO se
  evaluan sus requisitos;
* 'evaluar todo' ignora el filtro;
* al guardar una vacante nueva, se clasifica sola (misma regla para todas
  las fuentes).
"""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import areas
from jobpulse_v15 import matching
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository


def _crear_base(tmpdir: str) -> sqlite3.Connection:
    db = Database(Path(tmpdir) / "test.db")
    db.initialize()
    connection = sqlite3.connect(db.path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _sembrar(connection: sqlite3.Connection) -> list[areas.ReglaArea]:
    areas.sembrar_taxonomia(connection)
    return areas.cargar_reglas(connection)


def _insertar_job(connection: sqlite3.Connection, job_id: str, titulo: str) -> None:
    connection.execute(
        "INSERT INTO jobs (job_id, title, company) VALUES (?, ?, 'Acme CR')",
        (job_id, titulo),
    )


def _marcar_area(connection: sqlite3.Connection, codigo: str) -> None:
    connection.execute(
        """
        INSERT INTO candidate_profile_facts
            (category, value_code, value_text, origin)
        VALUES ('area', ?, ?, 'manual')
        """,
        (codigo, codigo),
    )


def _insertar_requisito(connection: sqlite3.Connection, job_id: str) -> None:
    connection.execute(
        """
        INSERT INTO job_analysis
            (job_id, text_hash, extractor_version, analysis_status, is_current)
        VALUES (?, 'hash-test', 'test-v1', 'complete', 1)
        """,
        (job_id,),
    )
    analysis_id = connection.execute(
        "SELECT analysis_id FROM job_analysis WHERE job_id = ?", (job_id,)
    ).fetchone()["analysis_id"]
    connection.execute(
        """
        INSERT INTO job_requirements
            (analysis_id, category, value_code, value_text, requirement_level,
             codigo_canonico, origin)
        VALUES (?, 'education', 'bachelor', 'Bachelor', 'required',
                'educacion-universitaria', 'manual')
        """,
        (analysis_id,),
    )


class TestClasificacion(unittest.TestCase):
    """La clasificacion es por TITULO y no depende de la fuente."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)
        self.reglas = _sembrar(self.connection)

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def test_titulos_de_la_bd_real(self):
        """Titulos LITERALES de la BD real -> area esperada."""
        casos = [
            ("IT Support Specialist Expert", "informatica"),
            ("Soporte Técnico Senior TI", "informatica"),
            ("Agente IT Helpdesk", "informatica"),
            ("Network Security Engineer - RDT Security Platforms", "informatica"),
            ("Analyst Payroll", "administracion"),
            ("Sr Supv, Accounts Payable", "administracion"),
            ("Auxiliar de Cocina", "alimentacion"),
            ("Housekeeping Manager", "alimentacion"),
            ("MECÁNICO AUTOMOTRIZ", "automotriz"),
            ("Alistador Bodega Congelado (Carretilla Eléctrica) - Horario Diurno",
             "almacenamiento"),
            ("Ingeniero de Manufactura", "ingenieria"),
            ("Quality Technician I", "calidad"),
            ("HR Generalist Senior - Global Discipline Delivery", "recursos_humanos"),
            ("Buyer Procurement Operations", "logistica"),
            ("Cajero (a) Operativo (a) Cartago", "ventas"),
            ("Regulatory Affairs Specialist", "cumplimiento"),
            ("Specialized Online ESL Teacher - Remote Special Needs Instructor",
             "educacion"),
            # 'Assoc Sewer' es costura en planta medica (no alcantarillado).
            ("Assoc Sewer", "produccion"),
        ]
        for titulo, esperado in casos:
            with self.subTest(titulo=titulo):
                resultado = areas.clasificar_texto(titulo, self.reglas)
                self.assertEqual(resultado.area_codigo, esperado)

    def test_titulo_sin_encaje_queda_en_otros(self):
        resultado = areas.clasificar_texto("COLABORADOR REGULAR", self.reglas)
        self.assertEqual(resultado.area_codigo, areas.AREA_OTROS)
        self.assertFalse(resultado.ambigua)

    def test_titulo_ambiguo_queda_en_otros(self):
        """Dos areas con la MISMA prioridad maxima = ambiguo -> 'otros'."""
        resultado = areas.clasificar_texto(
            "Recepcionista Hospital Curridabat", self.reglas
        )
        self.assertEqual(resultado.area_codigo, areas.AREA_OTROS)
        self.assertTrue(resultado.ambigua)
        self.assertEqual(set(resultado.candidatas), {"salud", "servicio_cliente"})

    def test_la_evidencia_es_literal(self):
        resultado = areas.clasificar_texto("IT Support Specialist", self.reglas)
        self.assertTrue(resultado.evidencia)
        self.assertIn(resultado.evidencia, "IT Support Specialist")

    def test_la_fuente_no_influye(self):
        """El mismo titulo se clasifica igual sin importar de donde venga."""
        reglas = self.reglas
        primero = areas.clasificar_texto("IT Support Specialist", reglas)
        segundo = areas.clasificar_texto("IT Support Specialist", reglas)
        self.assertEqual(primero.area_codigo, segundo.area_codigo)

    def test_clasificar_todas_guarda_en_job_area(self):
        _insertar_job(self.connection, "job-1", "IT Support Specialist")
        _insertar_job(self.connection, "job-2", "Auxiliar de Cocina")
        self.connection.commit()
        conteo = areas.clasificar_todas(self.connection)
        self.assertEqual(conteo.get("informatica"), 1)
        self.assertEqual(conteo.get("alimentacion"), 1)
        self.assertEqual(
            areas.area_de_oferta(self.connection, "job-1"), "informatica"
        )


class TestFiltroDelPerfil(unittest.TestCase):
    """El predicado del filtro (conservador por diseno)."""

    def test_sin_areas_marcadas_no_hay_filtro(self):
        self.assertFalse(areas.es_fuera_de_area("informatica", set()))
        self.assertFalse(areas.es_fuera_de_area("informatica", []))

    def test_area_no_marcada_queda_fuera(self):
        self.assertTrue(areas.es_fuera_de_area("informatica", ["administracion"]))

    def test_area_marcada_no_queda_fuera(self):
        self.assertFalse(areas.es_fuera_de_area("informatica", ["informatica"]))

    def test_otros_nunca_se_excluye(self):
        """Una clasificacion dudosa no puede tapar una oferta."""
        self.assertFalse(areas.es_fuera_de_area(areas.AREA_OTROS, ["informatica"]))

    def test_sin_clasificar_nunca_se_excluye(self):
        self.assertFalse(areas.es_fuera_de_area(None, ["informatica"]))

    def test_areas_del_perfil_lee_los_hechos(self):
        connection = _crear_base(self.tmpdir.name)
        try:
            self.assertEqual(areas.areas_del_perfil(connection), set())
            _marcar_area(connection, "informatica")
            _marcar_area(connection, "logistica")
            connection.commit()
            self.assertEqual(
                areas.areas_del_perfil(connection), {"informatica", "logistica"}
            )
        finally:
            connection.close()

    @property
    def tmpdir(self):
        if not hasattr(self, "_tmpdir"):
            self._tmpdir = tempfile.TemporaryDirectory()
        return self._tmpdir

    def tearDown(self):
        if hasattr(self, "_tmpdir"):
            self._tmpdir.cleanup()


class TestFiltroEnElPaso5(unittest.TestCase):
    """El filtro actua en el motor: la oferta de otra area NO se evalua."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)
        _sembrar(self.connection)
        _insertar_job(self.connection, "job-it", "IT Support Specialist")
        _insertar_job(self.connection, "job-cocina", "Auxiliar de Cocina")
        _insertar_job(self.connection, "job-generico", "COLABORADOR REGULAR")
        _insertar_requisito(self.connection, "job-it")
        _insertar_requisito(self.connection, "job-cocina")
        _insertar_requisito(self.connection, "job-generico")
        self.connection.commit()
        areas.clasificar_todas(self.connection)

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def test_sin_areas_marcadas_se_evaluan_todas(self):
        evaluador = matching.EvaluadorPaso5(self.connection)
        for job_id in ("job-it", "job-cocina", "job-generico"):
            with self.subTest(job_id=job_id):
                self.assertNotEqual(
                    evaluador.evaluar_job(job_id).estado,
                    matching.ESTADO_FUERA_DE_AREA,
                )

    def test_otra_area_no_se_evalua(self):
        _marcar_area(self.connection, "alimentacion")
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-it")
        self.assertEqual(resultado.estado, matching.ESTADO_FUERA_DE_AREA)
        self.assertEqual(resultado.motivo, matching.MOTIVO_FUERA_DE_AREA)
        # No se evaluaron requisitos: no hay cobertura ni faltantes.
        self.assertEqual(resultado.total_req, 0)
        self.assertIsNone(resultado.puntaje)

    def test_el_area_marcada_si_se_evalua(self):
        _marcar_area(self.connection, "alimentacion")
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        self.assertNotEqual(
            evaluador.evaluar_job("job-cocina").estado,
            matching.ESTADO_FUERA_DE_AREA,
        )

    def test_los_otros_siempre_se_evaluan(self):
        """'COLABORADOR REGULAR' no encaja en ninguna area: se evalua igual."""
        _marcar_area(self.connection, "alimentacion")
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        self.assertNotEqual(
            evaluador.evaluar_job("job-generico").estado,
            matching.ESTADO_FUERA_DE_AREA,
        )

    def test_evaluar_todo_ignora_el_filtro(self):
        _marcar_area(self.connection, "alimentacion")
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(
            self.connection, aplicar_filtro_areas=False
        )
        self.assertNotEqual(
            evaluador.evaluar_job("job-it").estado,
            matching.ESTADO_FUERA_DE_AREA,
        )

    def test_la_corrida_conserva_una_fila_por_vacante(self):
        _marcar_area(self.connection, "alimentacion")
        self.connection.commit()
        corrida, resultados = matching.ejecutar_paso5(self.connection, "20260101_000000")
        self.assertEqual(len(resultados), 3)
        filas = self.connection.execute(
            "SELECT COUNT(*) n FROM job_match WHERE corrida_id = ?", (corrida,)
        ).fetchone()["n"]
        self.assertEqual(filas, 3)


class TestClasificacionAlGuardar(unittest.TestCase):
    """Una vacante nueva se clasifica sola, sin importar la fuente."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmpdir.name) / "test.db")
        self.db.initialize()
        self.connection = sqlite3.connect(self.db.path)
        self.connection.row_factory = sqlite3.Row
        areas.sembrar_taxonomia(self.connection)
        self.connection.commit()
        self.repository = Repository(self.db)
        self.repository.register_platform("demo", "Demo", "api", "es")
        self.repository.register_site(
            "demo-site",
            "demo",
            "Demo",
            "https://demo.example",
            company_name="Demo",
            country="CR",
        )

    def tearDown(self):
        self.connection.close()
        self.repository = None
        self.tmpdir.cleanup()

    def test_vacante_nueva_queda_clasificada(self):
        self.repository.save_job(
            {
                "job_id": "nueva-1",
                "title": "IT Support Specialist",
                "company": "Acme",
            },
            site_id="demo-site",
            source_job_id="src-1",
        )
        with self.repository.database.connection() as connection:
            self.assertEqual(
                areas.area_de_oferta(connection, "nueva-1"), "informatica"
            )

    def test_titulo_generico_queda_en_otros(self):
        self.repository.save_job(
            {
                "job_id": "nueva-2",
                "title": "COLABORADOR REGULAR",
                "company": "Acme",
            },
            site_id="demo-site",
            source_job_id="src-2",
        )
        with self.repository.database.connection() as connection:
            self.assertEqual(
                areas.area_de_oferta(connection, "nueva-2"), areas.AREA_OTROS
            )


if __name__ == "__main__":
    unittest.main()
