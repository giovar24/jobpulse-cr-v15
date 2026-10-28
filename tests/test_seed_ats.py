# -*- coding: utf-8 -*-
"""Tests del directorio ATS CR (seed_ats): carga de seeds + registro idempotente.

Patron de tests/test_repository.py (tempdir + Database + Repository).
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository
from jobpulse_v15 import seed_ats

SITE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class TestCargaSeeds(unittest.TestCase):
    def test_directorio_no_vacio_y_plataformas_soportadas(self):
        tableros = seed_ats.cargar_directorio()
        self.assertGreater(len(tableros), 50, "el directorio portado debe traer tableros")
        for tablero in tableros:
            self.assertIn(tablero["platform"], seed_ats.PLATAFORMAS_SOPORTADAS)
            self.assertTrue(tablero["base_url"].startswith("http"))
            self.assertTrue(tablero["company"])

    def test_cubre_workday_y_demas_ats(self):
        tableros = seed_ats.cargar_directorio()
        plataformas = {t["platform"] for t in tableros}
        self.assertIn("workday", plataformas)
        # Los tres archivos de seed aportan filas.
        self.assertIn("workable", plataformas)
        self.assertIn("successfactors", plataformas)
        self.assertGreaterEqual(len(plataformas), 4)

    def test_filtro_por_plataforma(self):
        solo_workday = seed_ats.cargar_directorio(["workday"])
        self.assertTrue(solo_workday)
        self.assertEqual({t["platform"] for t in solo_workday}, {"workday"})

    def test_site_ids_unicos_y_validos(self):
        ids = [
            f"{t['platform']}-{seed_ats._slug(t['company'])}"
            for t in seed_ats.cargar_directorio()
        ]
        self.assertEqual(len(ids), len(set(ids)), "los site_id deben ser unicos")
        for site_id in ids:
            self.assertRegex(site_id, SITE_ID_RE)


class TestRegistroDirectorio(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registra_todos_y_esta_configurado(self):
        stats = seed_ats.registrar_directorio(self.repository)
        self.assertEqual(len(stats["registrados"]), stats["tableros"])
        self.assertEqual(stats["omitidos"], [])

        sites = self.repository.list_sites()
        self.assertEqual(len(sites), stats["tableros"])
        for site in sites:
            self.assertIn(site["platform_id"], seed_ats.PLATAFORMAS_SOPORTADAS)
            self.assertTrue(site["enabled"], f"{site['site_id']} debe quedar activo")
            self.assertIn("directos", site["run_groups"])
            self.assertEqual(site["country"], "CR")
            self.assertEqual(site["site_config"].get("adapter"), site["platform_id"])
            self.assertTrue(site["site_config"].get("country_query"))
            if site["platform_id"] == "workday":
                self.assertEqual(site["site_config"].get("search_text"), "Costa Rica")

        # Las plataformas existen y con el provider_type de init-sources.
        for platform_id, (_name, provider_type, _lang) in seed_ats.PLATAFORMAS.items():
            platform = self.repository.get_platform(platform_id)
            self.assertIsNotNone(platform, f"falta la plataforma {platform_id}")
            self.assertEqual(platform["provider_type"], provider_type)

    def test_segunda_corrida_no_duplica(self):
        primero = seed_ats.registrar_directorio(self.repository)
        segundo = seed_ats.registrar_directorio(self.repository)
        self.assertEqual(segundo["registrados"], [])
        self.assertEqual(len(segundo["omitidos"]), primero["tableros"])
        for _site_id, motivo in segundo["omitidos"]:
            self.assertEqual(motivo, "base_url ya registrada")
        self.assertEqual(
            len(self.repository.list_sites()), primero["tableros"],
            "el registro debe ser idempotente",
        )

    def test_dry_run_no_escribe(self):
        stats = seed_ats.registrar_directorio(self.repository, dry_run=True)
        self.assertTrue(stats["dry_run"])
        self.assertGreater(len(stats["registrados"]), 0)
        self.assertEqual(self.repository.list_sites(), [])

    def test_filtro_por_plataforma(self):
        stats = seed_ats.registrar_directorio(self.repository, ["successfactors"])
        sites = self.repository.list_sites()
        self.assertEqual(len(sites), len(stats["registrados"]))
        self.assertTrue(sites)
        for site in sites:
            self.assertEqual(site["platform_id"], "successfactors")

    def test_omite_url_ya_registrada_aunque_otro_site_id(self):
        # Un tablero Workday registrado a mano con otro site_id no debe duplicarse.
        tablero = next(
            t for t in seed_ats.cargar_directorio(["workday"])
        )
        self.repository.register_platform("workday", "Workday", "api", "en")
        self.repository.register_site(
            "manual-workday",
            "workday",
            "Tablero manual",
            tablero["base_url"],
            run_groups=("directos",),
            site_config={"adapter": "workday"},
        )
        stats = seed_ats.registrar_directorio(self.repository, ["workday"])
        self.assertNotIn("manual-workday", stats["registrados"])
        self.assertTrue(stats["omitidos"])
        con_misma_url = [
            site
            for site in self.repository.list_sites()
            if site["base_url"].rstrip("/").casefold()
            == tablero["base_url"].rstrip("/").casefold()
        ]
        self.assertEqual(len(con_misma_url), 1, "la URL no debe duplicarse")

    def test_seeds_son_json_valido_y_versionados(self):
        self.assertTrue(seed_ats.SEEDS_DIR.is_dir())
        archivos = sorted(seed_ats.SEEDS_DIR.glob("*.json"))
        self.assertGreaterEqual(len(archivos), 3)
        for archivo in archivos:
            filas = json.loads(archivo.read_text(encoding="utf-8"))
            self.assertIsInstance(filas, list)
            self.assertTrue(filas, f"{archivo.name} vacio")


if __name__ == "__main__":
    unittest.main()
