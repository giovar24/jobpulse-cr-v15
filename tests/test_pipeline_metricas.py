# -*- coding: utf-8 -*-
"""METRICAS POR ETAPA DEL PIPELINE (Ola 4.3).

El pipeline encadena siete etapas y cada una devuelve contadores propios, en
formatos distintos. Sin un registro comparable no se puede responder a la
pregunta que importa: "de TODOS los avisos que entraron, cuantos llegaron al
Paso 5, cuantos tenian requisitos y en que etapa se perdieron".

`jobpulse_v15.pipeline_metricas` traduce el resultado de cada etapa a tres
numeros COMPARABLES (avisos / requisitos / errores) y los guarda en
`pipeline_etapa` (migracion 024).

REGLAS DURAS que estos tests fijan:

1. la instrumentacion es **aditiva**: no borra ni funde datos;
2. una metrica que falla NO rompe el pipeline (eso lo prueba `test_pipeline`);
3. los contadores de cada etapa son los que el motor realmente produce (no
   inventados): `requisitos_guardados`, `requisitos_evaluados`, etc.;
4. el `corrida_id` del pipeline es DISTINTO del `corrida_id` del Paso 5
   (el del `job_match`), y eso se guarda en el detalle de la etapa `paso5`.
"""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import pipeline_metricas  # noqa: E402
from jobpulse_v15.db import Database  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.database = Database(self.db_path)
        self.database.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _registrar(self, etapa, resultado, *, corrida_id="pipe_test", ok=True):
        ahora = datetime.now()
        return pipeline_metricas.registrar_etapa(
            self.database,
            corrida_id=corrida_id,
            etapa=etapa,
            ok=ok,
            duracion_ms=123,
            resultado=resultado,
            iniciado_en=ahora,
            terminado_en=ahora,
        )


class TestCorridaId(Base):
    def test_el_id_del_pipeline_tiene_prefijo_propio(self):
        """Distingue la EJECUCION del pipeline del `corrida_id` del Paso 5."""
        corrida = pipeline_metricas.nuevo_corrida_id(self.database)
        self.assertTrue(corrida.startswith("pipe_"))
        self.assertNotEqual(corrida[:5], "2026")

    def test_dos_corridas_en_el_mismo_segundo_son_distintas(self):
        ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
        with self.database.connection() as connection:
            connection.execute(
                "INSERT INTO pipeline_etapa ("
                " corrida_id, etapa, ok, duracion_ms, avisos, requisitos,"
                " errores, detalle_json, iniciado_en, terminado_en"
                ") VALUES (?, 'analisis', 1, 0, 0, 0, 0, NULL, ?, ?)",
                (
                    "pipe_%s" % ahora,
                    "2026-11-06T10:00:00",
                    "2026-11-06T10:00:01",
                ),
            )
        corrida = pipeline_metricas.nuevo_corrida_id(self.database)
        self.assertNotEqual(corrida, "pipe_%s" % ahora)


class TestContadores(Base):
    def test_analisis(self):
        contadores = pipeline_metricas.contadores_etapa(
            "analisis",
            {"analizados": 12, "requisitos_guardados": 40, "fallos": 2},
        )
        self.assertEqual(
            contadores, {"avisos": 12, "requisitos": 40, "errores": 2}
        )

    def test_scrape(self):
        contadores = pipeline_metricas.contadores_etapa(
            "scrape",
            {
                "jobs_found": 30,
                "jobs_new": 20,
                "errores": 1,
                "sitios": 3,
                "sitios_ok": 2,
            },
        )
        self.assertEqual(
            contadores, {"avisos": 30, "requisitos": 0, "errores": 1}
        )

    def test_ia_suma_los_ciclos_y_el_pase_completo(self):
        contadores = pipeline_metricas.contadores_etapa(
            "ia",
            {
                "stats_ia": {
                    "ciclos": [{"enriched": 5, "failed": 1}],
                    "completo": {"enriched": 3, "failed": 0},
                }
            },
        )
        self.assertEqual(
            contadores, {"avisos": 8, "requisitos": 0, "errores": 1}
        )

    def test_reanalisis_suma_los_dos_motivos(self):
        contadores = pipeline_metricas.contadores_etapa(
            "reanalisis",
            {
                "reanalizados": 4,
                "requisitos_fuente": 11,
                "errores": 0,
                "texto_reanalizados": 2,
                "texto_errores": 1,
            },
        )
        self.assertEqual(
            contadores, {"avisos": 6, "requisitos": 11, "errores": 1}
        )

    def test_paso5(self):
        contadores = pipeline_metricas.contadores_etapa(
            "paso5", {"evaluadas": 50, "requisitos_evaluados": 210}
        )
        self.assertEqual(
            contadores, {"avisos": 50, "requisitos": 210, "errores": 0}
        )

    def test_evidencia_cuenta_los_fallos_que_son_lista(self):
        contadores = pipeline_metricas.contadores_etapa(
            "evidencia",
            {"descartadas": 3, "no_confirmadas": 31, "fallos": ["a", "b"]},
        )
        self.assertEqual(
            contadores, {"avisos": 34, "requisitos": 0, "errores": 2}
        )

    def test_evidencia_cuenta_los_avisos_documentados(self):
        """Los avisos de la evidencia son los MISMOS que evaluó el Paso 5."""
        contadores = pipeline_metricas.contadores_etapa(
            "evidencia",
            {
                "documentados": 705,
                "descartadas": 96,
                "no_confirmadas": 31,
                "fallos": [],
            },
        )
        self.assertEqual(
            contadores, {"avisos": 705, "requisitos": 0, "errores": 0}
        )

    def test_backfill(self):
        contadores = pipeline_metricas.contadores_etapa(
            "backfill", {"actualizados": 7, "sin_codigo": 9}
        )
        self.assertEqual(
            contadores, {"avisos": 0, "requisitos": 7, "errores": 0}
        )

    def test_una_etapa_desconocida_no_inventa_numeros(self):
        contadores = pipeline_metricas.contadores_etapa("inventada", {"avisos": 99})
        self.assertEqual(
            contadores, {"avisos": 0, "requisitos": 0, "errores": 0}
        )

    def test_un_resultado_vacio_no_rompe(self):
        contadores = pipeline_metricas.contadores_etapa("analisis", {})
        self.assertEqual(
            contadores, {"avisos": 0, "requisitos": 0, "errores": 0}
        )


class TestDetalle(Base):
    def test_el_detalle_keeps_los_contadores_propios(self):
        detalle = pipeline_metricas.detalle_etapa(
            "paso5",
            {
                "corrida": "20261106_182554",
                "evaluadas": 705,
                "requisitos_evaluados": 2857,
                "por_estado": {"calificada": 190},
            },
        )
        self.assertEqual(detalle["corrida"], "20261106_182554")
        self.assertEqual(detalle["evaluadas"], 705)
        self.assertEqual(detalle["requisitos_evaluados"], 2857)
        self.assertEqual(detalle["por_estado"], {"calificada": 190})

    def test_el_detalle_del_reanalisis_incluye_los_dos_motivos(self):
        detalle = pipeline_metricas.detalle_etapa(
            "reanalisis",
            {
                "candidatos": 3,
                "reanalizados": 2,
                "sin_cambio": 1,
                "requisitos_fuente": 8,
                "texto_candidatos": 1,
                "texto_reanalizados": 1,
                "texto_errores": 0,
            },
        )
        self.assertEqual(detalle["candidatos"], 3)
        self.assertEqual(detalle["sin_cambio"], 1)
        self.assertEqual(detalle["texto_reanalizados"], 1)
        self.assertEqual(detalle["texto_errores"], 0)


class TestRegistro(Base):
    def test_registrar_guarda_la_fila(self):
        self._registrar(
            "analisis", {"analizados": 3, "requisitos_guardados": 7, "fallos": 0}
        )
        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT * FROM pipeline_etapa"
            ).fetchone()
        self.assertEqual(fila["corrida_id"], "pipe_test")
        self.assertEqual(fila["etapa"], "analisis")
        self.assertEqual(fila["ok"], 1)
        self.assertEqual(fila["duracion_ms"], 123)
        self.assertEqual(fila["avisos"], 3)
        self.assertEqual(fila["requisitos"], 7)
        self.assertEqual(fila["errores"], 0)
        self.assertIsInstance(json.loads(fila["detalle_json"]), dict)

    def test_una_etapa_fallada_guarda_el_error(self):
        self._registrar(
            "ia",
            {"ok": False, "estado": "error", "error": "TimeoutError: tardo"},
            ok=False,
        )
        with self.database.connection() as connection:
            fila = connection.execute("SELECT * FROM pipeline_etapa").fetchone()
        self.assertEqual(fila["ok"], 0)
        self.assertIn("TimeoutError", fila["detalle_json"])

    def test_consultar_corrida_devuelve_las_etapas_en_orden(self):
        self._registrar("analisis", {"analizados": 1}, corrida_id="pipe_a")
        self._registrar("paso5", {"evaluadas": 1}, corrida_id="pipe_a")
        with self.database.connection() as connection:
            corrida = pipeline_metricas.consultar_corrida(connection, "pipe_a")
        self.assertIsNotNone(corrida)
        self.assertEqual(
            [e["etapa"] for e in corrida["etapas"]], ["analisis", "paso5"]
        )
        self.assertTrue(corrida["ok"])
        self.assertEqual(corrida["duracion_ms"], 246)

    def test_consultar_corrida_de_una_corrida_inexistente(self):
        with self.database.connection() as connection:
            self.assertIsNone(
                pipeline_metricas.consultar_corrida(connection, "pipe_no_existe")
            )

    def test_consultar_corridas_devuelve_las_ultimas(self):
        self._registrar("analisis", {"analizados": 1}, corrida_id="pipe_1")
        self._registrar("analisis", {"analizados": 2}, corrida_id="pipe_2")
        self._registrar("analisis", {"analizados": 3}, corrida_id="pipe_3")
        with self.database.connection() as connection:
            corridas = pipeline_metricas.consultar_corridas(connection, limite=2)
        self.assertEqual(len(corridas), 2)
        # La mas reciente primero.
        self.assertEqual(corridas[0]["corrida_id"], "pipe_3")
        self.assertEqual(corridas[1]["corrida_id"], "pipe_2")

    def test_el_resumen_de_una_linea(self):
        self._registrar("analisis", {"analizados": 3, "requisitos_guardados": 7})
        with self.database.connection() as connection:
            corrida = pipeline_metricas.consultar_corrida(connection, "pipe_test")
        linea = pipeline_metricas.resumen_linea(corrida)
        self.assertIn("pipe_test", linea)
        self.assertIn("analisis=ok", linea)
        self.assertIn("123ms", linea)


class TestResumenEnMemoria(Base):
    """La linea de metricas que muestran la UI v2 y `run_full_flow.py`."""

    def test_una_sola_implementacion_para_todos(self):
        linea = pipeline_metricas.resumen_linea_etapas(
            {
                "etapas": {
                    "analisis": {"analizados": 2, "requisitos_guardados": 5},
                    "paso5": {"evaluadas": 705, "requisitos_evaluados": 2866},
                }
            }
        )
        self.assertIn("MÉTRICAS:", linea)
        self.assertIn("analisis: 2 av · 5 rq · 0 err", linea)
        self.assertIn("paso5: 705 av · 2866 rq · 0 err", linea)

    def test_sin_etapas_no_devuelve_linea(self):
        self.assertEqual(pipeline_metricas.resumen_linea_etapas({}), "")
        self.assertEqual(pipeline_metricas.resumen_linea_etapas({"etapas": {}}), "")

    def test_las_etapas_siguen_el_orden_del_pipeline(self):
        self.assertEqual(
            pipeline_metricas.ETAPAS,
            ("scrape", "analisis", "ia", "reanalisis", "backfill", "paso5",
             "evidencia"),
        )


class TestEsquema(Base):
    def test_asegurar_esquema_avisa_cuando_migra(self):
        base = Database(self.db_path)
        avisos = []
        version = pipeline_metricas.asegurar_esquema(base, avisos.append)
        self.assertEqual(version, 24)
        # Ya estaba migrada: no avisa.
        self.assertEqual(avisos, [])

    def test_asegurar_esquema_migra_una_base_vieja(self):
        """Una base en esquema 23 recibe la 024 al abrirla (convencion)."""
        viejo = Path(self.temp_dir.name) / "viejo.db"
        shutil.copy2(self.db_path, viejo)
        # Simula una base anterior a la 024.
        with Database(viejo).connection() as connection:
            connection.execute("DROP TABLE pipeline_etapa")
            connection.execute("PRAGMA user_version = 23")

        avisos = []
        version = pipeline_metricas.asegurar_esquema(Database(viejo), avisos.append)
        self.assertEqual(version, 24)
        self.assertTrue(avisos)
        self.assertIn("24", avisos[0])


if __name__ == "__main__":
    unittest.main()
