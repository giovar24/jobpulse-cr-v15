# -*- coding: utf-8 -*-
"""Evidencia del Paso 5 como MODULO (O12 · Ola 1.4).

Antes la logica vivia en dos scripts de la raiz, solo ejecutables por CLI y por
subprocess. Ahora vive en ``jobpulse_v15.evidencia`` y los scripts son
envoltorios: la UI puede generar y verificar la evidencia **sin subprocess**.

REGLAS DURAS que estos tests fijan:

1. el nombre del documento lo decide la corrida VIGENTE, no una fecha fija
   (una corrida nueva no pisa el documento de otro dia);
2. "al dia" = existe un documento que declara la corrida vigente;
3. la verificacion exige que la frase citada sea LITERAL del texto de la BD;
4. la muestra historica de 43 casos (``MEDICION``) se conserva aunque los
   avisos ya no esten en la BD (se listan como `purgado`).
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import evidencia, matching  # noqa: E402
from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402

TEXTO = (
    "Requisitos del puesto.\n"
    "Required Qualifications: Bachelor's degree in Computer Science is required.\n"
    "We offer a competitive salary."
)


class TestUtilidades(unittest.TestCase):
    def test_fecha_de_corrida(self):
        self.assertEqual(evidencia.fecha_de_corrida("20261104_231932"), "2026-11-04")

    def test_fecha_de_corrida_sin_formato(self):
        self.assertEqual(evidencia.fecha_de_corrida("nada"), "sin-fecha")
        self.assertEqual(evidencia.fecha_de_corrida(None), "sin-fecha")

    def test_docs_dir_para(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "data").mkdir()
            (raiz / "docs").mkdir()
            self.assertEqual(
                evidencia.docs_dir_para(raiz / "data" / "x.db"), raiz / "docs"
            )

    def test_docs_dir_para_una_copia_no_toca_el_repo(self):
        """Una copia en otra carpeta escribe su evidencia junto a ella."""
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            copia = raiz / "copia.db"
            copia.write_bytes(b"")
            self.assertEqual(evidencia.docs_dir_para(copia), raiz / "docs")

    def test_corrida_de_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "doc.md"
            ruta.write_text(
                "# Paso 5 — Evidencia (corrida `20261104_231932`)\n", encoding="utf-8"
            )
            self.assertEqual(evidencia.corrida_de_doc(ruta), "20261104_231932")

    def test_corrida_de_doc_sin_el_patron(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "doc.md"
            ruta.write_text("# otra cosa\n", encoding="utf-8")
            self.assertIsNone(evidencia.corrida_de_doc(ruta))
            self.assertIsNone(evidencia.corrida_de_doc(Path(tmp) / "no-existe.md"))


class Base(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temp_dir.name)
        self.db_path = self.raiz / "data" / "jobpulse_v15.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.database = Database(self.db_path)
        self.database.initialize()
        self.repository = Repository(self.database)
        self.docs = self.raiz / "docs"
        self.docs.mkdir()
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "sitio", "workday", "Sitio", "https://example.test/jobs"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _job(self, job_id="job-1"):
        self.repository.save_job(
            {
                "job_id": job_id,
                "title": "Support Engineer",
                "company": "Example",
                "country": "CR",
                "posting_language": "en",
                "description_raw": TEXTO,
            },
            site_id="sitio",
            source_job_id=job_id,
        )
        return job_id

    def _corrida(self, corrida_id, job_id=None, estado="descartada", motivo="x",
                 valida=1):
        with self.database.connection() as connection:
            connection.execute(
                "INSERT INTO job_match (job_id, corrida_id, estado, motivo, valida) "
                "VALUES (?, ?, ?, ?, ?)",
                (job_id, corrida_id, estado, motivo, valida),
            )


class TestGenerar(Base):
    def test_genera_el_documento_de_la_corrida_vigente(self):
        job_id = self._job()
        self._corrida("20261104_231932", job_id)

        resultado = evidencia.generar_evidencia(
            db_path=self.db_path, docs_dir=self.docs, log=lambda _t: None
        )

        self.assertEqual(resultado["ruta"], self.docs / "PASO5_EVIDENCIA_2026-11-04.md")
        self.assertEqual(resultado["corrida"], "20261104_231932")
        self.assertEqual(resultado["descartadas"], 1)
        self.assertEqual(resultado["no_confirmadas"], 0)
        contenido = resultado["ruta"].read_text(encoding="utf-8")
        self.assertIn(job_id, contenido)
        self.assertIn("Documento GENERADO", contenido)

    def test_una_fila_no_valida_no_es_la_corrida_vigente(self):
        job_id = self._job()
        self._corrida("20261101_000000", job_id, valida=0)

        with self.assertRaises(ValueError):
            evidencia.generar_evidencia(
                db_path=self.db_path, docs_dir=self.docs, log=lambda _t: None
            )

    def test_salida_explicita(self):
        job_id = self._job()
        self._corrida("20261104_231932", job_id)
        destino = self.raiz / "otro.md"

        resultado = evidencia.generar_evidencia(
            db_path=self.db_path, docs_dir=self.docs, salida=destino,
            log=lambda _t: None,
        )

        self.assertEqual(resultado["ruta"], destino)
        self.assertTrue(destino.is_file())

    def test_la_muestra_historica_se_conserva_aunque_los_avisos_no_esten(self):
        job_id = self._job()
        self._corrida("20261104_231932", job_id)

        resultado = evidencia.generar_evidencia(
            db_path=self.db_path, docs_dir=self.docs, log=lambda _t: None
        )

        contenido = resultado["ruta"].read_text(encoding="utf-8")
        # Los 43 casos de la medicion historica siguen listados (purgados).
        self.assertIn("Medición AMPLIADA de `educacion_no_cumple` (43 casos)", contenido)
        self.assertIn("`cinde-4901`", contenido)
        self.assertIn("purgado", contenido)


class TestVerificar(Base):
    def test_verifica_documento_generado(self):
        job_id = self._job()
        self._corrida("20261104_231932", job_id)
        generado = evidencia.generar_evidencia(
            db_path=self.db_path, docs_dir=self.docs, log=lambda _t: None
        )

        resultado = evidencia.verificar_evidencia(
            db_path=self.db_path, docs_dir=self.docs, doc=generado["ruta"],
            log=lambda _t: None,
        )

        self.assertTrue(resultado["ok"], resultado["fallos"])
        self.assertGreaterEqual(resultado["verificaciones"], 1)
        self.assertEqual(resultado["fallos"], [])

    def test_falla_si_la_frase_no_es_literal(self):
        job_id = self._job()
        self._corrida("20261104_231932", job_id)
        conf = matching.confirmar_requisito_universitario(TEXTO)
        self.assertTrue(conf.segmento, "el texto de prueba debe confirmar el titulo")
        # Documento falso: el job_id aparece, pero la frase del aviso no.
        falso = self.raiz / "falso.md"
        falso.write_text(
            "# Paso 5 — Evidencia del bloqueante educativo (corrida `20261104_231932`)\n"
            "\n### 1. `%s` — Support Engineer\n\n> frase inventada que no esta\n" % job_id,
            encoding="utf-8",
        )

        resultado = evidencia.verificar_evidencia(
            db_path=self.db_path, docs_dir=self.docs, doc=falso, log=lambda _t: None
        )

        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado["fallos"])

    def test_corrida_de_doc_sin_corrida_vigente(self):
        resultado = evidencia.verificar_evidencia(
            db_path=self.db_path, docs_dir=self.docs, log=lambda _t: None
        )
        self.assertFalse(resultado["ok"])
        self.assertIn("corrida vigente", resultado["fallos"][0])


class TestEstado(Base):
    def test_sin_corrida(self):
        estado = evidencia.estado_evidencia(
            db_path=self.db_path, docs_dir=self.docs
        )
        self.assertFalse(estado["al_dia"])
        self.assertIn("corrida vigente", estado["motivo"])

    def test_sin_documento(self):
        job_id = self._job()
        self._corrida("20261104_231932", job_id)

        estado = evidencia.estado_evidencia(
            db_path=self.db_path, docs_dir=self.docs
        )

        self.assertFalse(estado["al_dia"])
        self.assertIn("no existe documento", estado["motivo"])

    def test_documento_de_otra_corrida(self):
        job_id = self._job()
        self._corrida("20261104_231932", job_id)
        (self.docs / "PASO5_EVIDENCIA_2026-11-01.md").write_text(
            "# Evidencia (corrida `20261101_000000`)\n", encoding="utf-8"
        )

        estado = evidencia.estado_evidencia(
            db_path=self.db_path, docs_dir=self.docs
        )

        self.assertFalse(estado["al_dia"])
        self.assertIn("no corresponde", estado["motivo"])

    def test_al_dia_y_verificado(self):
        job_id = self._job()
        self._corrida("20261104_231932", job_id)
        evidencia.generar_evidencia(
            db_path=self.db_path, docs_dir=self.docs, log=lambda _t: None
        )

        estado = evidencia.estado_evidencia(
            db_path=self.db_path, docs_dir=self.docs, verificar=True
        )

        self.assertTrue(estado["al_dia"], estado["motivo"])
        self.assertGreaterEqual(estado["verificaciones"], 1)

    def test_doc_por_defecto_elige_el_de_la_corrida_vigente(self):
        job_id = self._job()
        self._corrida("20261104_231932", job_id)
        # Un documento VIEJO con el nombre mas alto no debe ganar: se elige por
        # la corrida declarada en la primera linea, no por el nombre.
        viejo = self.docs / "PASO5_EVIDENCIA_2026-11-01.md"
        viejo.write_text(
            "# Evidencia (corrida `20261101_000000`)\n", encoding="utf-8"
        )
        generado = evidencia.generar_evidencia(
            db_path=self.db_path, docs_dir=self.docs, log=lambda _t: None
        )

        elegido = evidencia.doc_por_defecto(
            db_path=self.db_path, docs_dir=self.docs
        )

        self.assertEqual(elegido, generado["ruta"])

    def test_doc_por_defecto_sin_candidatos(self):
        elegido = evidencia.doc_por_defecto(
            db_path=self.db_path, docs_dir=self.docs
        )
        self.assertEqual(elegido, self.docs / "PASO5_EVIDENCIA_2026-10-29.md")


if __name__ == "__main__":
    unittest.main()
