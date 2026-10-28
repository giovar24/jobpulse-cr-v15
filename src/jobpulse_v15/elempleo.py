"""Adaptador elempleo.com/cr para v1.5 — browser automation via Playwright CDP.

Sitio renderizado client-side (JS pesado: NewRelic, GTM, Prebid, Boomerang).
Requiere sesión de Brave (Playwright CDP). No hay API JSON pública.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, Page

from jobpulse_v15.location_utils import (
    normalize_cr_location,
    normalize_work_mode,
    normalize_employment_type,
    extract_date_from_source_updated,
)

logger = logging.getLogger("jobpulse.elempleo")


class ElempleoFetchError(RuntimeError):
    """Error obteniendo vacantes de elempleo.com/cr."""


class ElempleoOffers(list[dict[str, Any]]):
    """Ofertas del barrido elempleo con conteo de omitidas."""

    def __init__(self, offers: list[dict[str, Any]], *, jobs_skipped: int = 0) -> None:
        super().__init__(offers)
        self.jobs_skipped = jobs_skipped


def _limpiar(t: str) -> str:
    return " ".join((t or "").split())


def _parse_date_relative(txt: str) -> Optional[str]:
    """Convierte 'hace 3 días', '2 weeks ago' a ISO YYYY-MM-DD (aprox)."""
    if not txt:
        return None
    txt = txt.lower().strip()
    now = datetime.now(timezone.utc)
    m = re.search(r"(\d+)\s*(min|minute|minuto)s?", txt)
    if m:
        return (now - timedelta(minutes=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\s*(hour|hora)s?", txt)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\s*(day|dia|dias|día)s?", txt)
    if m:
        return (now - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\s*(week|semana)s?", txt)
    if m:
        return (now - timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\s*(month|mes)s?", txt)
    if m:
        return (now - timedelta(days=int(m.group(1)) * 30)).strftime("%Y-%m-%d")
    # Formato fecha absoluta: "25 de octubre de 2026"
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", txt)
    if m:
        day = int(m.group(1))
        month_str = m.group(2).lower()
        year = int(m.group(3))
        months = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        }
        month = months.get(month_str)
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"
    return None


class ElempleoFetcher:
    """Barrido de elempleo.com/cr via Playwright CDP en el Brave del usuario."""

    BASE_URL = "https://www.elempleo.com/cr/ofertas-empleo/"

    def __init__(self, *, timeout: float = 45.0, request_delay: float = 1.0) -> None:
        if timeout <= 0:
            raise ValueError("timeout debe ser mayor que cero.")
        if request_delay < 0 or request_delay > 10:
            raise ValueError("request_delay debe estar entre 0 y 10 segundos.")
        self.timeout = timeout
        self.request_delay = request_delay

    async def fetch(
        self,
        site: dict[str, Any],
        *,
        pages: int = 1,
        skip_source_job_ids: Optional[set[str]] = None,
        port: int,
    ) -> ElempleoOffers:
        """Barrido de elempleo.com/cr.

        `port`: puerto CDP de Brave (lo pasa el caller desde CLI/main).
        """
        if isinstance(pages, bool) or not isinstance(pages, int):
            raise ValueError("pages debe ser un entero.")
        if pages < 1 or pages > 50:
            raise ValueError("pages debe estar entre 1 y 50.")

        skipped_ids = skip_source_job_ids or set()
        cfg = site.get("site_config") or {}
        country_query = cfg.get("country_query") or "Costa Rica"

        async def _run() -> ElempleoOffers:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
                ctx = browser.contexts[0]
                return await self._fetch_dom(ctx, site, cfg, pages, skipped_ids, country_query)

        return asyncio.run(_run())

    async def _fetch_dom(
        self,
        ctx: BrowserContext,
        site: dict[str, Any],
        cfg: dict[str, Any],
        pages: int,
        skipped_ids: set[str],
        country_query: str,
    ) -> ElempleoOffers:
        offers = []
        skipped = 0
        seen = set()

        for page_num in range(1, pages + 1):
            url = self.BASE_URL if page_num == 1 else f"{self.BASE_URL}?page={page_num}"
            logger.info("Elempleo: pagina %d/%d (%s)", page_num, pages, url)

            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                await page.wait_for_timeout(3000)  # esperar JS

                # Detectar login-wall / interstitial
                if await self._es_login_wall(page):
                    logger.warning("Elempleo %s: login-wall detectado en %s", site.get("site_id"), url)
                    break

                # Extraer tarjetas de resultados
                cards = await page.query_selector_all(".result-item")
                if not cards:
                    logger.info("Elempleo %s: sin tarjetas en pagina %d", site.get("site_id"), page_num)
                    break

                for card in cards:
                    try:
                        # URL del detalle
                        data_url = await card.get_attribute("data-url")
                        if not data_url:
                            continue
                        detail_url = data_url if data_url.startswith("http") else f"https://www.elempleo.com{data_url}"

                        # Título
                        title_el = await card.query_selector("h2.item-title.ee-mod a.js-offer-title")
                        title = _limpiar(await title_el.inner_text()) if title_el else ""
                        if not title:
                            continue

                        # Empresa
                        company_el = await card.query_selector(".item-company a")
                        company = _limpiar(await company_el.inner_text()) if company_el else ""

                        # source_job_id desde la URL
                        source_job_id = self._extract_job_id(detail_url)
                        if not source_job_id:
                            source_job_id = title

                        if source_job_id in seen or source_job_id in skipped_ids:
                            skipped += 1
                            continue
                        seen.add(source_job_id)

                        # Navegar a detalle para extraer ubicación, descripción, etc.
                        detail_data = await self._fetch_detail(ctx, detail_url)

                        location_raw = detail_data.get("location", "")
                        searchable = " ".join(filter(None, [title, company, location_raw]))
                        if country_query.casefold() not in searchable.casefold():
                            continue

                        # Normalizar campos estándar
                        location_norm = normalize_cr_location(location_raw)
                        work_mode = normalize_work_mode(detail_data.get("work_mode"))
                        employment_type = normalize_employment_type(detail_data.get("employment_type"))
                        date_published = extract_date_from_source_updated(
                            detail_data.get("date"), detail_data.get("date")
                        )

                        offers.append({
                            "source_job_id": source_job_id,
                            "source_url": detail_url,
                            "source_updated_at": detail_data.get("date"),
                            "job": {
                                "job_id": f"elempleo-{source_job_id}",
                                "title": title,
                                "company": company or site.get("company_name", ""),
                                "location_raw": location_raw,
                                "country": "CR",
                                "region": location_norm.get("region"),
                                "city": location_norm.get("city"),
                                "work_mode": work_mode,
                                "employment_type": employment_type,
                                "schedule": None,
                                "posting_language": "es",
                                "posting_language_origin": "source",
                                "date_published": date_published,
                                "expires_at": None,
                                "salary_raw": detail_data.get("salary", ""),
                                "salary_min": None,
                                "salary_max": None,
                                "salary_currency": None,
                                "salary_period": None,
                                "description_raw": detail_data.get("description", ""),
                                "requirements_raw": detail_data.get("requirements", ""),
                            },
                            "raw_payload": {"detail_url": detail_url, **detail_data},
                        })

                    except Exception as e:
                        logger.warning("Elempleo error extrayendo tarjeta: %s", e)

                # Paginación: elempleo usa ?page=N
                if page_num >= pages:
                    break

                if self.request_delay:
                    await asyncio.sleep(self.request_delay)

            finally:
                await page.close()

        logger.info("Elempleo %s: %d ofertas, %d omitidas", site.get("site_id"), len(offers), skipped)
        return ElempleoOffers(offers, jobs_skipped=skipped)

    @staticmethod
    def _extract_job_id(url: str) -> Optional[str]:
        """Extrae ID numérico de la URL: /cr/ofertas-trabajo/slug/123456"""
        m = re.search(r"/(\d+)(?:/|$)", url)
        return m.group(1) if m else None

    @staticmethod
    async def _es_login_wall(page: Page) -> bool:
        """Detecta login-wall o interstitial."""
        # Buscar formularios de login
        try:
            if await page.query_selector('input[type="email"]') \
               and await page.query_selector('input[type="password"]'):
                return True
        except Exception:
            pass
        # Textos típicos
        try:
            body = (await page.inner_text("body"))[:2000].lower()
            if any(x in body for x in ("inicia sesion", "iniciar sesion", "sign in", "log in", "acceder")):
                return True
        except Exception:
            pass
        return False

    async def _fetch_detail(self, ctx: BrowserContext, detail_url: str) -> Dict[str, Any]:
        """Navega a la página de detalle y extrae información completa."""
        page = await ctx.new_page()
        data = {
            "location": "",
            "work_mode": "unknown",
            "employment_type": None,
            "date": None,
            "description": "",
            "requirements": "",
            "salary": "",
        }
        try:
            await page.goto(detail_url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            await page.wait_for_timeout(2000)

            # Título (verificación)
            title_el = await page.query_selector("h1")
            if title_el:
                _limpiar(await title_el.inner_text())

            # Empresa
            company_el = await page.query_selector('[class*="company"] a') or await page.query_selector('[class*="company"]')
            if company_el:
                _limpiar(await company_el.inner_text())

            # Ubicación - buscar en varios selectores
            loc_selectors = [
                '[class*="location"]',
                '[class*="ubicacion"]',
                '.job-location',
                '[data-testid="location"]',
            ]
            for sel in loc_selectors:
                el = await page.query_selector(sel)
                if el:
                    text = _limpiar(await el.inner_text())
                    if text:
                        data["location"] = text
                        break

            # Modalidad de trabajo
            mode_selectors = [
                '[class*="modalidad"]',
                '[class*="work-mode"]',
                '[class*="tipo-contrato"]',
                '[class*="tipo-trabajo"]',
            ]
            for sel in mode_selectors:
                el = await page.query_selector(sel)
                if el:
                    text = _limpiar(await el.inner_text()).lower()
                    if "remoto" in text or "remote" in text:
                        data["work_mode"] = "remote"
                    elif "hibrido" in text or "híbrido" in text or "hybrid" in text:
                        data["work_mode"] = "hybrid"
                    elif "presencial" in text or "on-site" in text or "onsite" in text:
                        data["work_mode"] = "onsite"
                    break

            # Tipo de empleo
            type_selectors = [
                '[class*="tipo-empleo"]',
                '[class*="employment-type"]',
                '[class*="tipo-contrato"]',
                '[class*="jornada"]',
            ]
            for sel in type_selectors:
                el = await page.query_selector(sel)
                if el:
                    data["employment_type"] = _limpiar(await el.inner_text())
                    break

            # Fecha de publicación
            date_selectors = [
                '[class*="fecha"]',
                '[class*="date"]',
                '[class*="publicado"]',
                '[class*="posted"]',
            ]
            for sel in date_selectors:
                el = await page.query_selector(sel)
                if el:
                    text = _limpiar(await el.inner_text())
                    parsed = _parse_date_relative(text)
                    if parsed:
                        data["date"] = parsed
                    break

            # Descripción
            desc_selectors = [
                '[class*="description"]',
                '[class*="detalle"]',
                '.job-description',
                '.oferta-detalle',
            ]
            for sel in desc_selectors:
                el = await page.query_selector(sel)
                if el:
                    html = await el.inner_html()
                    data["description"] = self._html_to_text(html)
                    break

            # Requisitos
            req_selectors = [
                '[class*="requisito"]',
                '[class*="requirement"]',
                '.requisitos',
            ]
            for sel in req_selectors:
                el = await page.query_selector(sel)
                if el:
                    html = await el.inner_html()
                    data["requirements"] = self._html_to_text(html)
                    break

            # Salario
            salary_selectors = [
                '[class*="salary"]',
                '[class*="salario"]',
                '[class*="remuneracion"]',
            ]
            for sel in salary_selectors:
                el = await page.query_selector(sel)
                if el:
                    data["salary"] = _limpiar(await el.inner_text())
                    break

        except Exception as e:
            logger.warning("Elempleo error en detalle %s: %s", detail_url, e)
        finally:
            await page.close()
        return data

    @staticmethod
    def _html_to_text(html: str) -> str:
        if not html:
            return ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return " ".join(soup.get_text(" ", strip=True).split())