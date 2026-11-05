# -*- coding: utf-8 -*-
"""Tests de las migraciones nuevas: 017, 018, 019, 020 y 021.

Las migraciones son el UNICO mecanismo de cambio de esquema (AGENTS.md):
cambio de BD = archivo nuevo `NNN_*.sql`, nunca `ALTER` manual ni editar
una migracion ya aplicada. Estos tests:

  * comprueban que la version del esquema avanza bien;
  * comprueban que cada migracion hace LO QUE DICE (y es idempotente);
  * comprueban que la 019 corrige el alias erroneo 'google-workspace' ->
    'microsoft-365' (Google Workspace NO es Microsoft 365);
  * comprueban que la 020/021 Amplian la taxonomia con lo que los avisos
    reales piden (idiomas que faltaban, alias y conceptos nuevos).

Para la 019 se reproduce el estado PREMIGRACION a mano y se ejecuta el
archivo .sql: asi se verifica el SQL real, no una copia.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402

MIGRACIONES = Path(__file__).resolve().parents[1] / "src" / "jobpulse_v15" / "migrations"


def _aplicar(connection: sqlite3.Connection, nombre: str) -> None:
    """Ejecuta una migracion suelta (el SQL real del archivo)."""
    sql = (MIGRACIONES / nombre).read_text(encoding="utf-8")
    connection.executescript(sql)


class TestVersionDelEsquema(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_la_base_nueva_llega_a_la_ultima_migracion(self):
        version = self.database.initialize()

        self.assertEqual(version, 21)
        with self.database.connection() as connection:
            actual = connection.execute("PRAGMA user_version").fetchone()[0]
        self.assertEqual(actual, 21)

    def test_inicializar_de_nuevo_no_cambia_nada(self):
        self.database.initialize()

        self.assertEqual(self.database.initialize(), 21)


class TestMigracion017(unittest.TestCase):
    """017: granularidad del nivel educativo (master/MBA/associate/bachiller)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _codigo(self, variante: str) -> str | None:
        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT codigo_canonico FROM concepto "
                "WHERE categoria='education' AND variante=?",
                (variante,),
            ).fetchone()
        return fila["codigo_canonico"] if fila else None

    def test_mba_y_master_son_posgrado(self):
        self.assertEqual(self._codigo("mba"), "educacion-posgrado")
        self.assertEqual(self._codigo("master"), "educacion-posgrado")

    def test_associate_degree_es_ciclo_corto(self):
        self.assertEqual(self._codigo("associate degree"), "educacion-tecnica")
        self.assertEqual(self._codigo("two year college degree"), "educacion-tecnica")

    def test_bachiller_a_secas_es_secundaria(self):
        # En CR 'bachiller' a secas es secundaria: NO es universitario.
        self.assertEqual(self._codigo("bachiller"), "educacion-secundaria")

    def test_la_escalera_de_niveles_cubre_los_cuatro_niveles(self):
        with self.database.connection() as connection:
            niveles = {
                fila["codigo"]: fila["orden"]
                for fila in connection.execute(
                    "SELECT codigo, orden FROM nivel_escala "
                    "WHERE categoria='education'"
                )
            }
        self.assertEqual(
            niveles,
            {
                "secundaria": 1,
                "tecnico": 2,
                "universitaria": 3,
                "posgrado": 4,
            },
        )


class TestMigracion018(unittest.TestCase):
    """018: tablas de señales de postulacion (estado del PROCESO)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_las_tablas_existen(self):
        with self.database.connection() as connection:
            tablas = {
                fila["name"]
                for fila in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertIn("postulacion", tablas)
        self.assertIn("postulacion_senal", tablas)

    def test_los_estados_permitidos_son_los_del_diseno(self):
        # 'rejected' es un estado del PROCESO, no una etiqueta de aptitud.
        with self.database.connection() as connection:
            self.repository.register_platform("workday", "Workday", "api")
            self.repository.register_site(
                "sitio", "workday", "Sitio", "https://example.test/jobs"
            )
            self.repository.save_job(
                {
                    "job_id": "job-1",
                    "title": "Puesto",
                    "company": "Example",
                    "country": "CR",
                    "posting_language": "en",
                    "description_raw": "Descripcion.",
                },
                site_id="sitio",
                source_job_id="J-1",
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO postulacion (job_id, estado)
                    VALUES ('job-1', 'contratado')
                    """
                )

    def test_la_bitacora_es_idempotente(self):
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "sitio", "workday", "Sitio", "https://example.test/jobs"
        )
        self.repository.save_job(
            {
                "job_id": "job-1",
                "title": "Puesto",
                "company": "Example",
                "country": "CR",
                "posting_language": "en",
                "description_raw": "Descripcion.",
            },
            site_id="sitio",
            source_job_id="J-1",
        )
        senal = {
            "estado": "applied",
            "portal": "workday",
            "source_job_id": "J-1",
            "url": "",
            "fecha": "2026-11-03 10:00:00",
            "remitente": "no-reply@myworkdayjobs.com",
            "asunto": "Your application has been received",
        }
        self.repository.registrar_senales_postulacion([senal])
        self.repository.registrar_senales_postulacion([senal])

        self.assertEqual(len(self.repository.listar_senales_postulacion()), 1)


class TestMigracion019(unittest.TestCase):
    """019: Google Workspace NO es Microsoft 365 (alias erroneo corregido)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "sitio", "workday", "Sitio", "https://example.test/jobs"
        )
        self.repository.save_job(
            {
                "job_id": "job-1",
                "title": "Puesto",
                "company": "Example",
                "country": "CR",
                "posting_language": "en",
                "description_raw": "Descripcion.",
            },
            site_id="sitio",
            source_job_id="J-1",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _estado_erroneo(self) -> None:
        """Reproduce el estado previo a la 019 (el alias erroneo)."""
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE concepto SET codigo_canonico='microsoft-365' "
                "WHERE categoria='skill' AND variante='google-workspace'"
            )
            connection.execute(
                """
                INSERT INTO candidate_profile_facts (
                    category, value_code, value_text, codigo_canonico
                ) VALUES ('skill', 'google-workspace', 'Google Workspace',
                          'microsoft-365')
                """
            )
            self._insertar_requisito(
                connection, "google-workspace", "microsoft-365"
            )

    @staticmethod
    def _insertar_requisito(
        connection: sqlite3.Connection, value_code: str, codigo: str
    ) -> None:
        """Inserta un requisito con el codigo que se quiere probar."""
        connection.execute(
            """
            INSERT INTO job_analysis (
                job_id, text_hash, extractor_version, analysis_status
            ) VALUES ('job-1', 'hash-1', 'rules-1', 'partial')
            """
        )
        analysis_id = connection.execute(
            "SELECT analysis_id FROM job_analysis WHERE job_id='job-1'"
        ).fetchone()["analysis_id"]
        connection.execute(
            """
            INSERT INTO job_requirements (
                analysis_id, category, value_code, value_text,
                requirement_level, codigo_canonico, evidence, origin, confidence
            ) VALUES (?, 'skill', ?, ?, 'ambiguous', ?, ?, 'rule', 0.8)
            """,
            (analysis_id, value_code, value_code, codigo, value_code),
        )

    def test_la_019_corrige_el_alias_del_perfil(self):
        self._estado_erroneo()

        with self.database.connection() as connection:
            _aplicar(connection, "019_google_workspace.sql")
            codigo = connection.execute(
                "SELECT codigo_canonico FROM candidate_profile_facts "
                "WHERE category='skill' AND value_code='google-workspace'"
            ).fetchone()["codigo_canonico"]

        self.assertEqual(codigo, "google-workspace")

    def test_la_019_corrige_el_alias_de_los_requisitos(self):
        self._estado_erroneo()

        with self.database.connection() as connection:
            _aplicar(connection, "019_google_workspace.sql")
            codigo = connection.execute(
                "SELECT codigo_canonico FROM job_requirements "
                "WHERE value_code='google-workspace'"
            ).fetchone()["codigo_canonico"]

        self.assertEqual(codigo, "google-workspace")

    def test_la_019_no_toca_un_microsoft_365_legitimo(self):
        with self.database.connection() as connection:
            self._insertar_requisito(connection, "office 365", "microsoft-365")

        with self.database.connection() as connection:
            _aplicar(connection, "019_google_workspace.sql")
            codigo = connection.execute(
                "SELECT codigo_canonico FROM job_requirements "
                "WHERE value_code='office 365'"
            ).fetchone()["codigo_canonico"]

        self.assertEqual(codigo, "microsoft-365")

    def test_la_019_es_idempotente(self):
        self._estado_erroneo()

        with self.database.connection() as connection:
            _aplicar(connection, "019_google_workspace.sql")
            _aplicar(connection, "019_google_workspace.sql")
            codigo = connection.execute(
                "SELECT codigo_canonico FROM candidate_profile_facts "
                "WHERE category='skill' AND value_code='google-workspace'"
            ).fetchone()["codigo_canonico"]

        self.assertEqual(codigo, "google-workspace")

    def test_el_slug_active_directory_resuelve(self):
        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT codigo_canonico FROM concepto "
                "WHERE categoria='skill' AND variante='active-directory'"
            ).fetchone()
        self.assertIsNotNone(fila)
        self.assertEqual(fila["codigo_canonico"], "active-directory")


class TestMigracion020(unittest.TestCase):
    """020: conceptos para ALINEAR (skills y licencias que faltaban)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _codigo(self, categoria: str, variante: str) -> str | None:
        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT codigo_canonico FROM concepto "
                "WHERE categoria=? AND variante=?",
                (categoria, variante),
            ).fetchone()
        return fila["codigo_canonico"] if fila else None

    def test_la_base_nueva_llega_a_la_ultima_migracion(self):
        with self.database.connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
        self.assertEqual(version, 21)

    def test_las_skills_que_pedia_el_corpus(self):
        for variante in (
            "java",
            "tableau",
            "six_sigma",
            "c++",
            "c#",
            "typescript",
            "autocad",
            "solidworks",
        ):
            self.assertEqual(self._codigo("skill", variante), variante)

    def test_las_clases_de_licencia_de_cr(self):
        for variante in ("a2", "b3", "c2", "d1", "d2", "d3", "e1", "f1"):
            self.assertEqual(
                self._codigo("license", variante), "licencia-conducir"
            )

    def test_la_licencia_generica_sin_clase(self):
        self.assertEqual(
            self._codigo("license", "driver's license"), "licencia-conducir"
        )

    def test_la_migracion_es_idempotente(self):
        with self.database.connection() as connection:
            antes = connection.execute(
                "SELECT COUNT(*) FROM concepto"
            ).fetchone()[0]
            _aplicar(connection, "020_conceptos_alineacion.sql")
            _aplicar(connection, "020_conceptos_alineacion.sql")
            despues = connection.execute(
                "SELECT COUNT(*) FROM concepto"
            ).fetchone()[0]
        self.assertEqual(antes, despues)

    def test_no_toca_los_conceptos_que_ya_existian(self):
        # 'excel' ya venia de la 009: la 020 no lo duplica ni lo cambia.
        self.assertEqual(self._codigo("skill", "excel"), "excel")
        self.assertEqual(self._codigo("skill", "microsoft excel"), "excel")
        self.assertEqual(self._codigo("license", "b1"), "licencia-conducir")


class TestMigracion021(unittest.TestCase):
    """021: taxonomia que crece con los CAMPOS ESTRUCTURADOS del aviso.

    El corpus real (2026-11-04) traia 2438 menciones de skills de la fuente
    y solo 45 resolvian: el 98% NO era comparable con el perfil. Esta
    migracion anade los idiomas que faltaban, los alias de lo que ya existia
    y los conceptos nuevos (retail, manufactura, calidad, contabilidad,
    finanzas, IT/soporte, RRHH).
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _codigo(self, categoria: str, variante: str) -> str | None:
        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT codigo_canonico FROM concepto "
                "WHERE categoria=? AND variante=?",
                (categoria, variante),
            ).fetchone()
        return fila["codigo_canonico"] if fila else None

    def test_los_idiomas_que_faltaban_existen(self):
        for variante, codigo in (
            ("aleman", "aleman"),
            ("german", "aleman"),
            ("italiano", "italiano"),
            ("chino", "chino"),
            ("simplified chinese", "chino"),
            ("japones", "japones"),
            ("coreano", "coreano"),
            ("arabe", "arabe"),
            ("neerlandes", "neerlandes"),
        ):
            self.assertEqual(self._codigo("language", variante), codigo)

    def test_los_alias_de_lo_que_ya_existia(self):
        # El aviso nombra la misma competencia de otra forma: tiene que
        # resolver al MISMO codigo canonico.
        self.assertEqual(self._codigo("skill", "consultas sql"), "sql")
        self.assertEqual(self._codigo("skill", "service now"), "servicenow")
        self.assertEqual(self._codigo("skill", "azure active directory"), "active-directory")
        self.assertEqual(self._codigo("skill", "microsoft office"), "microsoft-365")
        self.assertEqual(self._codigo("skill", "ci cd pipelines"), "ci-cd")

    def test_los_conceptos_nuevos_que_pedia_el_corpus(self):
        for variante, codigo in (
            ("apertura de caja", "apertura-caja"),
            ("frenteos", "frenteos"),
            ("transacciones de cobro", "transacciones-cobro"),
            ("manejo de inventarios", "inventarios"),
            ("quality control", "control-calidad"),
            ("journal entries", "asientos-contables"),
            ("incident response", "incident-response"),
            ("metodologias agiles", "metodologias-agiles"),
            ("kubernetes", "kubernetes"),
            ("troubleshooting", "troubleshooting"),
        ):
            self.assertEqual(self._codigo("skill", variante), codigo)

    def test_no_entran_las_etiquetas_genericas(self):
        # Funcion, sector o palabra vacia: no son competencias (contarlas
        # penaliza a todos los avisos por igual y esconde los gaps reales).
        for variante in ("ventas", "construccion", "analysis", "planning"):
            self.assertIsNone(self._codigo("skill", variante), variante)

    def test_la_migracion_es_idempotente(self):
        with self.database.connection() as connection:
            antes = connection.execute("SELECT COUNT(*) FROM concepto").fetchone()[0]
            _aplicar(connection, "021_taxonomia_fuente.sql")
            _aplicar(connection, "021_taxonomia_fuente.sql")
            despues = connection.execute("SELECT COUNT(*) FROM concepto").fetchone()[0]
        self.assertEqual(antes, despues)

    def test_no_toca_los_conceptos_que_ya_existian(self):
        self.assertEqual(self._codigo("skill", "excel"), "excel")
        self.assertEqual(self._codigo("skill", "python"), "python")
        self.assertEqual(self._codigo("language", "en"), "ingles")
        self.assertEqual(self._codigo("skill", "active-directory"), "active-directory")

    def test_todas_las_variantes_nuevas_estan_normalizadas(self):
        # El resolver busca `LOWER(TRIM(value_code))` y el modulo
        # `skills_fuente` normaliza igual: minusculas, sin acentos.
        with self.database.connection() as connection:
            filas = connection.execute(
                "SELECT variante FROM concepto "
                "WHERE categoria IN ('skill','language','license')"
            ).fetchall()
        for fila in filas:
            variante = fila["variante"]
            self.assertEqual(variante, variante.lower(), variante)
            self.assertNotIn("  ", variante, variante)


if __name__ == "__main__":
    unittest.main()
