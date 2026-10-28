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
from jobpulse_v15.repository import Repository
from jobpulse_v15.workable import WorkableFetchError, WorkableFetcher


class TestWorkableFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = WorkableFetcher()
        self.site = {
            "site_id": "acme-cr",
            "site_name": "Acme Careers CR",
            "company_name": "Acme",
            "country": "CR",
            "base_url": "https://apply.workable.com/acme",
            "site_config": {"country_query": "Costa Rica"},
        }

    def test_fetch_maps_markdown_board_response_to_ingestion_format(self):
        # Mock the main jobs.md table
        list_md = """# Acme — All Open Positions

| Title | Department | Location | Type | Salary | Posted | Details |
|-------|-----------|----------|------|--------|--------|---------|
| Software Engineer | Engineering | San Jose, Costa Rica (Remote) | Full-time | — | 2026-10-20 | [View](https://apply.workable.com/acme/jobs/view/A1B2C3.md) |
"""
        # Mock the detail page
        detail_md = """# Software Engineer

> Acme · San Jose, Costa Rica (Remote) · Full-time · Posted 2026-10-20

**Workplace:** remote

**Department:** Engineering

## Description

**About the Role**

Build **reliable** systems.

## Requirements

Fluent English required.

## Apply

[Apply at Acme](https://apply.workable.com/acme/j/A1B2C3/apply)

---
Powered by [Workable](https://www.workable.com)
"""

        def mock_request_text(url):
            if url.endswith("/jobs.md"):
                return list_md
            elif "/jobs/view/" in url:
                return detail_md
            raise AssertionError(f"Unexpected URL: {url}")

        with patch.object(self.fetcher, "_request_text", side_effect=mock_request_text):
            offers = self.fetcher.fetch(self.site)

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["source_job_id"], "A1B2C3")
        self.assertEqual(offers[0]["job"]["job_id"], "workable-acme-A1B2C3")
        self.assertEqual(offers[0]["job"]["company"], "Acme")
        self.assertEqual(offers[0]["job"]["location_raw"], "San Jose, Costa Rica (Remote)")
        self.assertEqual(offers[0]["job"]["work_mode"], "remote")
        self.assertEqual(offers[0]["job"]["employment_type"], "Full-time")
        self.assertEqual(offers[0]["job"]["date_published"], "2026-10-20")
        self.assertIn("Build reliable systems", offers[0]["job"]["description_raw"])
        self.assertIn("Fluent English required", offers[0]["job"]["description_raw"])

    def test_fetch_filters_countries_deduplicates_and_counts_manual_skips(self):
        list_md = """# Acme — All Open Positions

| Title | Department | Location | Type | Salary | Posted | Details |
|-------|-----------|----------|------|--------|--------|---------|
| Analyst Toronto | Finance | Toronto, Canada | Full-time | — | 2026-10-20 | [View](https://apply.workable.com/acme/jobs/view/JOB1.md) |
| Engineer | Engineering | Remote, Costa Rica | Full-time | — | 2026-10-20 | [View](https://apply.workable.com/acme/jobs/view/JOB2.md) |
| Duplicate | Engineering | San Jose, Costa Rica | Full-time | — | 2026-10-20 | [View](https://apply.workable.com/acme/jobs/view/JOB2.md) |
"""
        detail_md = """# Job

> Acme · Remote, Costa Rica · Full-time · Posted 2026-10-20

**Workplace:** remote

## Description

Description here.

## Requirements

Requirements here.
"""

        call_count = [0]
        def mock_request_text(url):
            call_count[0] += 1
            if url.endswith("/jobs.md"):
                return list_md
            elif "/jobs/view/" in url:
                return detail_md
            raise AssertionError(f"Unexpected URL: {url}")

        with patch.object(self.fetcher, "_request_text", side_effect=mock_request_text):
            offers = self.fetcher.fetch(self.site, skip_source_job_ids={"JOB2"})

        # JOB1 (Toronto) filtered out by country; JOB2 skipped by skip_source_job_ids; JOB3 duplicate of JOB2
        self.assertEqual([offer["source_job_id"] for offer in offers], [])
        self.assertEqual(offers.jobs_skipped, 1)  # JOB2 skipped

    def test_fetch_rejects_untrusted_urls(self):
        for url in (
            "http://apply.workable.com/acme",
            "https://example.com/acme",
            "https://user@apply.workable.com/acme",
            "https://apply.workable.com/",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.fetcher.fetch({**self.site, "base_url": url})

    def test_fetch_handles_malformed_table_gracefully(self):
        # Empty or malformed table returns empty offers
        list_md = "No table here"
        with patch.object(self.fetcher, "_request_text", return_value=list_md):
            offers = self.fetcher.fetch(self.site)
        self.assertEqual(len(offers), 0)

    def test_workable_cli_imports_single_site(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "workable.db")
            database.initialize()
            repository = Repository(database)
            repository.register_platform("workable", "Workable", "api")
            repository.register_site(
                "acme-cr",
                "workable",
                "Acme Careers CR",
                "https://apply.workable.com/acme",
                company_name="Acme",
                country="CR",
                site_config={"adapter": "workable"},
            )
            offer = {
                "source_job_id": "A1B2C3",
                "source_url": "https://apply.workable.com/acme/jobs/view/A1B2C3.md",
                "job": {
                    "job_id": "workable-acme-A1B2C3",
                    "title": "Software Engineer",
                    "country": "CR",
                },
            }
            output = io.StringIO()
            with patch(
                "sys.argv",
                [
                    "jobpulse-v15",
                    "--db",
                    str(database.path),
                    "scrape",
                    "workable",
                    "--site",
                    "acme-cr",
                ],
            ), patch(
                "jobpulse_v15.cli.WorkableFetcher.fetch", return_value=[offer]
            ), redirect_stdout(output):
                self.assertEqual(main(), 0)

            result = json.loads(output.getvalue())
            self.assertEqual(result["jobs_new"], 1)
            self.assertIsNotNone(repository.get_job("workable-acme-A1B2C3"))

    def test_workable_group_continues_after_site_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "workable-group.db")
            database.initialize()
            repository = Repository(database)
            repository.register_platform("workable", "Workable", "api")
            for site_id in ("site-good", "site-fails"):
                repository.register_site(
                    site_id,
                    "workable",
                    site_id,
                    f"https://apply.workable.com/{site_id}",
                    run_groups=("directos",),
                )

            offer = {
                "source_job_id": "99",
                "job": {"job_id": "workable-site-good-99", "title": "Engineer"},
            }

            def fetch(site, **kwargs):
                _ = kwargs
                if site["site_id"] == "site-fails":
                    raise WorkableFetchError("tablero no disponible")
                return [offer]

            output = io.StringIO()
            with patch(
                "sys.argv",
                [
                    "jobpulse-v15",
                    "--db",
                    str(database.path),
                    "scrape",
                    "workable",
                    "--group",
                    "directos",
                ],
            ), patch(
                "jobpulse_v15.cli.WorkableFetcher.fetch", side_effect=fetch
            ), redirect_stdout(output):
                self.assertEqual(main(), 1)

            report = json.loads(output.getvalue())
            self.assertEqual(report["sites_selected"], 2)
            self.assertEqual(len(report["results"]), 1)
            self.assertEqual(len(report["failures"]), 1)
            self.assertIsNotNone(repository.get_job("workable-site-good-99"))
            self.assertEqual(
                repository.list_site_runs("site-fails", limit=1)[0]["site_status"],
                "error",
            )


if __name__ == "__main__":
    unittest.main()