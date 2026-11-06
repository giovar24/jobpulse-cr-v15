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
        # Cada oferta del listado abre su detalle (una navegacion por
        # oferta): con 50 avisos por pagina el barrido tardaria minutos.
        # `site_config["max_ofertas"]` lo acota (sin tope por defecto).
        max_ofertas = cfg.get("max_ofertas")
        max_ofertas = int(max_ofertas) if max_ofertas else 0

        async def _run() -> ElempleoOffers:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
                ctx = browser.contexts[0]
                return await self._fetch_dom(
                    ctx, site, cfg, pages, skipped_ids, country_query, max_ofertas
                )

        # `fetch` ya es una corrutina: await directo. Un `asyncio.run()`
        # aqui fallaba con "asyncio.run() cannot be called from a running
        # event loop" (doble envoltura: el caller envuelve la corrutina).
        return await _run()

    async def _fetch_dom(
        self,
        ctx: BrowserContext,
        site: dict[str, Any],
        cfg: dict[str, Any],
        pages: int,
        skipped_ids: set[str],
        country_query: str,
        max_ofertas: int = 0,
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

                # Extraer tarjetas de resultados.
                # OJO (verificado 2026-11-05): `.ee_list-item` NO son las
                # ofertas: es el menu lateral ("Todos los anuncios de
                # empleo", filtros...). Las ofertas siguen en
                # `.result-item` con `.js-area-bind.area-bind` dentro.
                cards = await page.query_selector_all(".result-item")
                if not cards:
                    cards = await page.query_selector_all(
                        ".js-area-bind.area-bind, [data-url*='/ofertas-trabajo/']"
                    )
                if not cards:
                    logger.info("Elempleo %s: sin tarjetas en pagina %d", site.get("site_id"), page_num)
                    break

                for card in cards:
                    if max_ofertas and len(offers) >= max_ofertas:
                        logger.info(
                            "Elempleo %s: tope de %d oferta(s) alcanzado.",
                            site.get("site_id"), max_ofertas,
                        )
                        break
                    try:
                        # El data-url está en el div interno .js-area-bind.area-bind
                        inner = await card.query_selector(".js-area-bind.area-bind")
                        if inner is None:
                            inner = card
                        data_url = await inner.get_attribute("data-url")
                        if not data_url:
                            continue
                        detail_url = data_url if data_url.startswith("http") else f"https://www.elempleo.com{data_url}"

                        # Título y empresa vienen en datalayertag (JSON en atributo)
                        datalayer = await inner.get_attribute("datalayertag")
                        title = ""
                        company = ""
                        if datalayer:
                            import json
                            try:
                                dl = json.loads(datalayer)
                                products = dl.get("ecommerce", {}).get("click", {}).get("products", [])
                                if products:
                                    p = products[0]
                                    title = p.get("name", "").strip()
                                    company = p.get("brand", "").strip()
                                    # brand a veces es "elempleo", buscar dimension7
                                    if company == "elempleo":
                                        company = p.get("dimension7", "").strip()
                            except Exception:
                                pass

                        # Fallback: extraer del DOM si datalayer falló
                        # (hoy el listado ya NO trae `datalayertag`).
                        if not title:
                            title_el = await card.query_selector(
                                "h2.item-title.ee-mod a.js-offer-title, "
                                "h2.item-title a, .js-offer-title"
                            )
                            title = _limpiar(await title_el.inner_text()) if title_el else ""
                        if not title:
                            continue

                        if not company:
                            for selector in (
                                ".js-offer-company",
                                ".company-name-text",
                                ".item-company a",
                            ):
                                company_el = await card.query_selector(selector)
                                if company_el:
                                    company = _limpiar(await company_el.inner_text())
                                    if company:
                                        break

                        # Ciudad de la ficha (`.js-offer-city`): es mas
                        # precisa que la primera ciudad que aparezca en el
                        # texto del detalle (que puede ser otra).
                        ciudad_ficha = ""
                        ciudad_el = await card.query_selector(
                            ".js-offer-city, .info-city"
                        )
                        if ciudad_el is not None:
                            ciudad_ficha = _limpiar(await ciudad_el.inner_text())

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

                        location_raw = detail_data.get("location", "") or ciudad_ficha
                        if ciudad_ficha and ciudad_ficha != location_raw:
                            location_raw = ciudad_ficha
                        # El filtro de pais mira el PAIS del aviso: la
                        # ubicacion es el canton ("San Jose") y el pais
                        # ("Costa Rica") va aparte (verificado 2026-11-05:
                        # sin esto se descartaban TODAS las ofertas).
                        if not self._pasa_filtro_pais(
                            title, company, location_raw,
                            detail_data.get("country", ""), country_query,
                        ):
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

                if max_ofertas and len(offers) >= max_ofertas:
                    break

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
    def _pasa_filtro_pais(
        title: str,
        company: str,
        location: str,
        country: str,
        country_query: str,
    ) -> bool:
        """¿El aviso es del pais buscado?

        La ubicacion es el CANTON ("San Jose") y el pais ("Costa Rica")
        va aparte: mirar solo la ubicacion descartaba todas las ofertas
        (verificado 2026-11-05).
        """
        if not country_query:
            return True
        searchable = " ".join(
            filter(None, [title, company, location, country])
        )
        return country_query.casefold() in searchable.casefold()

    @staticmethod
    async def _es_login_wall(page: Page) -> bool:
        """Detecta un MURO DE LOGIN real (no el boton del encabezado).

        OJO (verificado 2026-11-05): el encabezado de elempleo.com SIEMPRE
        trae el enlace "Inicia sesion" (el boton de entrar). Antes se
        buscaba esa palabra en el texto de la pagina, asi que el barrido
        se cortaba en la pagina 1 y el sitio daba 0 avisos SIEMPRE.

        Un muro de login de verdad es un FORMULARIO de acceso (o la
        pagina de "Iniciar sesion" sin avisos). Si la pagina trae
        tarjetas de avisos, NO hay muro.
        """
        try:
            if await page.query_selector('input[type="password"]'):
                return True
        except Exception:
            pass
        try:
            if await page.query_selector("form[action*='iniciar-sesion']"):
                return True
        except Exception:
            pass
        # Si hay resultados, no hay muro (los avisos son la prueba).
        try:
            if await page.query_selector(
                ".result-item, .ee_list-oferta, [data-url*='/ofertas-trabajo/']"
            ):
                return False
        except Exception:
            pass
        try:
            url = (page.url or "").lower()
            if "/iniciar-sesion" in url or "/cross/iniciar" in url:
                return True
        except Exception:
            pass
        try:
            body = (await page.inner_text("body"))[:2000].lower()
        except Exception:
            return False
        return (
            "inicia sesion" in body
            or "iniciar sesion" in body
            or "sign in" in body
            or "log in" in body
        ) and "resultado" not in body and "oferta" not in body

    async def _fetch_detail(self, ctx: BrowserContext, detail_url: str) -> Dict[str, Any]:
        """Navega a la página de detalle y extrae información completa del body text."""
        page = await ctx.new_page()
        data = {
            "location": "",
            "country": "",
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

            # Obtener todo el texto de la página para extraer con regex
            body_text = await page.inner_text("body")

            # 1. Ubicación - buscar provincia/cantón en el cuerpo
            location_patterns = [
                r"\b(San José|Alajuela|Cartago|Heredia|Guanacaste|Limón|Puntarenas)\b",
                r"\b(San Jose|Limon)\b",
            ]
            for pattern in location_patterns:
                m = re.search(pattern, body_text, re.IGNORECASE)
                if m:
                    data["location"] = m.group(1).title()
                    break

            # 1.b País - el aviso dice "CRC Costa Rica" (verificado
            # 2026-11-05). El filtro de país lo necesita: la ubicación
            # es el cantón, no el país.
            country_match = re.search(
                r"\b(Costa Rica|Panam[áa]|Nicaragua|Honduras|Guatemala|"
                r"El Salvador|Rep[úu]blica Dominicana|Espa[ñn]a|"
                r"Estados Unidos|Colombia|M[ée]xico)\b",
                body_text,
                re.IGNORECASE,
            )
            if country_match:
                data["country"] = country_match.group(1)

            # 2. Salario - buscar patrón monetario costarricense
            salary_match = re.search(r"[¢$]\s*[\d\.,]+\s*(?:a|hasta)\s*[\d\.,]+\s*(?:mil|millón|millones)?", body_text)
            if not salary_match:
                salary_match = re.search(r"[¢$]\s*[\d\.,]+\s*(?:mil|millón|millones)?", body_text)
            if salary_match:
                data["salary"] = _limpiar(salary_match.group(0))

            # 3. Fecha de publicación - "Publicado 28 Oct 2026"
            date_match = re.search(r"Publicado\s+(\d{1,2}\s+\w+\s+\d{4})", body_text, re.IGNORECASE)
            if date_match:
                data["date"] = self._parse_date_es(date_match.group(1))

            # 4. Modalidad de trabajo - buscar palabras clave en el cuerpo
            body_lower = body_text.lower()
            if "remoto" in body_lower or "remote" in body_lower or "teletrabajo" in body_lower:
                data["work_mode"] = "remote"
            elif "hibrido" in body_lower or "híbrido" in body_lower or "hybrid" in body_lower or "mixto" in body_lower:
                data["work_mode"] = "hybrid"
            elif "presencial" in body_lower or "on-site" in body_lower or "onsite" in body_lower or "en sitio" in body_lower:
                data["work_mode"] = "onsite"

            # 5. Tipo de empleo - buscar en el cuerpo
            if "contrato indefinido" in body_lower:
                data["employment_type"] = "Full-time"
            elif "contrato definido" in body_lower or "tiempo determinado" in body_lower:
                data["employment_type"] = "Contract"
            elif "medio tiempo" in body_lower or "part time" in body_lower or "part-time" in body_lower:
                data["employment_type"] = "Part-time"
            elif "tiempo completo" in body_lower or "full time" in body_lower or "full-time" in body_lower:
                data["employment_type"] = "Full-time"

            # 6. Descripción - el bloque del aviso (`.description-block`)
            #    es mas fiable que el texto plano (verificado 2026-11-05).
            for selector in (
                ".description-block p span",
                ".description-block p",
                ".js-description p span",
                ".js-description",
            ):
                desc_el = await page.query_selector(selector)
                if desc_el is not None:
                    texto = _limpiar(await desc_el.inner_text())
                    if texto:
                        data["description"] = texto
                        break
            if not data["description"]:
                desc_match = re.search(
                    r"Descripción general\s*(.*?)(?:\n\s*(?:Habilidades|Requisitos|Competencias|Datos|$))",
                    body_text, re.DOTALL | re.IGNORECASE,
                )
                if desc_match:
                    data["description"] = _limpiar(desc_match.group(1))

            # 7. Requisitos - el aviso no tiene seccion "Requisitos": los
            #    requisitos son las ETIQUETAS de `.requirements-content`
            #    (competencias, educacion, experiencia).
            etiquetas = await page.query_selector_all(
                ".requirements-content li .info-tag-not-select"
            )
            if etiquetas:
                textos = []
                for etiqueta in etiquetas:
                    try:
                        texto = _limpiar(await etiqueta.inner_text())
                    except Exception:
                        texto = ""
                    if texto and texto not in textos:
                        textos.append(texto)
                if textos:
                    data["requirements"] = "; ".join(textos)
            if not data["requirements"]:
                req_match = re.search(
                    r"Requisitos\s*(.*?)(?:\n\s*(?:Competencias|Datos|Habilidades|Descripción|$))",
                    body_text, re.DOTALL | re.IGNORECASE,
                )
                if req_match:
                    data["requirements"] = _limpiar(req_match.group(1))

        except Exception as e:
            logger.warning("Elempleo error en detalle %s: %s", detail_url, e)
        finally:
            await page.close()
        return data

    @staticmethod
    def _parse_date_es(txt: str) -> Optional[str]:
        """Convierte '28 Oct 2026' -> '2026-10-28'."""
        if not txt:
            return None
        txt = txt.strip()
        months = {
            "ene": 1, "enero": 1,
            "feb": 2, "febrero": 2,
            "mar": 3, "marzo": 3,
            "abr": 4, "abril": 4,
            "may": 5, "mayo": 5,
            "jun": 6, "junio": 6,
            "jul": 7, "julio": 7,
            "ago": 8, "agosto": 8,
            "sep": 9, "septiembre": 9, "set": 9,
            "oct": 10, "octubre": 10,
            "nov": 11, "noviembre": 11,
            "dic": 12, "diciembre": 12,
        }
        m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", txt, re.IGNORECASE)
        if m:
            day = int(m.group(1))
            month_str = m.group(2).lower()[:3]
            year = int(m.group(3))
            month = months.get(month_str)
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"
        return None

    @staticmethod
    def _html_to_text(html: str) -> str:
        if not html:
            return ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return " ".join(soup.get_text(" ", strip=True).split())