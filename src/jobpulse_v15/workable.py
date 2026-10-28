"""Adaptador para la API publica de tableros Workable (formato jobs.md).

Workable cambi� su API: ahora expone las vacantes en formato Markdown
en `https://apply.workable.com/{token}/jobs.md` con una tabla.
Cada fila tiene un enlace "Details" a la p�gina de detalle (tamb�en .md).
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from jobpulse_v15.ingestion import IngestionError

logger = logging.getLogger("jobpulse.workable")


class WorkableFetchError(IngestionError):
    """Error al consultar tablero Workable."""


class WorkableOffers(list[dict[str, Any]]):
    """Ofertas filtradas con conteo de anuncios omitidos por estado manual."""

    def __init__(
        self, offers: list[dict[str, Any]], *, jobs_skipped: int = 0
    ) -> None:
        super().__init__(offers)
        self.jobs_skipped = jobs_skipped


class WorkableFetcher:
    """Consulta un tablero Workable (formato jobs.md) y adapta sus vacantes al formato v1.5."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        if timeout <= 0:
            raise ValueError("timeout debe ser mayor que cero.")
        self.timeout = timeout

    def fetch(
        self,
        site: dict[str, Any],
        *,
        pages: int | None = None,
        skip_source_job_ids: set[str] | None = None,
    ) -> WorkableOffers:
        token = self._board_token(site.get("base_url"))
        config = site.get("site_config") or {}
        if not isinstance(config, dict):
            raise ValueError("La configuracion Workable debe ser un objeto.")
        country_query = config.get("country_query") or "Costa Rica"
        if not isinstance(country_query, str) or not country_query.strip():
            raise ValueError("country_query debe contener texto.")

        # 1. Obtener lista principal (jobs.md)
        list_url = f"https://apply.workable.com/{token}/jobs.md"
        logger.debug("Workable: solicitando lista %s", list_url)
        list_md = self._request_text(list_url)

        # 2. Parsear tabla markdown
        jobs = self._parse_jobs_table(list_md, token)
        if not jobs:
            logger.info("Workable %s: no se encontraron vacantes en la tabla", token)
            return WorkableOffers([], jobs_skipped=0)

        # 3. Para cada job, obtener detalle y filtrar por pa�s
        offers = []
        skipped = 0
        seen_ids: set[str] = set()
        skipped_ids = skip_source_job_ids or set()

        for job in jobs:
            source_job_id = job["source_job_id"]
            if source_job_id in seen_ids:
                continue

            title = job["title"]
            location_raw = job["location_raw"]
            detail_url = job["detail_url"]

            searchable = " ".join(filter(None, [title, location_raw]))
            if country_query.casefold() not in searchable.casefold():
                continue

            if source_job_id in seen_ids:
                continue

            seen_ids.add(source_job_id)

            if source_job_id in skipped_ids:
                skipped += 1
                continue

            # 4. Obtener detalle del job
            detail_md = self._request_text(detail_url)
            description, requirements, work_mode, employment_type, published = self._parse_job_detail(detail_md)

            combined = " ".join(part for part in (description, requirements) if part)

            offers.append(
                {
                    "source_job_id": source_job_id,
                    "source_url": detail_url,
                    "source_updated_at": published,
                    "job": {
                        "job_id": f"workable-{token}-{source_job_id}",
                        "title": title,
                        "company": (
                            self._optional_text(site.get("company_name"))
                            or self._optional_text(site.get("site_name"))
                        ),
                        "location_raw": location_raw,
                        "country": self._optional_text(site.get("country")),
                        "work_mode": work_mode,
                        "employment_type": employment_type,
                        "date_published": published[:10] if published and len(published) >= 10 else None,
                        "posting_language": "undetermined",
                        "posting_language_origin": "unknown",
                        "description_raw": combined or None,
                    },
                    "raw_payload": job,
                }
            )

        return WorkableOffers(offers, jobs_skipped=skipped)

    # --- Parsing ---

    def _parse_jobs_table(self, markdown: str, token: str) -> list[dict[str, Any]]:
        """Parsea la tabla markdown de jobs.md.

        Formato esperado:
        | Title | Department | Location | Type | Salary | Posted | Details |
        |-------|-----------|----------|------|--------|--------|---------|
        | Job Title | Dept | Country (Remote) | Full-time | ... | 2026-10-27 | [View](url) |
        """
        jobs = []

        # Encontrar l�neas de la tabla (despu�s del header y separator)
        lines = markdown.split("\n")
        in_table = False
        for line in lines:
            line = line.strip()
            if line.startswith("| Title |") or line.startswith("| Title|"):
                in_table = True
                continue
            if in_table and line.startswith("|---") or line.startswith("| ---"):
                continue
            if in_table and line.startswith("|"):
                # Parsear fila
                cells = [c.strip() for c in line.split("|")[1:-1]]  # quitar vac�os al inicio/final
                if len(cells) >= 7:
                    title = cells[0]
                    department = cells[1]
                    location = cells[2]
                    job_type = cells[3]
                    salary = cells[4]
                    posted = cells[5]
                    details_cell = cells[6]

                    # Extraer URL del enlace [View](url)
                    url_match = re.search(r"\[View\]\(([^)]+)\)", details_cell)
                    detail_url = url_match.group(1) if url_match else None
                    if not detail_url:
                        continue

                    # El source_job_id viene de la URL del detalle
                    # Formato: https://apply.workable.com/{token}/jobs/view/{id}.md
                    id_match = re.search(r"/view/([A-Za-z0-9]+)\.md", detail_url)
                    source_job_id = id_match.group(1) if id_match else detail_url

                    jobs.append({
                        "source_job_id": source_job_id,
                        "title": title,
                        "department": department,
                        "location_raw": location,
                        "job_type": job_type,
                        "salary": salary,
                        "posted": posted,
                        "detail_url": detail_url,
                    })

            elif in_table and not line.startswith("|"):
                # Fin de la tabla
                break

        return jobs

    def _parse_job_detail(self, markdown: str) -> tuple[str | None, str | None, str, str | None, str | None]:
        """Parsea la p�gina de detalle del job (markdown).

        Retorna: (description, requirements, work_mode, employment_type, published_date)
        """
        description = None
        requirements = None
        work_mode = "unknown"
        employment_type = None
        published = None

        # work_mode desde l�nea "Workplace: remote/hybrid/on-site"
        wm_match = re.search(r"(?i)\*\*Workplace:\*\*\s*(\w+)", markdown)
        if wm_match:
            wm = wm_match.group(1).lower()
            if wm == "remote":
                work_mode = "remote"
            elif wm == "hybrid":
                work_mode = "hybrid"
            elif wm in ("on-site", "onsite"):
                work_mode = "onsite"

        # employment_type desde l�nea de header o Type
        # Header: "> Company · Location · Full-time · Posted date"
        type_match = re.search(r">\s*[^·]+\s·\s*[^·]+\s·\s*([^·]+)\s·\s*Posted", markdown)
        if type_match:
            employment_type = type_match.group(1).strip()
        else:
            # Buscar en l�nea Type de la tabla del listado (ya no disponible aqu�)
            pass

        # published date
        pub_match = re.search(r"Posted\s+(\d{4}-\d{2}-\d{2})", markdown)
        if pub_match:
            published = pub_match.group(1)

        # Description y Requirements - buscar secciones ## Description y ## Requirements
        # Workable usa ## Description y ## Requirements como headers
        desc_match = re.search(r"## Description\s*\n(.*?)(?:\n## |\n---|\Z)", markdown, re.DOTALL | re.IGNORECASE)
        if desc_match:
            description = self._md_to_text(desc_match.group(1))

        req_match = re.search(r"## Requirements\s*\n(.*?)(?:\n## |\n---|\Z)", markdown, re.DOTALL | re.IGNORECASE)
        if req_match:
            requirements = self._md_to_text(req_match.group(1))

        # Fallback: si no hay headers, tomar todo el contenido
        if not description and not requirements:
            # Remover header metadata lines
            content = re.sub(r"^>.*\n", "", markdown, flags=re.MULTILINE)
            content = re.sub(r"^\*\*.*?\*\*\s*.*\n", "", content, flags=re.MULTILINE)
            content = content.strip()
            if content:
                description = self._md_to_text(content)

        return description, requirements, work_mode, employment_type, published

    @staticmethod
    def _md_to_text(md: str) -> str:
        """Convierte markdown simple a texto plano."""
        if not md:
            return ""
        # Remover links [text](url) -> text
        md = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
        # Remover bold/italic
        md = re.sub(r"\*\*([^*]+)\*\*", r"\1", md)
        md = re.sub(r"\*([^*]+)\*", r"\1", md)
        # Remover headers
        md = re.sub(r"^#+\s*", "", md, flags=re.MULTILINE)
        # Remover horizontal rules
        md = re.sub(r"^---+\s*$", "", md, flags=re.MULTILINE)
        # Normalizar whitespace
        return " ".join(md.split())

    # --- HTTP ---

    def _request_text(self, url: str) -> str:
        request = Request(
            url,
            headers={"Accept": "text/markdown,text/plain,*/*", "User-Agent": "JobPulse-CR/1.5"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            raise WorkableFetchError(
                f"Workable respondio HTTP {exc.code} para {url}."
            ) from exc
        except (URLError, TimeoutError, OSError, UnicodeDecodeError) as exc:
            raise WorkableFetchError(
                f"No se pudo consultar Workable {url}: {exc}"
            ) from exc

    # --- Helpers ---

    @staticmethod
    def _board_token(value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("La URL Workable debe ser texto.")
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").casefold()
        if (
            parsed.scheme.casefold() != "https"
            or hostname != "apply.workable.com"
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("La URL debe apuntar a un tablero HTTPS de Workable.")
        parts = [part for part in parsed.path.split("/") if part]
        if not parts or not re.fullmatch(r"^[A-Za-z0-9_-]+$", parts[0]):
            raise ValueError(
                "La URL Workable no contiene un token de tablero valido."
            )
        return parts[0]

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None