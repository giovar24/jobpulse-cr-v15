# -*- coding: utf-8 -*-
"""PIPELINE (orquestador único) — O12 · Ola 2.1/2.2/2.3.

Antes cada llamador (CLI, UI clásica, UI v2) tenía su propio camino y la UI
veía 231 avisos `sin_requisitos` frente a 11 de la CLI. Ahora hay UN
orquestador (`jobpulse_v15.pipeline`) y todos los caminos pasan por él.

REGLAS DURAS que estos tests fijan:

1. una etapa desconocida es ``ValueError`` (nunca se ignora en silencio);
2. el orden de las etapas es el documentado (scrape → análisis → IA →
   re-análisis → backfill → Paso 5 → evidencia);
3. el Paso 5 es siempre una **corrida nueva** (las previas quedan
   ``valida=0``);
4. sin IA configurada la etapa se OMITE (no rompe el pipeline);
5. dos corridas del pipeline sobre la misma BD dan el **mismo estado** de
   `job_match` (paridad CLI/UI: ahora es la misma implementación);
6. la evidencia se genera y verifica sin subprocess.
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import pipeline  # noqa: E402
from jobpulse_v15.analysis_flow import extract_job_analysis  # noqa: E402
from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402

DESCRIPCION = (
    "Buscamos un ingeniero de soporte con experiencia en redes. "
    "Requisitos: mínimo 3 años de experiencia, manejo de Linux y SQL. "
    "Se requiere bachelor's degree en Computer Science."
)


class Base(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temp_dir.name)
        self.db_path = self.raiz / "data" / "jobpulse_v15.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.database = Database(self.db_path)
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "sitio", "workday", "Sitio", "https://example.test/jobs"
        )
        self.docs = self.raiz / "docs"
        self.docs.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _job(self, job_id="job-1", **campos):
        datos = {
            "job_id": job_id,
            "title": "Support Engineer",
            "company": "Example",
            "country": "CR",
            "posting_language": "en",
            "description_raw": DESCRIPCION,
        }
        datos.update(campos)
        self.repository.save_job(datos, site_id="sitio", source_job_id=job_id)
        return job_id

    def _campos(self, job_id, skills=None, languages=None):
        with self.database.connection() as connection:
            if skills is not None:
                connection.execute(
                    "UPDATE jobs SET skills = ? WHERE job_id = ?", (skills, job_id)
                )
            if languages is not None:
                connection.execute(
                    "UPDATE jobs SET languages = ? WHERE job_id = ?",
                    (languages, job_id),
                )

    def _match(self):
        with self.database.connection() as connection:
            filas = connection.execute(
                "SELECT job_id, estado, motivo, valida, corrida_id "
                "FROM job_match ORDER BY corrida_id, job_id"
            ).fetchall()
        return [dict(fila) for fila in filas]

    def _requisitos(self, job_id):
        with self.database.connection() as connection:
            filas = connection.execute(
                "SELECT r.category, r.value_text, r.origin, r.codigo_canonico "
                "FROM job_requirements AS r "
                "JOIN job_analysis AS a ON a.analysis_id = r.analysis_id "
                "WHERE a.job_id = ? AND a.is_current = 1",
                (job_id,),
            ).fetchall()
        return [dict(fila) for fila in filas]


class TestContrato(Base):
    def test_etapa_desconocida_es_error(self):
        with self.assertRaises(ValueError):
            pipeline.ejecutar(self.repository, etapas=("inventada",))

    def test_orden_de_las_etapas(self):
        self.assertEqual(
            pipeline.ETAPAS,
            ("scrape", "analisis", "ia", "reanalisis", "backfill", "paso5",
             "evidencia"),
        )
        # El default NO raspa (hace falta saber qué sitios) ni hace backfill.
        self.assertNotIn("scrape", pipeline.ETAPAS_POR_DEFECTO)
        self.assertNotIn("backfill", pipeline.ETAPAS_POR_DEFECTO)
        self.assertIn("paso5", pipeline.ETAPAS_POR_DEFECTO)

    def test_scrape_sin_sitios_no_hace_nada(self):
        resultado = pipeline.ejecutar(self.repository, etapas=("scrape",))
        etapa = resultado["etapas"]["scrape"]
        self.assertFalse(etapa["ok"])
        self.assertIn("sites", etapa["motivo"])

    def test_el_progreso_reporta_cada_etapa(self):
        self._job()
        lineas = []
        pipeline.ejecutar(
            self.repository,
            etapas=("analisis", "paso5"),
            progreso=lineas.append,
            db_path=self.db_path,
        )
        self.assertIn("=== ANALISIS ===", lineas)
        self.assertIn("=== PASO5 ===", lineas)

    def test_resumen_linea(self):
        self._job()
        resultado = pipeline.ejecutar(
            self.repository, etapas=("analisis", "paso5"), db_path=self.db_path
        )
        linea = pipeline.resumen_linea(resultado)
        self.assertIn("PIPELINE:", linea)
        self.assertIn("paso5=", linea)


class TestMetricas(Base):
    """Ola 4.3: cada etapa deja su metrica en `pipeline_etapa`."""

    def _metricas(self):
        with self.database.connection() as connection:
            filas = connection.execute(
                "SELECT corrida_id, etapa, ok, duracion_ms, avisos, requisitos,"
                " errores, detalle_json FROM pipeline_etapa ORDER BY id"
            ).fetchall()
        return [dict(fila) for fila in filas]

    def test_cada_etapa_registra_su_metrica(self):
        self._job()
        resultado = pipeline.ejecutar(
            self.repository, etapas=("analisis", "paso5"), db_path=self.db_path
        )
        metricas = self._metricas()
        self.assertEqual([m["etapa"] for m in metricas], ["analisis", "paso5"])
        for metrica in metricas:
            self.assertEqual(metrica["corrida_id"], resultado["corrida_pipeline"])
            self.assertEqual(metrica["ok"], 1)
            self.assertGreaterEqual(metrica["duracion_ms"], 0)
        analisis = metricas[0]
        self.assertEqual(analisis["avisos"], 1)
        self.assertGreater(analisis["requisitos"], 0)

    def test_el_id_del_pipeline_es_distinto_del_del_paso5(self):
        """El `corrida_id` del pipeline agrupa etapas; el del Paso 5 es el
        de `job_match` (son cosas distintas)."""
        self._job()
        resultado = pipeline.ejecutar(
            self.repository, etapas=("analisis", "paso5"), db_path=self.db_path
        )
        self.assertTrue(resultado["corrida_pipeline"].startswith("pipe_"))
        self.assertNotEqual(resultado["corrida_pipeline"], resultado["corrida"])
        paso5 = [m for m in self._metricas() if m["etapa"] == "paso5"][0]
        self.assertEqual(json.loads(paso5["detalle_json"])["corrida"], resultado["corrida"])

    def test_una_metrica_que_falla_no_rompe_el_pipeline(self):
        """La instrumentacion es aditiva: si falla, la corrida sigue."""
        self._job()
        from jobpulse_v15 import pipeline_metricas

        with patch.object(
            pipeline_metricas,
            "registrar_etapa",
            side_effect=sqlite3.OperationalError("no se pudo escribir"),
        ):
            resultado = pipeline.ejecutar(
                self.repository, etapas=("analisis", "paso5"), db_path=self.db_path
            )
        self.assertTrue(resultado["ok"], resultado.get("errores"))
        self.assertIn("paso5", resultado["etapas"])
        self.assertEqual(self._metricas(), [])

    def test_la_etapa_que_falla_queda_registrada(self):
        self._job()
        resultado = pipeline.ejecutar(
            self.repository, etapas=("scrape",), db_path=self.db_path
        )
        metricas = self._metricas()
        self.assertEqual(len(metricas), 1)
        self.assertEqual(metricas[0]["etapa"], "scrape")
        # Sin sitios no hay nada que barrer: la etapa lo dice (ok=False).
        self.assertEqual(metricas[0]["ok"], 0)
        self.assertFalse(resultado["ok"])


class TestEtapas(Base):
    def test_analisis_analiza_los_pendientes(self):
        self._job()
        resultado = pipeline.ejecutar(
            self.repository, etapas=("analisis",), db_path=self.db_path
        )
        etapa = resultado["etapas"]["analisis"]
        self.assertEqual(etapa["pendientes"], 1)
        self.assertEqual(etapa["analizados"], 1)
        self.assertTrue(self.repository.get_current_analysis("job-1"))

    def test_ia_sin_configurar_se_omite(self):
        from jobpulse_v15 import ia_enrichment as iae

        with patch.object(iae, "get_ia_client", lambda: None):
            resultado = pipeline.ejecutar(
                self.repository, etapas=("ia",), db_path=self.db_path
            )
        etapa = resultado["etapas"]["ia"]
        self.assertEqual(etapa["estado"], "omitido")
        self.assertFalse(etapa["ok"])
        # No rompe el pipeline: la etapa está, con su motivo.
        self.assertIn("ia", resultado["etapas"])

    def test_reanalisis_integra_los_campos_de_la_ia(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)  # análisis ANTES de la IA
        self._campos(job_id, skills=json.dumps(["Python"]))

        resultado = pipeline.ejecutar(
            self.repository, etapas=("reanalisis",), db_path=self.db_path
        )
        etapa = resultado["etapas"]["reanalisis"]
        self.assertEqual(etapa["candidatos"], 1)
        self.assertEqual(etapa["reanalizados"], 1)
        origenes = {r["origin"] for r in self._requisitos(job_id)}
        self.assertIn("source_field", origenes)

    def test_reanalisis_es_idempotente(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._campos(job_id, skills=json.dumps(["Python"]))
        pipeline.ejecutar(self.repository, etapas=("reanalisis",), db_path=self.db_path)

        segunda = pipeline.ejecutar(
            self.repository, etapas=("reanalisis",), db_path=self.db_path
        )
        self.assertEqual(segunda["etapas"]["reanalisis"]["reanalizados"], 0)

    def test_backfill_solo_toca_los_nulos(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        with self.database.connection() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM job_requirements WHERE codigo_canonico IS NULL"
            ).fetchone()[0]
        resultado = pipeline.ejecutar(
            self.repository, etapas=("backfill",), db_path=self.db_path
        )
        etapa = resultado["etapas"]["backfill"]
        self.assertEqual(etapa["sin_codigo"], total)
        self.assertTrue(etapa["ok"])

    def test_paso5_es_corrida_nueva_e_invalida_la_anterior(self):
        self._job()
        primera = pipeline.ejecutar(
            self.repository, etapas=("analisis", "paso5"), db_path=self.db_path
        )
        corrida_1 = primera["etapas"]["paso5"]["corrida"]
        self.assertEqual(len(self._match()), 1)
        self.assertEqual(self._match()[0]["valida"], 1)

        segunda = pipeline.ejecutar(
            self.repository, etapas=("paso5",), db_path=self.db_path
        )
        corrida_2 = segunda["etapas"]["paso5"]["corrida"]
        self.assertNotEqual(corrida_1, corrida_2)
        filas = self._match()
        self.assertEqual(len(filas), 2)
        validas = [f for f in filas if f["valida"] == 1]
        self.assertEqual(len(validas), 1)
        self.assertEqual(validas[0]["corrida_id"], corrida_2)

    def test_evidencia_genera_y_verifica(self):
        self._job()
        resultado = pipeline.ejecutar(
            self.repository,
            etapas=("analisis", "paso5", "evidencia"),
            db_path=self.db_path,
            docs_dir=self.docs,
        )
        etapa = resultado["etapas"]["evidencia"]
        self.assertTrue(etapa["ok"], etapa.get("fallos"))
        documento = Path(etapa["documento"])
        self.assertTrue(documento.is_file())
        # El documento es el de la corrida vigente y cita el aviso.
        self.assertIn(etapa["corrida"], documento.read_text(encoding="utf-8"))


class TestParidad(Base):
    """Criterio 2.1: la UI y la CLI dan el MISMO estado de `job_match`."""

    def test_dos_corridas_dan_el_mismo_estado(self):
        self._job("job-1")
        self._job("job-2", title="Data Analyst")
        self._campos("job-1", skills=json.dumps(["Python"]))

        pipeline.ejecutar(
            self.repository,
            etapas=("analisis", "reanalisis", "paso5"),
            db_path=self.db_path,
        )
        primero = {
            f["job_id"]: (f["estado"], f["motivo"])
            for f in self._match()
            if f["valida"] == 1
        }

        pipeline.ejecutar(
            self.repository,
            etapas=("analisis", "reanalisis", "paso5"),
            db_path=self.db_path,
        )
        segundo = {
            f["job_id"]: (f["estado"], f["motivo"])
            for f in self._match()
            if f["valida"] == 1
        }

        self.assertEqual(primero, segundo)
        self.assertEqual(len(primero), 2)

    def test_el_reanalisis_no_inventa_requisitos_fantasma(self):
        """Sin campos estructurados no hay requisitos `source_field`."""
        self._job()
        pipeline.ejecutar(
            self.repository, etapas=("analisis", "reanalisis"), db_path=self.db_path
        )
        origenes = {r["origin"] for r in self._requisitos("job-1")}
        self.assertNotIn("source_field", origenes)

    def test_el_camino_de_la_ui_y_el_de_la_cli_dan_el_mismo_estado(self):
        """Criterio 2.1: UI y CLI → el MISMO estado de `job_match`.

        Camino UI: el orquestador (``pipeline.ejecutar``).
        Camino CLI: las etapas sueltas, como las haría un script.
        Se comparan sobre DOS bases idénticas (copia de la misma semilla).
        """
        import shutil
        import sqlite3

        from jobpulse_v15 import matching
        from jobpulse_v15.analysis_flow import reananalizar_con_campos_fuente

        self._job("job-1")
        self._job("job-2", title="Data Analyst")
        self._campos("job-1", skills=json.dumps(["Python"]))

        semilla = self.db_path
        ui_db = self.raiz / "ui.db"
        cli_db = self.raiz / "cli.db"
        shutil.copy2(semilla, ui_db)
        shutil.copy2(semilla, cli_db)

        # -- camino UI: el orquestador
        ui_repo = Repository(Database(ui_db))
        pipeline.ejecutar(
            ui_repo,
            etapas=("analisis", "reanalisis", "paso5"),
            db_path=ui_db,
        )

        # -- camino CLI: las etapas sueltas (lo que haría un script)
        cli_repo = Repository(Database(cli_db))
        for job in cli_repo.search_jobs(review_reason="analysis_missing", limit=100):
            extract_job_analysis(cli_repo, str(job["job_id"]))
        reananalizar_con_campos_fuente(cli_repo)
        conexion = sqlite3.connect(str(cli_db))
        conexion.row_factory = sqlite3.Row
        try:
            matching.ejecutar_paso5(conexion)
        finally:
            conexion.close()

        def _estados(ruta):
            conexion = sqlite3.connect(str(ruta))
            conexion.row_factory = sqlite3.Row
            try:
                return {
                    fila["job_id"]: (fila["estado"], fila["motivo"])
                    for fila in conexion.execute(
                        "SELECT job_id, estado, motivo FROM job_match "
                        "WHERE valida = 1"
                    )
                }
            finally:
                conexion.close()

        self.assertEqual(_estados(ui_db), _estados(cli_db))
        self.assertEqual(len(_estados(ui_db)), 2)


if __name__ == "__main__":
    unittest.main()
