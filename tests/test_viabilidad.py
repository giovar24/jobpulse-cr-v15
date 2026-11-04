# -*- coding: utf-8 -*-
"""Tests del motor de VIABILIDAD (ajuste tecnico del perfil con el aviso).

Regla que el modulo respeta (y estos tests fijan): el score NO se entrena
con resultados de postulacion (un rechazo humano no dice si el perfil califica
o no); es deterministico y auditable.
"""
import contextlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import areas  # noqa: E402
from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.matching import EvaluadorPaso5  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402
from jobpulse_v15.viabilidad import (  # noqa: E402
    BANDA_APLICAR,
    BANDA_NO_PRIORITARIO,
    BANDA_REVISAR,
    BANDA_SIN_DATOS,
    BANDA_VETO,
    MOTIVO_OBLIGATORIO_FALTANTE,
    MOTIVO_VETO_AREA,
    MOTIVO_VETO_EDUCACION,
    evaluar_viabilidad,
    evaluar_viabilidades,
    resumen_bandas,
)


def requisito(category, value_code, value_text, level="required", **extra):
    base = {
        "category": category,
        "value_code": value_code,
        "value_text": value_text,
        "requirement_level": level,
        "evidence": extra.pop("evidence", f"{value_text} required."),
        "origin": "rule",
        "confidence": 0.9,
    }
    base.update(extra)
    return base


class TestViabilidad(unittest.TestCase):
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
        # Taxonomia de areas (la siembran `init-areas`, no las migraciones):
        # sin ella las ofertas no se clasifican al guardarse.
        with self.database.connection() as connection:
            areas.sembrar_taxonomia(connection)
        # Perfil: excel, sql, ingles B2, bachillerato (secundaria).
        self.repository.save_candidate_profile_fact("skill", "excel", "Excel")
        self.repository.save_candidate_profile_fact("skill", "sql", "SQL")
        self.repository.save_candidate_profile_fact(
            "language", "ingles", "Ingles", qualifier="B2"
        )
        self.repository.save_candidate_profile_fact(
            "education",
            "bachillerato",
            "Bachiller en Educacion Media",
            education_status="completed",
        )
        # La conexion debe VIVIR mientras se use el evaluador (carga el
        # perfil, los requisitos y los textos al construirse).
        self._stack = contextlib.ExitStack()
        self.connection = self._stack.enter_context(self.database.connection())

    def tearDown(self):
        # Cerrar la conexion ANTES de borrar el temporal (Windows no deja
        # borrar un archivo abierto).
        self._stack.close()
        self.temp_dir.cleanup()

    def _job(self, job_id, title="Support Engineer", description=""):
        self.repository.save_job(
            {
                "job_id": job_id,
                "title": title,
                "company": "Example",
                "country": "CR",
                "city": "San Jose",
                "posting_language": "en",
                "description_raw": description,
            },
            site_id="sitio-1",
            source_job_id=job_id,
        )
        return job_id

    def _analisis(self, job_id, requirements, **kwargs):
        # `field_statuses` debe ser coherente con los requisitos (el
        # repositorio rechaza un campo 'found' sin requisitos guardados).
        categorias = {req["category"] for req in requirements}
        default_status = {categoria: "found" for categoria in sorted(categorias)}
        self.repository.save_analysis(
            job_id,
            text_hash=f"hash-{job_id}-{len(requirements)}",
            extractor_version="rules-1",
            analysis_status=kwargs.pop("analysis_status", "complete"),
            field_statuses=kwargs.pop("field_statuses", default_status),
            requirements=requirements,
            **kwargs,
        )

    def _evaluar(self, job_id, **kwargs):
        # Evaluador NUEVO por evaluacion: carga requisitos/textos al
        # construirse, asi que debe ver los datos recien guardados.
        return evaluar_viabilidad(EvaluadorPaso5(self.connection), job_id, **kwargs)

    # ------------------------------------------------------------------ veto
    def test_veto_educativo_cuando_el_titulo_universitario_es_obligatorio(self):
        job_id = self._job(
            "job-bachelor",
            description="Required Qualifications: Bachelor's degree in Computer Science.",
        )
        self._analisis(
            job_id,
            [
                requisito(
                    "education",
                    "bachelor",
                    "Bachelor's degree",
                    evidence="Required Qualifications: Bachelor's degree in Computer Science.",
                )
            ],
        )

        v = self._evaluar(job_id)

        self.assertEqual(v.banda, BANDA_VETO)
        self.assertEqual(v.veto, MOTIVO_VETO_EDUCACION)

    def test_veto_de_area(self):
        self.repository.save_candidate_profile_fact(
            "area", "informatica", "Informatica"
        )
        job_id = self._job("job-cocinero", title="Chef de Cocina")
        self._analisis(job_id, [requisito("skill", "excel", "Excel")])

        v = self._evaluar(job_id)

        self.assertEqual(v.banda, BANDA_VETO)
        self.assertEqual(v.veto, MOTIVO_VETO_AREA)

    # --------------------------------------------------------------- bandas
    def test_todo_cubierto_va_a_aplicar(self):
        job_id = self._job("job-ok")
        self._analisis(
            job_id,
            [
                requisito("skill", "excel", "Excel"),
                requisito("skill", "sql", "SQL"),
                requisito("language", "ingles", "English"),
            ],
        )

        v = self._evaluar(job_id)

        self.assertEqual(v.banda, BANDA_APLICAR)
        self.assertGreaterEqual(v.ajuste, 85.0)
        self.assertEqual(v.cobertura_obligatorios, 1.0)

    def test_un_obligatorio_faltante_impide_aplicar(self):
        job_id = self._job("job-python")
        self._analisis(
            job_id,
            [
                requisito("skill", "excel", "Excel"),
                requisito("skill", "sql", "SQL"),
                requisito("skill", "python", "Python"),
            ],
        )

        v = self._evaluar(job_id)

        self.assertEqual(v.banda, BANDA_REVISAR)
        self.assertIn(MOTIVO_OBLIGATORIO_FALTANTE, v.motivos)
        self.assertEqual(v.faltantes_obligatorios, ["skill:python"])

    def test_un_preferred_faltante_no_bloquea(self):
        job_id = self._job("job-preferred")
        self._analisis(
            job_id,
            [
                requisito("skill", "excel", "Excel"),
                requisito("skill", "sql", "SQL"),
                requisito("skill", "python", "Python", level="preferred"),
            ],
        )

        v = self._evaluar(job_id)

        self.assertEqual(v.banda, BANDA_APLICAR)
        self.assertEqual(v.faltantes_obligatorios, [])

    def test_sin_requisitos_no_evaluable(self):
        job_id = self._job("job-vacio")
        self._analisis(job_id, [])

        v = self._evaluar(job_id)

        self.assertEqual(v.banda, BANDA_SIN_DATOS)

    def test_una_licencia_no_comparable_no_penaliza(self):
        job_id = self._job("job-licencia")
        self._analisis(
            job_id,
            [
                requisito("skill", "excel", "Excel"),
                requisito("license", "b2", "Licencia B2"),
            ],
        )

        v = self._evaluar(job_id)

        # La licencia queda pendiente, no resta: el ajuste sigue en 'aplicar'.
        self.assertEqual(v.banda, BANDA_APLICAR)
        licencias = [d for d in v.desglose if d.category == "license"]
        self.assertEqual(len(licencias), 1)
        self.assertEqual(licencias[0].estado, "no_verificable")

    # ------------------------------------------------------------- puntaje
    def test_un_requisito_faltante_baja_el_ajuste(self):
        job_cubierto = self._job("job-cubierto")
        self._analisis(
            job_cubierto,
            [
                requisito("skill", "excel", "Excel"),
                requisito("skill", "sql", "SQL"),
            ],
        )
        job_parcial = self._job("job-parcial")
        self._analisis(
            job_parcial,
            [
                requisito("skill", "excel", "Excel"),
                requisito("skill", "python", "Python"),
            ],
        )

        v_cubierto = self._evaluar(job_cubierto)
        v_parcial = self._evaluar(job_parcial)

        self.assertGreater(v_cubierto.ajuste, v_parcial.ajuste)
        self.assertEqual(v_cubierto.ajuste, 100.0)

    def test_sin_semantica_el_peso_se_redistribuye(self):
        job_id = self._job("job-sem")
        self._analisis(
            job_id,
            [
                requisito("skill", "excel", "Excel"),
                requisito("skill", "sql", "SQL"),
            ],
        )

        sin_semantica = self._evaluar(job_id)
        con_semantica = self._evaluar(job_id, semantica=90.0)
        con_semantica_alta = self._evaluar(job_id, semantica=100.0)

        # Sin semantica NO se penaliza: el peso se redistribuye y el aviso
        # totalmente cubierto queda en 100.
        self.assertEqual(sin_semantica.ajuste, 100.0)
        # La semantica es un componente mas: sube o baja segun su valor.
        self.assertLess(con_semantica.ajuste, sin_semantica.ajuste)
        self.assertGreater(con_semantica_alta.ajuste, con_semantica.ajuste)

    def test_la_semantica_no_sube_de_banda_a_un_con_faltante(self):
        job_id = self._job("job-sem-falta")
        self._analisis(
            job_id,
            [
                requisito("skill", "excel", "Excel"),
                requisito("skill", "python", "Python"),
            ],
        )

        v = self._evaluar(job_id, semantica=100.0)

        self.assertEqual(v.banda, BANDA_REVISAR)

    # --------------------------------------------------------------- orden
    def test_ordena_por_banda_y_ajuste(self):
        ids = []
        for nombre, requisitos in (
            # Falta un obligatorio -> banda 'revisar'.
            (
                "job-a",
                [
                    requisito("skill", "excel", "Excel"),
                    requisito("skill", "python", "Python"),
                ],
            ),
            # Todo cubierto -> banda 'aplicar'.
            (
                "job-b",
                [
                    requisito("skill", "excel", "Excel"),
                    requisito("skill", "sql", "SQL"),
                    requisito("language", "ingles", "English"),
                ],
            ),
        ):
            ids.append(self._job(nombre))
            self._analisis(nombre, requisitos)

        viabilidades = evaluar_viabilidades(EvaluadorPaso5(self.connection), ids)

        self.assertEqual(viabilidades[0].job_id, "job-b")
        self.assertEqual(viabilidades[0].banda, BANDA_APLICAR)
        self.assertEqual(viabilidades[-1].job_id, "job-a")
        self.assertEqual(viabilidades[-1].banda, BANDA_REVISAR)

    def test_resumen_de_bandas(self):
        job_id = self._job("job-ok")
        self._analisis(job_id, [requisito("skill", "excel", "Excel")])

        conteo = resumen_bandas([self._evaluar(job_id)])

        self.assertEqual(conteo[BANDA_APLICAR], 1)
        self.assertEqual(conteo[BANDA_NO_PRIORITARIO], 0)


if __name__ == "__main__":
    unittest.main()
