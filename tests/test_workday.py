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
from jobpulse_v15.ingestion import IngestionService
from jobpulse_v15.repository import Repository
from jobpulse_v15.workday import MAX_PAGES, WorkdayFetchError, WorkdayFetcher


class TestWorkdayFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = WorkdayFetcher(request_delay=0)
        self.site = {
            "site_id": "intel-cr",
            "site_name": "Intel Careers CR",
            "company_name": "Intel",
            "country": "CR",
            "base_url": "https://intel.wd1.myworkdayjobs.com/External/en-US",
            "site_config": {},
        }

    @staticmethod
    def posting(location="San Jose, Costa Rica"):
        return {
            "title": "Software Engineer",
            "locationsText": location,
            "externalPath": (
                "/job/San-Jose/Software-Engineer_JR1234567"
            ),
        }

    @staticmethod
    def detail(location="San Jose, Costa Rica"):
        return {
            "jobPostingInfo": {
                "title": "Software Engineer",
                "jobPostingId": "JR1234567",
                "externalUrl": "https://intel.wd1.myworkdayjobs.com/External/job/1",
                "location": location,
                "jobDescription": (
                    "<div>Build <b>reliable</b> software.</div>"
                    "<p>Fluent English required.</p>"
                ),
                "startDate": "2026-10-20",
                "timeType": "Full time",
            }
        }

    def test_fetch_maps_single_board_response_to_v15_ingestion_format(self):
        with patch.object(
            self.fetcher,
            "_request_json",
            side_effect=[
                {"jobPostings": [self.posting()]},
                self.detail(),
            ],
        ) as request:
            offers = self.fetcher.fetch(self.site, pages=1)

        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer["source_job_id"], "JR1234567")
        self.assertEqual(offer["job"]["job_id"], "workday-JR1234567")
        self.assertEqual(offer["job"]["company"], "Intel")
        self.assertEqual(offer["job"]["country"], "CR")
        # "San Jose" es provincia y ciudad: la CIUDAD no se adivina, la
        # REGION si es cierta (el lugar esta en la provincia de San Jose).
        self.assertIsNone(offer["job"]["city"])
        self.assertEqual(offer["job"]["region"], "San José")
        self.assertEqual(offer["job"]["location_raw"], "San Jose, Costa Rica")
        self.assertEqual(offer["job"]["work_mode"], "unknown")
        self.assertEqual(offer["job"]["date_published"], "2026-10-20")
        self.assertEqual(
            offer["job"]["description_raw"],
            "Build reliable software. Fluent English required.",
        )
        self.assertEqual(len(offer["raw_payload"]), 2)
        self.assertEqual(
            request.call_args_list[0].args[0],
            "https://intel.wd1.myworkdayjobs.com"
            "/wday/cxs/intel/External/jobs",
        )
        self.assertEqual(
            request.call_args_list[1].args[0],
            "https://intel.wd1.myworkdayjobs.com"
            "/wday/cxs/intel/External/job/San-Jose/Software-Engineer_JR1234567",
        )
        self.assertEqual(request.call_args_list[0].kwargs["payload"]["searchText"],
                         "Costa Rica")

    def test_fetch_skips_malformed_listings_without_losing_the_board(self):
        """Un anuncio malformado (sin externalPath, p.ej. promocional) no mata
        el barrido del tablero: se omite con aviso y el resto se procesa
        (bug real de HPE 2026-10-28: jobPostings[6] sin externalPath)."""
        with patch.object(
            self.fetcher,
            "_request_json",
            side_effect=[
                {
                    "jobPostings": [
                        self.posting(),
                        "no-soy-un-objeto",
                        {"title": "Anuncio sin externalPath"},
                        self.posting(),
                    ]
                },
                self.detail(),
            ],
        ):
            offers = self.fetcher.fetch(self.site, pages=1)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["source_job_id"], "JR1234567")

    def test_fetch_normalizes_province_only_location_without_inventing_city(self):
        with patch.object(
            self.fetcher,
            "_request_json",
            side_effect=[
                {"jobPostings": [self.posting("Guanacaste, Costa Rica")]},
                self.detail("Guanacaste, Costa Rica"),
            ],
        ):
            offer = self.fetcher.fetch(self.site)[0]

        self.assertIsNone(offer["job"]["city"])
        self.assertEqual(offer["job"]["region"], "Guanacaste")
        self.assertEqual(offer["job"]["location_raw"], "Guanacaste, Costa Rica")

    def test_fetch_splits_city_and_province_when_both_are_explicit(self):
        location = "Liberia, Guanacaste, Costa Rica"
        with patch.object(
            self.fetcher,
            "_request_json",
            side_effect=[
                {"jobPostings": [self.posting(location)]},
                self.detail(location),
            ],
        ):
            offer = self.fetcher.fetch(self.site)[0]

        self.assertEqual(offer["job"]["city"], "Liberia")
        self.assertEqual(offer["job"]["region"], "Guanacaste")
        self.assertEqual(offer["job"]["location_raw"], location)

    def test_fetch_does_not_guess_between_capital_city_and_province(self):
        location = "San Jose, Costa Rica"
        with patch.object(
            self.fetcher,
            "_request_json",
            side_effect=[
                {"jobPostings": [self.posting(location)]},
                self.detail(location),
            ],
        ):
            offer = self.fetcher.fetch(self.site)[0]

        # No se adivina la ciudad, pero la provincia que el texto SI nombra
        # se guarda: el aviso esta en la provincia de San Jose.
        self.assertIsNone(offer["job"]["city"])
        self.assertEqual(offer["job"]["region"], "San José")
        self.assertEqual(offer["job"]["location_raw"], location)

    def test_fetch_no_adivina_la_ciudad_pero_conserva_la_provincia(self):
        location = "San Jose, Central, Costa Rica"
        with patch.object(
            self.fetcher,
            "_request_json",
            side_effect=[
                {"jobPostings": [self.posting(location)]},
                self.detail(location),
            ],
        ):
            offer = self.fetcher.fetch(self.site)[0]

        self.assertIsNone(offer["job"]["city"])
        self.assertEqual(offer["job"]["region"], "San José")
        self.assertEqual(offer["job"]["location_raw"], location)

    def test_manual_state_skips_workday_detail_and_is_not_counted_as_zero_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "manual-skip.db")
            database.initialize()
            repository = Repository(database)
            repository.register_platform("workday", "Workday", "api")
            repository.register_site(
                "intel-cr",
                "workday",
                "Intel Careers CR",
                self.site["base_url"],
                country="CR",
            )
            repository.save_job(
                {
                    "job_id": "workday-JR1234567",
                    "title": "Software Engineer",
                },
                site_id="intel-cr",
                source_job_id="JR1234567",
                source_url="https://example.test/jobs/1",
            )
            repository.set_user_job_state("workday-JR1234567", "applied")
            skipped_ids = repository.list_skipped_source_job_ids("intel-cr")
            fetcher = WorkdayFetcher(request_delay=0)

            with patch.object(
                fetcher,
                "_request_json",
                return_value={"jobPostings": [self.posting()]},
            ) as request:
                result = IngestionService(repository).fetch_and_import(
                    "intel-cr",
                    lambda: fetcher.fetch(
                        self.site,
                        skip_source_job_ids=skipped_ids,
                    ),
                    run_kind="workday",
                )

            request.assert_called_once()
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["jobs_found"], 1)
            self.assertEqual(result["jobs_valid"], 0)
            self.assertEqual(result["jobs_skipped"], 1)
            run = repository.get_run(result["run_id"])
            self.assertEqual(run["sites"][0]["status"], "ok")
            self.assertEqual(run["sites"][0]["jobs_found"], 1)

    def test_fetch_uses_configured_search_and_does_not_import_other_country(self):
        site = {
            **self.site,
            "site_config": {
                "search_text": "Costa Rica",
                "country_query": "Costa Rica",
                "country": "CR",
            },
        }
        with patch.object(
            self.fetcher,
            "_request_json",
            side_effect=[
                {"jobPostings": [self.posting("Austin, Texas")]},
                self.detail("Austin, Texas"),
            ],
        ):
            self.assertEqual(self.fetcher.fetch(site), [])

    def test_invalid_board_url_and_page_limits_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "URL Workday invalida"):
            self.fetcher.fetch({**self.site, "base_url": "https://example.com/jobs"})
        with self.assertRaisesRegex(ValueError, "pages debe estar"):
            self.fetcher.fetch(self.site, pages=MAX_PAGES + 1)

    def test_malformed_workday_response_is_an_error_not_zero_results(self):
        with patch.object(
            self.fetcher, "_request_json", return_value={"unexpected": []}
        ):
            with self.assertRaisesRegex(WorkdayFetchError, "jobPostings"):
                self.fetcher.fetch(self.site)

    def test_cli_fetch_is_explicit_and_persists_to_v15(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "cli.db")
            database.initialize()
            repository = Repository(database)
            repository.register_platform("workday", "Workday", "api")
            repository.register_site(
                "intel-cr",
                "workday",
                "Intel Careers CR",
                self.site["base_url"],
                company_name="Intel",
                country="CR",
            )
            output = io.StringIO()
            with patch(
                "jobpulse_v15.cli.WorkdayFetcher.fetch",
                return_value=[
                    {
                        "source_job_id": "JR1234567",
                        "source_url": "https://intel.example/job/1",
                        "job": {
                            "job_id": "workday-JR1234567",
                            "title": "Software Engineer",
                            "country": "CR",
                        },
                    }
                ],
            ) as fetch, patch(
                "sys.argv",
                [
                    "jobpulse-v15",
                    "--db",
                    str(database.path),
                    "scrape",
                    "workday",
                    "--site",
                    "intel-cr",
                ],
            ), redirect_stdout(output):
                self.assertEqual(main(), 0)

            fetch.assert_called_once()
            result = json.loads(output.getvalue())
            self.assertEqual(result["jobs_new"], 1)
            self.assertEqual(result["status"], "ok")
            self.assertIsNotNone(repository.get_job("workday-JR1234567"))

    def test_location_backfill_defaults_to_preview_and_preserves_existing_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "locations.db")
            database.initialize()
            repository = Repository(database)
            repository.register_platform("workday", "Workday", "api")
            repository.register_site(
                "intel-cr",
                "workday",
                "Intel Careers CR",
                self.site["base_url"],
                country="CR",
            )
            location = "Liberia, Guanacaste, Costa Rica"
            repository.save_job(
                {
                    "job_id": "workday-REQ123456",
                    "title": "Software Engineer",
                    "city": "Verified City",
                    "location_raw": location,
                },
                site_id="intel-cr",
                source_job_id="REQ123456",
                raw_payload={
                    "listing": self.posting(location),
                    "detail": self.detail(location),
                },
            )
            ambiguous_location = "San Jose, Costa Rica"
            repository.save_job(
                {
                    "job_id": "workday-REQ654321",
                    "title": "Test Engineer",
                    "city": "San Jose",
                    "location_raw": ambiguous_location,
                },
                site_id="intel-cr",
                source_job_id="REQ654321",
                raw_payload={
                    "listing": self.posting(ambiguous_location),
                    "detail": self.detail(ambiguous_location),
                },
            )
            # Ciudad BASURA del parser viejo (la ubicacion entera en `city`):
            # debe corregirse, no conservarse para siempre.
            basura_location = "GCG_Costa Rica_San Jose"
            repository.save_job(
                {
                    "job_id": "workday-REQ777777",
                    "title": "Auxiliar de limpieza",
                    "city": "GCG_Costa Rica_San Jose",
                    "location_raw": basura_location,
                },
                site_id="intel-cr",
                source_job_id="REQ777777",
                raw_payload={
                    "listing": self.posting(basura_location),
                    "detail": self.detail(basura_location),
                },
            )
            output = io.StringIO()
            command = [
                "jobpulse-v15",
                "--db",
                str(database.path),
                "location",
                "normalize-workday",
            ]
            with patch("sys.argv", command), redirect_stdout(output):
                self.assertEqual(main(), 0)

            preview = json.loads(output.getvalue())
            self.assertEqual(preview["mode"], "dry_run")
            self.assertEqual(preview["records_scanned"], 3)
            # Ya no queda ninguna "unrecognized": "San Jose, Costa Rica"
            # aporta la region San Jose aunque la ciudad sea ambigua.
            self.assertEqual(preview["skipped_unrecognized"], 0)
            self.assertEqual(len(preview["updates"]), 3)
            self.assertEqual(preview["updates"][0]["city"], "Verified City")
            self.assertEqual(preview["updates"][0]["region"], "Guanacaste")
            self.assertEqual(preview["updates"][1]["city"], "San Jose")
            self.assertEqual(preview["updates"][1]["region"], "San José")
            self.assertEqual(preview["corrected_cities"], 1)
            self.assertIsNone(repository.get_job("workday-REQ123456")["region"])

            output = io.StringIO()
            with patch("sys.argv", [*command, "--apply"]), redirect_stdout(output):
                self.assertEqual(main(), 0)

            applied = json.loads(output.getvalue())
            self.assertEqual(applied["mode"], "apply")
            self.assertTrue(applied["updates"][0]["updated"])
            job = repository.get_job("workday-REQ123456")
            self.assertEqual(job["city"], "Verified City")
            self.assertEqual(job["region"], "Guanacaste")
            ambiguous_job = repository.get_job("workday-REQ654321")
            self.assertEqual(ambiguous_job["city"], "San Jose")
            # La ciudad existente se conserva; la region que faltaba se llena.
            self.assertEqual(ambiguous_job["region"], "San José")
            # La ciudad basura se reemplaza (por None) y la region se llena.
            basura_job = repository.get_job("workday-REQ777777")
            self.assertIsNone(basura_job["city"])
            self.assertEqual(basura_job["region"], "San José")
            records = repository.list_workday_location_records("intel-cr")
            self.assertEqual(records[0]["location_raw"], location)

    def test_cli_search_can_include_manually_skipped_jobs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "managed-search.db")
            database.initialize()
            repository = Repository(database)
            repository.register_platform("workday", "Workday", "api")
            repository.register_site(
                "intel-cr",
                "workday",
                "Intel Careers CR",
                self.site["base_url"],
                country="CR",
            )
            for job_id in ("job-applied", "job-open"):
                repository.save_job(
                    {"job_id": job_id, "title": job_id},
                    site_id="intel-cr",
                    source_job_id=job_id,
                )
            repository.set_user_job_state("job-applied", "applied")
            command = [
                "jobpulse-v15",
                "--db",
                str(database.path),
                "search",
            ]

            output = io.StringIO()
            with patch("sys.argv", command), redirect_stdout(output):
                self.assertEqual(main(), 0)
            visible = json.loads(output.getvalue())
            self.assertEqual([job["job_id"] for job in visible], ["job-open"])

            output = io.StringIO()
            with patch(
                "sys.argv", [*command, "--include-manually-skipped"]
            ), redirect_stdout(output):
                self.assertEqual(main(), 0)
            included = json.loads(output.getvalue())
            self.assertEqual(
                {job["job_id"] for job in included},
                {"job-applied", "job-open"},
            )

    def test_cli_fetch_error_is_recorded_in_the_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "failure.db")
            database.initialize()
            repository = Repository(database)
            repository.register_platform("workday", "Workday", "api")
            repository.register_site(
                "intel-cr",
                "workday",
                "Intel Careers CR",
                self.site["base_url"],
                country="CR",
            )
            with patch(
                "jobpulse_v15.cli.WorkdayFetcher.fetch",
                side_effect=WorkdayFetchError("HTTP 503"),
            ), patch(
                "sys.argv",
                [
                    "jobpulse-v15",
                    "--db",
                    str(database.path),
                    "scrape",
                    "workday",
                    "--site",
                    "intel-cr",
                ],
            ), self.assertRaises(SystemExit):
                main()

            runs = repository.list_runs()
            self.assertEqual(len(runs), 1)
            run = repository.get_run(runs[0]["run_id"])
            self.assertEqual(run["status"], "error")
            self.assertIn("HTTP 503", run["sites"][0]["error_message"])

    def test_cli_rejects_non_workday_site_before_fetch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "not-workday.db")
            database.initialize()
            repository = Repository(database)
            repository.register_platform("other", "Other", "api")
            repository.register_site(
                "other-site",
                "other",
                "Other site",
                "https://example.test/jobs",
            )
            with patch(
                "jobpulse_v15.cli.WorkdayFetcher.fetch"
            ) as fetch, patch(
                "sys.argv",
                [
                    "jobpulse-v15",
                    "--db",
                    str(database.path),
                    "scrape",
                    "workday",
                    "--site",
                    "other-site",
                ],
            ), self.assertRaises(SystemExit):
                main()
            fetch.assert_not_called()
            self.assertEqual(repository.list_runs(), [])


class TestNormalizeLocation(unittest.TestCase):
    """Formatos reales de ubicacion de Workday en Costa Rica.

    Los casos salen literalmente de `jobs.location_raw`: los tableros no
    usan un unico formato, y el normalizador solo aceptaba "Ciudad, Costa
    Rica" con comas (dejaba como "unrecognized" media base y colaba
    ciudad="Remote").
    """

    def norm(self, location: str, country: str = "CR",
             country_query: str = "Costa Rica"):
        return WorkdayFetcher.normalize_location(location, country, country_query)

    # -- Solo se normaliza Costa Rica ---------------------------------
    def test_ignora_paises_que_no_son_costa_rica(self):
        self.assertEqual(
            self.norm("Alajuela, Costa Rica", country="MX"),
            {"city": None, "region": None},
        )
        self.assertEqual(
            self.norm("Bogota, Colombia", country_query="Colombia"),
            {"city": None, "region": None},
        )

    def test_codigo_de_pais_admite_cri(self):
        self.assertEqual(
            self.norm("Guanacaste, Costa Rica", country="CRI"),
            {"city": None, "region": "Guanacaste"},
        )

    # -- Pais delante: la posicion desambigua la provincia -------------
    def test_pais_delante_da_la_provincia_por_cierta(self):
        casos = {
            "Costa Rica - Alajuela": "Alajuela",
            "Costa Rica - Heredia": "Heredia",
            "Costa Rica-Alajuela": "Alajuela",
            "Costa Rica-Cartago": "Cartago",
            "Costa Rica - Limon": "Limón",
        }
        for texto, provincia in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(
                    self.norm(texto),
                    {"city": None, "region": provincia},
                )

    def test_planta_tras_la_provincia_no_es_ciudad(self):
        # Antes devolvia city="Wet Plant".
        self.assertEqual(
            self.norm("Costa Rica-Alajuela-Wet Plant"),
            {"city": None, "region": "Alajuela"},
        )
        self.assertEqual(
            self.norm("Costa Rica-Cartago-Dry Plant"),
            {"city": None, "region": "Cartago"},
        )

    # -- Provincia nombrada: la REGION es cierta, la ciudad no ---------
    def test_provincia_nombrada_da_la_region_sin_adivinar_la_ciudad(self):
        # "Alajuela" es provincia y tambien ciudad/distrito. La CIUDAD queda
        # nula (no se sabe a cual se refiere), pero la REGION es cierta: si
        # el texto nombra la provincia, el lugar esta en esa provincia.
        casos = {
            "San Jose, Costa Rica": "San José",
            "Alajuela, Costa Rica": "Alajuela",
            "Heredia, Costa Rica": "Heredia",
            "Cartago, Costa Rica": "Cartago",
            "Heredia Costa Rica": "Heredia",
            "Heredia, -H, Costa Rica": "Heredia",
            "San Jose, Central, Costa Rica": "San José",
            "Heredia, Heredia, Costa Rica": "Heredia",
        }
        for texto, provincia in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(
                    self.norm(texto), {"city": None, "region": provincia}
                )

    def test_provincia_sola_no_ambigua_si_se_guarda(self):
        # No existe una ciudad llamada Guanacaste: el dato es la provincia.
        self.assertEqual(
            self.norm("Guanacaste, Costa Rica"),
            {"city": None, "region": "Guanacaste"},
        )

    # -- Jerarquia distrito -> canton -> provincia ---------------------
    def test_jerarquia_distrito_canton_provincia(self):
        # La direccion costarricense va de lo mas especifico a lo mas
        # general: distrito, canton, provincia, pais.
        self.assertEqual(
            self.norm("San Antonio, Belen, Heredia, Costa Rica"),
            {"city": "San Antonio", "region": "Heredia"},
        )
        # "Belen" es el canton: se guarda con el nombre oficial ("Belén").
        self.assertEqual(
            self.norm("Belen, Heredia"),
            {"city": "Belén", "region": "Heredia"},
        )

    def test_guion_bajo_como_separador(self):
        # "GCG_Costa Rica_San Jose": antes se colaba como ciudad entera.
        self.assertEqual(
            self.norm("GCG_Costa Rica_San Jose"),
            {"city": None, "region": "San José"},
        )

    def test_solo_el_pais_o_la_modalidad_no_inventa_nada(self):
        for texto in ("Costa Rica", "Costa Rica Remote", "Remote - Costa Rica",
                      "Remote, Costa Rica", "Costa Rica, Costa Rica",
                      "Global Service Center- Costa Rica", "Virtual",
                      "Costa Rica (Remote)", "Latin America (Remote)"):
            with self.subTest(texto=texto):
                self.assertEqual(
                    self.norm(texto), {"city": None, "region": None}
                )

    # -- Ciudad + provincia -------------------------------------------
    def test_ciudad_delante_y_provincia_detras(self):
        self.assertEqual(
            self.norm("Coyol, Alajuela, Costa Rica"),
            {"city": "Coyol", "region": "Alajuela"},
        )
        self.assertEqual(
            self.norm("San José, Escazú, Costa Rica"),
            {"city": "Escazú", "region": "San José"},
        )

    def test_provincia_delante_con_canton_conocido(self):
        casos = {
            "Guanacaste / Liberia / Liberia": {"city": "Liberia", "region": "Guanacaste"},
            "San José / Escazú / Escazú": {"city": "Escazú", "region": "San José"},
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(self.norm(texto), esperado)

    def test_provincia_delante_con_distrito_conocido_lo_guarda(self):
        # "La Garita" es un distrito de Alajuela: con la division territorial
        # completa ya se puede guardar (antes se descartaba por no ser canton).
        self.assertEqual(
            self.norm("Alajuela / Alajuela / La Garita"),
            {"city": "La Garita", "region": "Alajuela"},
        )

    def test_no_guarda_planta_zona_ni_abreviatura_como_ciudad(self):
        casos = {
            "Costa Rica-Alajuela-Wet Plant": "Alajuela",
            "Costa Rica-Cartago-Dry Plant": "Cartago",
            "San Jose, Costa Rica Local Office": "San José",
        }
        for texto, provincia in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(
                    self.norm(texto), {"city": None, "region": provincia}
                )

    def test_zona_conocida_como_ciudad(self):
        # "Alajuela Coyol" es "provincia + zona", pero la zona (Coyol Free
        # Zone) esta en la tabla de lugares: la ciudad si se puede guardar.
        self.assertEqual(
            self.norm("Alajuela Coyol, Alajuela, Costa Rica"),
            {"city": "Coyol", "region": "Alajuela"},
        )

    # -- Canton conocido: completa la provincia -----------------------
    def test_canton_conocido_completa_la_provincia(self):
        casos = {
            "Grecia, Costa Rica": {"city": "Grecia", "region": "Alajuela"},
            "Santa Ana, Costa Rica": {"city": "Santa Ana", "region": "San José"},
            # "San Antonio de Belen": el distrito (San Antonio) con su canton
            # (Belen) resuelve la provincia de Heredia.
            "San Antonio de Belen, Costa Rica": {
                "city": "San Antonio", "region": "Heredia",
            },
            "Liberia, Costa Rica": {"city": "Liberia", "region": "Guanacaste"},
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(self.norm(texto), esperado)

    def test_canton_ambiguo_no_completa_la_provincia(self):
        # "Lagunilla" no esta en la division territorial: se guarda la ciudad
        # y se deja la provincia nula en vez de elegir una.
        self.assertEqual(
            self.norm("Lagunilla, Costa Rica"),
            {"city": "Lagunilla", "region": None},
        )

    def test_distrito_conocido_completa_la_provincia(self):
        # Con la division territorial completa, un distrito ya da la provincia.
        self.assertEqual(
            self.norm("Ulloa, Costa Rica"),
            {"city": "Ulloa", "region": "Heredia"},
        )
        self.assertEqual(
            self.norm("Río Segundo, -A, Costa Rica"),
            {"city": "Río Segundo", "region": "Alajuela"},
        )

    def test_sin_acentos_y_mayusculas(self):
        self.assertEqual(
            self.norm("GUANACASTE, COSTA RICA"),
            {"city": None, "region": "Guanacaste"},
        )
        self.assertEqual(
            self.norm("costa rica - limon"),
            {"city": None, "region": "Limón"},
        )
        self.assertEqual(
            self.norm("grecia, costa rica"),
            {"city": "Grecia", "region": "Alajuela"},
        )

    def test_texto_vacio_o_basura(self):
        for texto in ("", "   ", ",", "-", "---", "()", ",", "A"):
            with self.subTest(texto=texto):
                self.assertEqual(
                    self.norm(texto), {"city": None, "region": None}
                )


if __name__ == "__main__":
    unittest.main()
