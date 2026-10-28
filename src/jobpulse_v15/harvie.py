"""Adaptador para el tablero HeyHarvie (https://heyharvie.com).

API pública: https://heyharvie.com/api/candidate/jobs (paginado)
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from jobpulse_v15.ingestion import IngestionError

logger = logging.getLogger("jobpulse.harvie")


class HarvieFetchError(IngestionError):
    """Error en la obtención de vacantes de HeyHarvie."""


class HarvieOffers(list[dict[str, Any]]):
    """Ofertas filtradas con conteo de anuncios omitidos por estado manual."""

    def __init__(
        self, offers: list[dict[str, Any]], *, jobs_skipped: int = 0
    ) -> None:
        super().__init__(offers)
        self.jobs_skipped = jobs_skipped


class HarvieFetcher:
    """Consulta el tablero HeyHarvie y adapta sus vacantes al formato v1.5."""

    BASE_URL = "https://heyharvie.com/api/candidate/jobs"

    def __init__(self, *, timeout: float = 30.0) -> None:
        if timeout <= 0:
            raise ValueError("timeout debe ser mayor que cero.")
        self.timeout = timeout

    def fetch(
        self,
        site: dict[str, Any],
        *,
        skip_source_job_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        """Obtiene todas las vacantes de HeyHarvie (paginación automática)."""
        config = site.get("site_config") or {}
        if not isinstance(config, dict):
            raise ValueError("La configuracion HeyHarvie debe ser un objeto.")

        country_query = config.get("country_query") or "Costa Rica"
        if not isinstance(country_query, str) or not country_query.strip():
            raise ValueError("country_query debe contener texto.")

        all_offers = []
        skipped = 0
        seen_ids: set[str] = set()
        skipped_ids = skip_source_job_ids or set()

        page = 1
        while True:
            url = f"{self.BASE_URL}?{urlencode({'page': page})}"
            logger.debug("HeyHarvie: solicitando página %d", page)

            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
                with urlopen(req, timeout=self.timeout) as resp:
                    payload = json.load(resp)
            except HTTPError as exc:
                raise HarvieFetchError(f"HTTP {exc.code} al consultar {url}") from exc
            except URLError as exc:
                raise HarvieFetchError(f"Error de red al consultar {url}: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise HarvieFetchError(f"Respuesta no JSON de HeyHarvie: {exc}") from exc

            jobs_data = payload.get("data", {}).get("jobs", {})
            page_jobs = jobs_data.get("data", [])

            if not page_jobs:
                break

            for job in page_jobs:
                source_job_id = str(job.get("id", "")).strip()
                if not source_job_id:
                    logger.warning("HeyHarvie: job sin id; omitido.")
                    continue
                if source_job_id in seen_ids:
                    continue

                title = job.get("name") or job.get("title")
                if not title:
                    logger.warning("HeyHarvie: %s sin titulo; omitido.", source_job_id)
                    continue

                seen_ids.add(source_job_id)

                if source_job_id in skipped_ids:
                    skipped += 1
                    continue

                # Location: job.location.name (ej. "Lagar La Uruca")
                # Location has country_selected with name "Costa Rica"
                location_obj = job.get("location") or {}
                location_name = self._optional_text(location_obj.get("name"))
                country_obj = location_obj.get("country_selected") or location_obj.get("country") or {}
                country_name = self._optional_text(country_obj.get("name"))

                # Filtrar por país (Costa Rica)
                searchable = " ".join(filter(None, [title, location_name, country_name]))
                if country_query.casefold() not in searchable.casefold():
                    continue

                location_raw = location_name or country_name or None

                # Description & requirements
                description = self._html_to_text(self._optional_text(job.get("description")) or "")
                requirements = self._html_to_text(self._optional_text(job.get("requirements")) or "")
                combined = " ".join(part for part in (description, requirements) if part)

                # Published date
                published = self._optional_text(job.get("publish_date"))

                # Company
                company_obj = job.get("company") or {}
                company_name = self._optional_text(company_obj.get("name")) or site.get("company_name") or site.get("site_name")

                # Build offer
                all_offers.append(
                    {
                        "source_job_id": source_job_id,
                        "source_url": f"https://heyharvie.com/jobs/{job.get('slug')}" if job.get("slug") else None,
                        "source_updated_at": published,
                        "job": {
                            "job_id": f"harvie-{source_job_id}",
                            "title": title,
                            "company": company_name,
                            "location_raw": location_raw,
                            "country": "CR" if country_name and "costa rica" in country_name.casefold() else None,
                            "work_mode": self._detect_work_mode(job),
                            "employment_type": self._optional_text(job.get("employment_type")),
                            "date_published": published[:10] if published else None,
                            "posting_language": "es",
                            "posting_language_origin": "source",
                            "description_raw": combined or None,
                        },
                        "raw_payload": job,
                    }
                )

            # Pagination
            current_page = jobs_data.get("current_page", page)
            last_page = jobs_data.get("last_page", page)
            if current_page >= last_page:
                break
            page += 1

        return HarvieOffers(all_offers, jobs_skipped=skipped)

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convierte HTML simple a texto plano (tags básicos)."""
        if not html:
            return ""
        # Remove script/style
        import re
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Replace block tags with newline
        html = re.sub(r"</(div|p|br|li|ul|ol|h[1-6]|section|article)>", "\n", html, flags=re.IGNORECASE)
        # Strip remaining tags
        html = re.sub(r"<[^>]+>", "", html)
        # Decode entities
        from html import unescape
        html = unescape(html)
        # Normalize whitespace
        return " ".join(html.split())

    @staticmethod
    def _detect_work_mode(job: dict[str, Any]) -> str:
        """Detecta modalidad desde campos de HeyHarvie."""
        # workplace field: "on-site", "remote", "hybrid"
        workplace = job.get("workplace")
        if workplace == "remote":
            return "remote"
        if workplace == "hybrid":
            return "hybrid"
        if workplace == "on-site":
            return "onsite"
        # location may indicate
        loc = job.get("location") or {}
        if isinstance(loc, dict):
            name = (loc.get("name") or "").lower()
            if "remote" in name or "remoto" in name:
                return "remote"
        return "unknown"