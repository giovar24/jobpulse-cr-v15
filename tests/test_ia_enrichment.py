# -*- coding: utf-8 -*-
"""Tests del enriquecimiento IA con cliente simulado (sin servidor real).

Cubren: reintentos por campo, preflight del servidor, pase critico,
pase completo (incluye jobs que solo necesitan campos secundarios) y
persistencia en BD.
"""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jobpulse_v15 import ia_enrichment as iae
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository


RESPUESTAS = {
    iae.LOCATION_PROMPT: {"city": "Heredia", "region": "Heredia"},
    iae.WORK_MODE_PROMPT: {"work_mode": "onsite"},
    iae.DATE_PROMPT: {"date_published": "2026-10-20"},
    iae.EMPLOYMENT_PROMPT: {"employment_type": "Full-time"},
    iae.SALARY_PROMPT: {
        "salary_min": 1000000, "salary_max": 1500000,
        "salary_currency": "CRC", "salary_period": "monthly",
    },
    iae.SKILLS_PROMPT: {"skills": ["SQL", "Active Directory"]},
    iae.LANGUAGES_PROMPT: {"languages": {"ingles": "B2"}},
}


class FakeIAClient:
    """Cliente IA simulado: responde segun el prompt del sistema."""

    base_url = "http://fake.test"
    modelo = "fake-model"

    def __init__(self, fallar=False):
        self.llamadas = 0
        self.fallar = fallar
        self.prompts_pedidos = []

    async def chat_json(self, messages, schema=None, temperature=0.0,
                        max_tokens=0):
        self.llamadas += 1
        if self.fallar:
            raise RuntimeError("servidor caido")
        system = messages[0]["content"]
        self.prompts_pedidos.append(system)
        return dict(RESPUESTAS.get(system, {"ok": True}))


class TestExtractField(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def test_extract_reintenta_3_veces_y_devuelve_none(self):
        cliente = FakeIAClient(fallar=True)
        resultado = self._run(iae._extract_field(
            cliente, iae.WORK_MODE_PROMPT, "texto", iae.WORK_MODE_SCHEMA,
            "work_mode",
        ))
        self.assertIsNone(resultado)
        self.assertEqual(cliente.llamadas, 3)

    def test_extract_devuelve_respuesta_del_esquema(self):
        cliente = FakeIAClient()
        resultado = self._run(iae._extract_field(
            cliente, iae.WORK_MODE_PROMPT, "texto", iae.WORK_MODE_SCHEMA,
            "work_mode",
        ))
        self.assertEqual(resultado, {"work_mode": "onsite"})
        self.assertEqual(cliente.llamadas, 1)


class TestNeedsEnrichment(unittest.TestCase):
    def test_critical(self):
        self.assertTrue(iae.needs_critical_enrichment(
            {"work_mode": "unknown", "date_published": "2026-01-01"}))
        self.assertTrue(iae.needs_critical_enrichment(
            {"work_mode": "onsite", "date_published": "",
             "location_raw": "San Jose", "city": None}))
        self.assertFalse(iae.needs_critical_enrichment(
            {"work_mode": "onsite", "date_published": "2026-01-01",
             "city": "Heredia"}))

    def test_secondary(self):
        self.assertTrue(iae.needs_secondary_enrichment({"skills": None}))
        self.assertTrue(iae.needs_secondary_enrichment(
            {"skills": ["SQL"], "languages": {}, "employment_type": None,
             "salary_raw": "1.000.000/mes", "salary_min": None}))
        self.assertFalse(iae.needs_secondary_enrichment({
            "skills": ["SQL"], "languages": {"ingles": "B2"},
            "employment_type": "Full-time", "salary_min": 1000000,
            "salary_raw": "x",
        }))


class TestPreflight(unittest.TestCase):
    def test_preflight_ok(self):
        error = asyncio.run(iae.verificar_servidor_ia(FakeIAClient()))
        self.assertIsNone(error)

    def test_preflight_falla_con_mensaje(self):
        error = asyncio.run(iae.verificar_servidor_ia(FakeIAClient(fallar=True)))
        self.assertIsNotNone(error)
        self.assertIn("no responde", error)


class TestRunIAEnrichment(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        self.database = Database(self.db_path)
        self.database.initialize()
        self.repo = Repository(self.database)
        self.repo.register_platform("test", "Test", "directos")
        self.repo.register_site(
            "test-site", "test", "Sitio test",
            "https://example.test/jobs", run_groups=("all",),
        )
        self._insert_job()
        self.cliente = FakeIAClient()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _insert_job(self, **overrides):
        job = {
            "job_id": "T-1",
            "title": "IT Support Specialist",
            "company": "Test Corp",
            "location_raw": "San Jose, Heredia",
            "work_mode": "unknown",
            "date_published": "2026-10-20",
            "description_raw": "Soporte IT con Active Directory y SQL.",
        }
        job.update(overrides)
        self.repo.save_job(
            job, site_id="test-site", source_job_id=job["job_id"],
            source_url="https://example.test/jobs/T-1",
        )

    def _run(self, modo="criticos", limit=50):
        only_critical = modo == "criticos"
        with patch.object(
            iae, "get_ia_client", return_value=self.cliente,
        ):
            return asyncio.run(iae.run_ia_enrichment(
                db_path=self.db_path, limit=limit,
                only_critical=only_critical,
            ))

    def test_pase_critico_enriquece_y_persiste(self):
        resultado = self._run()
        stats = resultado["stats"]
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["enriched"], 1)
        self.assertEqual(stats["failed"], 0)
        self.assertGreater(stats["fields_filled"]["work_mode"], 0)
        self.assertEqual(stats["fields_filled"]["city"], 1)

        job = self.repo.get_job("T-1")
        self.assertEqual(job["work_mode"], "onsite")
        self.assertEqual(job["city"], "Heredia")
        self.assertEqual(job["region"], "Heredia")

    def test_pase_critico_salta_job_completo(self):
        # Job ya completo con criticos: no entra al pase critico.
        self.repo.save_job(
            {
                "job_id": "T-2", "title": "Full Job",
                "city": "Heredia", "work_mode": "onsite",
                "date_published": "2026-10-21",
            },
            site_id="test-site", source_job_id="T-2",
            source_url="https://example.test/jobs/T-2",
        )
        resultado = self._run(limit=50)
        stats = resultado["stats"]
        self.assertEqual(stats["total"], 1)  # solo T-1
        self.assertEqual(stats["enriched"], 1)

    def test_pase_completo_incluye_secundarios(self):
        # Job con TODOS los criticos completos, sin skills/emp type.
        self.repo.save_job(
            {
                "job_id": "T-3", "title": "Full Job 2",
                "city": "Heredia", "work_mode": "onsite",
                "date_published": "2026-10-21",
                "description_raw": "Se requiere Python y AWS.",
            },
            site_id="test-site", source_job_id="T-3",
            source_url="https://example.test/jobs/T-3",
        )
        # Pase completo: T-1 (criticos) y T-3 (solo secundarios).
        resultado_full = self._run(modo="completo", limit=50)
        self.assertEqual(resultado_full["stats"]["total"], 2)
        self.assertEqual(resultado_full["stats"]["enriched"], 2)

        job3 = self.repo.get_job("T-3")
        skills3 = job3["skills"]
        if isinstance(skills3, str):
            import json as _json
            skills3 = _json.loads(skills3) if skills3 not in ("", "null") else None
        self.assertEqual(skills3, ["SQL", "Active Directory"])
        self.assertEqual(job3["employment_type"], "Full-time")

        # Despues del pase, el critico no tiene nada pendiente.
        resultado_crit = self._run(limit=50)
        self.assertEqual(resultado_crit["stats"]["total"], 0)

    def test_salary_completo_se_persiste(self):
        # Salary solo se pide si hay salary_raw: min+max+currency+period
        # deben aplicar TODOS (antes se perdian max/currency/period).
        self.repo.save_job(
            {
                "job_id": "T-4", "title": "Job con salario",
                "city": "Heredia", "work_mode": "onsite",
                "date_published": "2026-10-21",
                "salary_raw": "1 000 000 - 1 500 000 CRC/mes",
            },
            site_id="test-site", source_job_id="T-4",
            source_url="https://example.test/jobs/T-4",
        )
        # T-4 tiene los criticos completos: usa el pase completo.
        resultado = self._run(modo="completo", limit=50)
        self.assertEqual(resultado["stats"]["enriched"], 2)  # T-1 y T-4
        self.assertEqual(resultado["stats"]["fields_filled"]["salary"], 1)

        job = self.repo.get_job("T-4")
        self.assertEqual(job["salary_min"], 1000000)
        self.assertEqual(job["salary_max"], 1500000)
        self.assertEqual(job["salary_currency"], "CRC")
        self.assertEqual(job["salary_period"], "monthly")
        # skills/languages NO tocados: deben seguir vacios de verdad
        # (NULL/''), no la cadena basura 'null'.
        self.assertIn(job["skills"], (None, "", "[]"))

    def test_preflight_servidor_apagado_aborta_antes(self):
        self.cliente = FakeIAClient(fallar=True)
        resultado = self._run(limit=50)
        self.assertIn("error", resultado)
        self.assertIn("no responde", resultado["error"])
        # No toco la BD: el job sigue sin city.
        job = self.repo.get_job("T-1")
        self.assertIsNone(job["city"])


class TestPuertaSalario(unittest.TestCase):
    """El prompt de salario se dispara por el TEXTO, no por `salary_raw`.

    Bug corregido el 2026-11-01: la puerta exigia `salary_raw`, que las APIs
    de empleo casi nunca traen (0 de 354 avisos), y los 14 avisos que SI
    declaraban su compensacion nunca se procesaban.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        self.database = Database(self.db_path)
        self.database.initialize()
        self.repo = Repository(self.database)
        self.repo.register_platform("test", "Test", "directos")
        self.repo.register_site(
            "test-site", "test", "Sitio test",
            "https://example.test/jobs", run_groups=("all",),
        )
        self.cliente = FakeIAClient()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _job(self, job_id, description):
        self.repo.save_job(
            {
                "job_id": job_id, "title": "Puesto con compensacion",
                "company": "Test Corp", "country": "CR",
                "city": "Heredia", "region": "Heredia",
                "work_mode": "onsite", "date_published": "2026-10-21",
                "description_raw": description,
            },
            site_id="test-site", source_job_id=job_id,
            source_url=f"https://example.test/jobs/{job_id}",
        )

    def _run(self):
        with patch.object(iae, "get_ia_client", return_value=self.cliente):
            return asyncio.run(iae.run_ia_enrichment(
                db_path=self.db_path, limit=50, only_critical=False,
            ))

    def test_salario_por_texto_sin_salary_raw(self):
        self._job(
            "S-1",
            "Excelente puesto. Compensation: USD 1,400 - 1,600 per month "
            "for the selected candidate.",
        )
        self.assertEqual(self.repo.get_job("S-1")["salary_raw"], None)
        resultado = self._run()
        self.assertIn(iae.SALARY_PROMPT, self.cliente.prompts_pedidos)
        job = self.repo.get_job("S-1")
        self.assertEqual(job["salary_min"], 1000000)
        self.assertEqual(job["salary_currency"], "CRC")

    def test_sin_declaracion_no_se_pide_salario(self):
        self._job(
            "S-2",
            "We are a growing company with great benefits and a competitive "
            "package for the right candidate.",
        )
        self._run()
        self.assertNotIn(iae.SALARY_PROMPT, self.cliente.prompts_pedidos)

    def test_needs_secondary_detecta_el_salario_por_texto(self):
        self.assertTrue(iae.needs_secondary_enrichment({
            "skills": ["SQL"], "languages": {"ingles": "B2"},
            "employment_type": "Full-time",
            "salary_min": None, "salary_raw": None,
            "description_raw": "Compensation: USD 2,000 per month",
        }))


class TestCiudadDevueltaPorLaIA(unittest.TestCase):
    """La IA tambien devuelve basura: una planta no es una ciudad."""

    class _Cliente(FakeIAClient):
        async def chat_json(self, messages, schema=None, temperature=0.0,
                            max_tokens=0):
            self.llamadas += 1
            system = messages[0]["content"]
            self.prompts_pedidos.append(system)
            if system == iae.LOCATION_PROMPT:
                return {"city": "Dry Plant", "region": "Cartago"}
            return dict(RESPUESTAS.get(system, {"ok": True}))

    def test_ciudad_basura_no_se_guarda(self):
        job = {
            "job_id": "L-1", "title": "Assoc Sewer",
            "company": "Edwards", "country": "CR",
            "location_raw": "Costa Rica-Cartago-Dry Plant",
            "work_mode": "onsite", "date_published": "2026-10-21",
            "description_raw": "Applies sewing skills in a production plant.",
        }
        cliente = self._Cliente()
        filled = asyncio.run(iae.enrich_job_fields(job, cliente))
        self.assertNotIn("city", filled)
        # La region si es una provincia real del catalogo
        self.assertEqual(filled.get("region"), "Cartago")

    def test_ciudad_valida_si_se_guarda(self):
        job = {
            "job_id": "L-2", "title": "Puesto",
            "company": "Edwards", "country": "CR",
            "location_raw": "Grecia, Costa Rica",
            "work_mode": "onsite", "date_published": "2026-10-21",
            "description_raw": "Descripcion del puesto.",
        }

        class _Cliente(FakeIAClient):
            async def chat_json(self, messages, schema=None, temperature=0.0,
                                max_tokens=0):
                self.llamadas += 1
                system = messages[0]["content"]
                self.prompts_pedidos.append(system)
                if system == iae.LOCATION_PROMPT:
                    return {"city": "Grecia", "region": "Alajuela"}
                return dict(RESPUESTAS.get(system, {"ok": True}))

        filled = asyncio.run(iae.enrich_job_fields(job, _Cliente()))
        self.assertEqual(filled.get("city"), "Grecia")
        self.assertEqual(filled.get("region"), "Alajuela")


class TestPaseCompleto(unittest.TestCase):
    """O7.3: orquestación compartida CLI/UI (ciclos críticos + pase completo)."""

    def _run(self, coro):
        return asyncio.run(coro)

    @staticmethod
    def _stats(**kw):
        base = {"total": 0, "enriched": 0, "failed": 0, "skipped": 0, "fields_filled": {}}
        base.update(kw)
        return base

    def test_ciclos_y_pase_completo(self):
        llamadas = []

        async def fake_run(limit=50, only_critical=True):
            llamadas.append(("crit" if only_critical else "full", limit))
            if only_critical:
                if len([c for c in llamadas if c[0] == "crit"]) == 1:
                    return {"stats": self._stats(total=10, enriched=4, skipped=6,
                                                fields_filled={"city": 4})}
                return {"stats": self._stats()}
            return {"stats": self._stats(total=5, enriched=2, skipped=3,
                                         fields_filled={"skills": 2})}

        eventos = []
        with patch.object(iae, "run_ia_enrichment", fake_run), \
             patch.object(iae, "get_ia_client", lambda: FakeIAClient()), \
             patch.object(iae, "verificar_servidor_ia", self._verificar_ok):
            r = self._run(iae.pase_completo(on_event=eventos.append))
        self.assertEqual(len(r["ciclos"]), 2)  # 1 con trabajo + 1 vacío = stop
        self.assertEqual(r["completo"]["total"], 5)
        self.assertIn(("full", 2000), llamadas)
        self.assertIn(("crit", 500), llamadas)
        self.assertTrue(any("CR\u00cdTICO ciclo 1" in e for e in eventos))
        self.assertTrue(any("COMPLETO" in e for e in eventos))

    async def _verificar_ok(self, cliente):
        return None

    def test_solo_criticos_no_corre_pase_completo(self):
        llamadas = []

        async def fake_run(limit=50, only_critical=True):
            llamadas.append(("crit" if only_critical else "full", limit))
            if only_critical:
                return {"stats": self._stats()}
            raise AssertionError("el pase completo no debe correr con --solo-criticos")

        with patch.object(iae, "run_ia_enrichment", fake_run), \
             patch.object(iae, "get_ia_client", lambda: FakeIAClient()), \
             patch.object(iae, "verificar_servidor_ia", self._verificar_ok):
            r = self._run(iae.pase_completo(solo_criticos=True))
        self.assertIsNone(r["completo"])
        self.assertEqual([c[0] for c in llamadas], ["crit"])

    def test_sin_configuracion_error_claro(self):
        with patch.object(iae, "get_ia_client", lambda: None):
            r = self._run(iae.pase_completo())
        self.assertIn("error", r)
        self.assertIn("no configurada", r["error"])

    def test_error_del_pase_se_propaga_con_lo_acumulado(self):
        async def fake_run(limit=50, only_critical=True):
            if len([1]) == 1 and only_critical:
                # primer ciclo ok, segundo ciclo revienta
                if not getattr(fake_run, "_ya", False):
                    fake_run._ya = True
                    return {"stats": self._stats(total=3, enriched=1)}
                fake_run._ya = True
                return {"error": "servidor cayo"}
            raise AssertionError("no debe llegar al completo")

        with patch.object(iae, "run_ia_enrichment", fake_run), \
             patch.object(iae, "get_ia_client", lambda: FakeIAClient()), \
             patch.object(iae, "verificar_servidor_ia", self._verificar_ok):
            r = self._run(iae.pase_completo())
        self.assertIn("error", r)
        self.assertIn("servidor cayo", r["error"])
        self.assertEqual(len(r.get("ciclos", [])), 1)


class TestWorkModePorPatrones(unittest.TestCase):
    """Modalidad declarada de forma literal: se resuelve sin llamar a la IA."""

    detectar = staticmethod(iae.work_mode_por_patrones)

    # ── Etiquetas #LI- (declaracion del reclutador) ───────────────
    def test_etiquetas_li_de_linkedin(self):
        casos = {
            "#LI-Onsite Required Skills:": "onsite",
            "#LI-ONSITE Required Skills:": "onsite",
            "# R POCR #LI-ONSITE Required Skills:": "onsite",
            "#RPOCRA #LI-Onsite Required Skills:": "onsite",
            "#LI-Hybrid - Why You Should Join Us": "hybrid",
            "#LI-Remote -": "remote",
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(self.detectar(texto), esperado)

    # ── Frases que describen la modalidad del PUESTO ─────────────
    def test_frases_de_modalidad_del_puesto(self):
        casos = {
            "Ability to work in a hybrid work environment.": "hybrid",
            "Hybrid work arrangement requiring on-site presence.": "hybrid",
            "This is a hybrid position based in Ultra Park II.": "hybrid",
            "Modelo híbrido. Beneficios: seguro médico.": "hybrid",
            "Esquema híbrido de trabajo.": "hybrid",
            "employees are required to work 100% onsite.": "onsite",
            "This role is 100% remote.": "remote",
            "Fully remote position.": "remote",
            "Trabajo totalmente remoto.": "remote",
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(self.detectar(texto), esperado)

    # ── Lo que NO es modalidad: antes daba falsos positivos ──────
    def test_no_confunde_otros_usos_de_las_palabras(self):
        falsos = (
            "Access to an on-site fitness center.",
            "Familiarity with hybrid identity (Azure AD/Entra ID).",
            "Experience working in Agile, Waterfall, or hybrid project environments.",
            "Advanced RAG pipelines with hybrid search.",
            "Use dynamic presentation skills in onsite and/or virtual training.",
            "We offer a dynamic, hybrid-friendly culture.",
            "Over-the-Phone (OPI) and Video Remote Interpreter (VRI).",
            "Teletrabajo ocasional según necesidad del negocio.",
        )
        for texto in falsos:
            with self.subTest(texto=texto):
                self.assertIsNone(self.detectar(texto))

    # ── Casos REALES de la BD (detectados el 2026-10-31) ───────
    def test_marcas_reales_de_la_bd(self):
        casos = {
            # Etiqueta del reclutador en español.
            "#LI-Híbrido Primary Location San Jose, Costa Rica": "hybrid",
            # Campo "Working Conditions" de TD SYNNEX.
            "Working Conditions: Remote / Work-from-home.": "remote",
            "Working Conditions: Professional environment (Hybrid).": "hybrid",
            # Workday escribe "Hybrid Work : <regla>".
            "Hybrid Work : Candidates will be expected to work from the"
            " office at least 50% of the time.": "hybrid",
            # El puesto, no el servicio.
            "This is a remote role based out of Costa Rica.": "remote",
            # Oficina + algo de remoto = híbrido.
            "Zuora Costa Rica office (Heredia): Multiple office days with"
            " some remote flexibility.": "hybrid",
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(self.detectar(texto), esperado)

    # ── Lo que la regla NO debe resolver (conservador) ──────────
    def test_no_usa_boilerplate_de_la_empresa_ni_del_servicio(self):
        falsos = (
            # Beneficio de un puesto 100% remoto: NO es híbrido.
            "we currently offer a competitive pay structure and remote"
            " flexibility",
            # Puesto 100% presencial.
            "This role is based in our Costa Rica office in Heredia, with"
            " required office days every week.",
            # Campañas de marketing, no modalidad.
            "Experience managing both onsite (owned & operated) and offsite"
            " (programmatic, social) campaigns.",
            # "remoto" como característica del servicio.
            "Four weeks of paid training (on-site or remote) covering"
            " interpretation techniques.",
            "rather than informal or loosely managed remote roles",
            # Política general de la empresa (NO declara el puesto).
            "Por eso ofrecemos un modelo de trabajo flexible que combina el"
            " trabajo remoto con la colaboración presencial intencionada.",
            "Our Approach to Flexible Work With Flex Work, we're combining"
            " the best of both worlds: in-person time and remote.",
        )
        for texto in falsos:
            with self.subTest(texto=texto):
                self.assertIsNone(self.detectar(texto))

    def test_sin_texto_devuelve_none(self):
        self.assertIsNone(self.detectar(None, "", "   "))
        self.assertIsNone(self.detectar())

    def test_recorre_varios_textos_y_gana_el_primero(self):
        # La etiqueta suele estar en la descripcion, no en los requisitos.
        self.assertEqual(
            self.detectar("sin marca", "#LI-Hybrid"), "hybrid"
        )
        self.assertEqual(
            self.detectar("#LI-Onsite", "#LI-Hybrid"), "onsite"
        )

    # ── La etiqueta esta fuera del recorte de 2000 chars que ve la IA ──
    def test_lee_mas_alla_del_recorte_de_la_ia(self):
        relleno = "x" * 4000
        self.assertEqual(
            self.detectar(f"{relleno} #LI-Onsite Required Skills:"),
            "onsite",
        )


class TestWorkModeSinLlamarALaIA(unittest.TestCase):
    """``enrich_job_fields`` usa la regla y no gasta la llamada al modelo."""

    def test_no_consulta_el_modelo_si_hay_etiqueta(self):
        cliente = FakeIAClient()
        job = {
            "job_id": "P-1",
            "title": "Operario de Manufactura",
            "city": "Heredia",
            "region": "Heredia",
            "work_mode": "unknown",
            "date_published": "2026-10-20",
            "description_raw": "Descripcion larga. #LI-ONSITE Required Skills:",
        }
        filled = asyncio.run(iae.enrich_job_fields(job, cliente))
        self.assertEqual(filled.get("work_mode"), "onsite")
        # work_mode no se pidio al modelo: no hubo respuesta "onsite" del fake
        # que pudiera justificarlo (el fake tambien diria onsite), asi que se
        # comprueba contando llamadas: ninguna de modalidad.
        self.assertFalse(
            getattr(cliente, "prompts_pedidos", []).count(
                iae.WORK_MODE_PROMPT
            )
        )

    def test_si_no_hay_etiqueta_si_consulta_el_modelo(self):
        cliente = FakeIAClient()
        job = {
            "job_id": "P-2",
            "title": "Analista",
            "city": "Heredia",
            "region": "Heredia",
            "work_mode": "unknown",
            "date_published": "2026-10-20",
            "description_raw": "Buscamos una persona ordenada.",
        }
        filled = asyncio.run(iae.enrich_job_fields(job, cliente))
        self.assertEqual(filled.get("work_mode"), "onsite")


if __name__ == "__main__":
    unittest.main()
