"""Adaptador LinkedIn (linkedin.com) para v1.5 — versión probada del proyecto principal.

DÓNDE ESTÁN LOS AVISOS (verificado 2026-11-05 en vivo):

- El listado público ``https://www.linkedin.com/jobs/search/?keywords=..&location=..``
  responde 200 por HTTP simple y trae las tarjetas en ``div.base-card``
  (``data-entity-urn="urn:li:jobPosting:<id>"``) con
  ``h3.base-search-card__title``, ``h4.base-search-card__subtitle``,
  ``span.job-search-card__location``, ``time.job-search-card__listdate``
  y ``a.base-card__full-link`` (enlace ``/jobs/view/<slug>-<id>``).
- La misma página trae un ``script[type="application/ld+json"]`` de tipo
  ``ItemList`` con título, empresa, ubicación y URL de cada aviso: es la
  vía de respaldo cuando el HTML cambia de clases.
- ``/jobs/search-results/`` ya NO sirve el listado (devuelve 999) y el
  navegador sin sesión recibe un ``authwall``: por eso el listado se
  pide por HTTP y el navegador queda como REFUERZO (si hay sesión de
  Brave, se fusiona lo que traiga encima).

REGLAS:
- El detalle se saca del endpoint público ``jobs-guest`` (sin sesión) y,
  si hace falta, de la página del aviso con las cookies de Brave.
- La sesión de Brave se reusa (login manual una vez); el SSO Google queda
  como RECURSO opt-in solo si la sesión se cae (LinkedIn es agresivo con
  logins automatizados).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import quote_plus

import httpx
from playwright.async_api import Page

from jobpulse_v15.location_utils import normalize_cr_location
from jobpulse_v15.requiere_login import RequiereLoginError, mensaje_requiere_login

logger = logging.getLogger("jobpulse.linkedin")

DATE_RE = re.compile(
    r"(hace\s+\d+\s*(min|minuto|hora|día|dias|semana|mes)|"
    r"\d+\s*(min|minute|hour|day|week|month)\s*ago)",
    re.IGNORECASE,
)

_MAX_PAGES = 10

# Listado publico de vacantes (NO `jobs-guest`, NO `search-results`).
LISTADO_URL = "https://www.linkedin.com/jobs/search/"
# Resultados por pagina en el listado publico.
RESULTADOS_POR_PAGINA = 25

# Selectores de tarjeta, del mas estable al mas especifico. LinkedIn cambia
# las clases de vez en cuando: por eso se aceptan varias.
_SELECTORES_TARJETA = (
    "div.base-card",
    "li[data-occludable-job-id]",
    "li[data-job-id]",
    "div[data-job-id]",
    ".job-card-container",
    "[data-entity-urn*='jobPosting']",
)


class LinkedInFetchError(RuntimeError):
    """Error obteniendo vacantes de LinkedIn."""


class LinkedInOffers(list[dict[str, Any]]):
    def __init__(self, offers: list[dict[str, Any]], *, jobs_skipped: int = 0) -> None:
        super().__init__(offers)
        self.jobs_skipped = jobs_skipped


def _extract_date(html: str) -> str:
    m = re.search(r"(?is)posted-time-ago[^>]*>([^<]+)<", html)
    if m and m.group(1).strip():
        return m.group(1).strip()
    m = re.search(r"(?i)(\d+\s+(?:minute|hour|day|week|month)s?\s+ago)", html)
    if m:
        return m.group(1)
    m = re.search(r"(?i)(hace\s+\d+\s+(?:minuto|hora|d[ií]a|semana|mes)\w*)", html)
    if m:
        return m.group(1)
    return ""


def _numeric_id(job_id: str | None, link: str | None) -> str:
    if job_id:
        m = re.search(r"(\d{6,})", job_id)
        if m:
            return m.group(1)
    if link:
        m = re.search(r"/jobs/view/(\d+)", link)
        if m:
            return m.group(1)
    return ""


def _parse_date_relative(txt: str) -> str | None:
    """Convierte '1 day ago', 'hace 2 días' a ISO YYYY-MM-DD (aprox)."""
    if not txt:
        return None
    from datetime import datetime, timedelta, timezone
    txt = txt.lower().strip()
    now = datetime.now(timezone.utc)
    # Patrones: "X days ago", "hace X días", "X hours ago", etc.
    m = re.search(r"(\d+)\s*(min|minute|minuto)s?", txt)
    if m:
        return (now - timedelta(minutes=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\s*(hour|hora)s?", txt)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\s*(day|día|dias)s?", txt)
    if m:
        return (now - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\s*(week|semana)s?", txt)
    if m:
        return (now - timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\s*(month|mes)s?", txt)
    if m:
        return (now - timedelta(days=int(m.group(1)) * 30)).strftime("%Y-%m-%d")
    return None


def _split_requirements(text: str) -> tuple[str, str]:
    """Separa descripción de requisitos si vienen juntos."""
    if not text:
        return "", ""
    # Buscar separadores comunes
    for sep in ["\n\nRequisitos", "\n\nRequirements", "\nRequisitos:", "\nRequirements:"]:
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip(), sep.replace("\n", "").strip() + " " + parts[1].strip()
    return text, ""


# --------------------------------------------------------------------- parseo
# Funciones PURAS (sin red y sin navegador): se pueden testear con el HTML
# real que devolvio LinkedIn el 2026-11-05.


def _texto(elemento: Any) -> str:
    """Texto de un elemento de BeautifulSoup, con espacios normalizados."""
    if elemento is None:
        return ""
    texto = elemento.get_text(" ", strip=True) if hasattr(elemento, "get_text") else str(elemento)
    return " ".join(texto.split())


def _id_de_urn(urn: str | None) -> str:
    """``urn:li:jobPosting:4474290121`` -> ``4474290121``."""
    match = re.search(r"jobPosting:(\d+)", urn or "")
    return match.group(1) if match else ""


def _id_de_url(url: str | None) -> str:
    """ID numerico del aviso a partir de ``/jobs/view/<slug>-<id>``.

    El slug puede traer numeros (``ref%23258081``): el ID es SIEMPRE el
    ULTIMO grupo de 6+ digitos de la URL.
    """
    if not url:
        return ""
    limpio = url.split("?")[0].split("#")[0]
    grupos = re.findall(r"(\d{6,})", limpio)
    return grupos[-1] if grupos else ""


def _item_de_tarjeta(tarjeta: Any) -> Dict[str, Any] | None:
    """Convierte una tarjeta del listado en el diccionario que usa el fetch."""
    enlace = tarjeta.select_one("a.base-card__full-link[href*='/jobs/view/']")
    if enlace is None:
        enlace = tarjeta.select_one("a[href*='/jobs/view/']")
    href = str(enlace.get("href") or "") if enlace is not None else ""
    link = href.split("?")[0]

    job_id = _id_de_urn(tarjeta.get("data-entity-urn")) or _id_de_url(link)

    titulo = (
        _texto(tarjeta.select_one("h3.base-search-card__title"))
        or _texto(tarjeta.select_one(".base-search-card__title"))
        or _texto(tarjeta.select_one("h3"))
        or _texto(tarjeta.select_one("a.base-card__full-link span.sr-only"))
    )
    empresa = (
        _texto(tarjeta.select_one("h4.base-search-card__subtitle"))
        or _texto(tarjeta.select_one(".base-search-card__subtitle"))
        or _texto(tarjeta.select_one(".artdeco-entity-lockup__subtitle"))
    )
    ubicacion = (
        _texto(tarjeta.select_one("span.job-search-card__location"))
        or _texto(tarjeta.select_one(".job-search-card__location"))
    )
    if not ubicacion:
        metadatos = tarjeta.select_one(".base-search-card__metadata")
        if metadatos is not None:
            fecha_texto = _texto(metadatos.select_one("time"))
            ubicacion = _texto(metadatos).replace(fecha_texto, "").strip(" ·,")

    fecha = ""
    momento = tarjeta.select_one("time")
    if momento is not None:
        fecha = str(momento.get("datetime") or "").strip() or _texto(momento)

    if not titulo or not link:
        return None
    return {
        "job_id": job_id,
        "titulo": titulo,
        "empresa": empresa,
        "ubicacion_oferta": ubicacion,
        "fecha_publicacion": fecha,
        "link": link,
    }


def _tarjetas_html(html: str) -> List[Dict[str, Any]]:
    """Tarjetas del listado (`div.base-card` y familia)."""
    if not html:
        return []
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    tarjetas: List[Dict[str, Any]] = []
    vistas: set[str] = set()
    for selector in _SELECTORES_TARJETA:
        for tarjeta in soup.select(selector):
            item = _item_de_tarjeta(tarjeta)
            if item is None:
                continue
            clave = item["job_id"] or item["link"]
            if clave in vistas:
                continue
            vistas.add(clave)
            tarjetas.append(item)
    return tarjetas


def _json_ld(html: str) -> List[Dict[str, Any]]:
    """Listado desde el JSON-LD `ItemList` (respaldo si cambian las clases)."""
    if not html:
        return []
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
    for script in soup.select("script[type='application/ld+json']"):
        try:
            datos = json.loads(script.string or script.get_text() or "{}")
        except (TypeError, ValueError):
            continue
        bloques = datos if isinstance(datos, list) else [datos]
        for bloque in bloques:
            if not isinstance(bloque, dict):
                continue
            candidatos = [bloque]
            grafo = bloque.get("@graph")
            if isinstance(grafo, list):
                candidatos.extend(grafo)
            for candidato in candidatos:
                if not isinstance(candidato, dict):
                    continue
                if candidato.get("@type") != "ItemList":
                    continue
                for elemento in candidato.get("itemListElement") or []:
                    if not isinstance(elemento, dict):
                        continue
                    url = str(elemento.get("url") or "").split("?")[0]
                    titulo = str(elemento.get("name") or "").strip()
                    if not url or not titulo:
                        continue
                    items.append({
                        "job_id": _id_de_url(url),
                        "titulo": titulo,
                        "empresa": str(
                            elemento.get("disambiguatingDescription") or ""
                        ).strip(),
                        "ubicacion_oferta": str(
                            elemento.get("description") or ""
                        ).strip(),
                        "fecha_publicacion": "",
                        "link": url,
                    })
    return items


def _listado_desde_html(html: str) -> List[Dict[str, Any]]:
    """Listado de avisos: primero el DOM, luego el JSON-LD."""
    tarjetas = _tarjetas_html(html)
    if tarjetas:
        return tarjetas
    return _json_ld(html)



class LinkedInFetcher:
    """Scraper LinkedIn con sesión Brave + enriquecimiento HTTP."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        request_delay: float = 1.5,
        brave_bin: str | None = None,
        brave_perfil: str | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout debe ser mayor que cero.")
        if request_delay < 0 or request_delay > 10:
            raise ValueError("request_delay debe estar entre 0 y 10 segundos.")
        self.timeout = timeout
        self.request_delay = request_delay
        self.brave_bin = brave_bin
        self.brave_perfil = brave_perfil
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        }

    def _muro_login(self, page: Page) -> bool:
        try:
            url = (page.url or "").lower()
        except Exception:
            return False
        return "authwall" in url or "/login" in url

    async def _fetch_details_guest(
        self, client: httpx.AsyncClient, job_id: str
    ) -> Tuple[Dict[str, Any], bool]:
        """Endpoint público 'jobs-guest' suele devolver descripción sin sesión.

        Devuelve ``(detalles, limitado)``: ``limitado`` dice que LinkedIn
        respondió 429 (rate limit). Medido 2026-11-05: sin espera el
        endpoint aguanta ~10 peticiones seguidas y despues da 429; con
        1,5 s entre peticiones aguanta todas. Con un 429 NO se prueba
        enseguida la otra URL (seria el doble de trafico y otro 429):
        se espera y se reintenta.
        """
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        for intento in range(2):
            try:
                response = await client.get(url)
            except Exception as e:
                logger.warning(f"LinkedIn guest detail failed for {job_id}: {e}")
                return {}, False
            if response.status_code == 429:
                espera = 8.0 * (intento + 1)
                logger.warning(
                    "LinkedIn: 429 en el detalle de %s; esperando %.0fs.",
                    job_id, espera,
                )
                await asyncio.sleep(espera)
                continue
            if response.status_code != 200:
                return {}, False
            html = response.text
            patterns = [
                r'<div class="[^"]*show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>',
                r'<div class="[^"]*description__text[^"]*"[^>]*>(.*?)</div>',
                r'<section class="[^"]*description[^"]*"[^>]*>(.*?)</section>',
            ]
            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                if match:
                    desc = self._html_to_text(match.group(1))
                    if desc:
                        return {
                            "description": desc,
                            "salary": "",
                            "requirements": "",
                            "date": _extract_date(html),
                        }, False
            return {}, False
        return {}, True

    async def _fetch_details_http(self, client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
        """Fetch detalles usando HTTP con cookies reales."""
        try:
            response = await client.get(url)
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return {}

            html = response.text
            details = {"description": "", "salary": "", "requirements": "", "date": _extract_date(html)}

            desc_patterns = [
                r'<div class="[^"]*jobs-description-content__text[^"]*".*?>(.*?)</div>',
                r'<div class="[^"]*description__text[^"]*".*?>(.*?)</div>',
                r'<div class="[^"]*show-more-less-html__markup[^"]*".*?>(.*?)</div>',
                r'<section class="[^"]*description[^"]*".*?>(.*?)</section>',
                r'<div id="job-details".*?>(.*?)</div>',
            ]

            for pattern in desc_patterns:
                match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                if match:
                    details["description"] = self._html_to_text(match.group(1))
                    break

            if not details["description"]:
                text_content = re.sub(r'<[^>]+>', ' ', html)
                desc_match = re.search(
                    r'(?i)(About the job|Descripci[oó]n del puesto)(.*?)(?=Similar jobs|Recommended|Apply now|$)',
                    text_content,
                    re.DOTALL,
                )
                if desc_match:
                    details["description"] = self._html_to_text(desc_match.group(2))

            if details["description"]:
                salary_match = re.search(
                    r'(?i)(salario|salary|remuneraci[oó]n|pago):\s*([^\n\.]+)', details["description"]
                )
                if salary_match:
                    details["salary"] = salary_match.group(2).strip()

                req_match = re.search(
                    r'(?i)(requirements|requisitos|calificaciones)(.*?)(?=\n\n|$)',
                    details["description"],
                    re.DOTALL,
                )
                if req_match:
                    details["requirements"] = req_match.group(2).strip()

            return details
        except Exception as e:
            logger.warning(f"HTTP detail fetch failed for {url}: {e}")
            return {}

    @staticmethod
    def _html_to_text(markup: str) -> str:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(markup, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return " ".join(text.split())

    async def fetch(
        self,
        site: dict[str, Any],
        *,
        pages: int = 2,
        search_text: str | None = None,
        skip_source_job_ids: set[str] | None = None,
        port: int = 9222,
    ) -> LinkedInOffers:
        if isinstance(pages, bool) or not isinstance(pages, int):
            raise ValueError("pages debe ser un entero.")
        if pages < 1 or pages > _MAX_PAGES:
            raise ValueError(f"pages debe estar entre 1 y {_MAX_PAGES}.")

        search_term = search_text or site.get("site_config", {}).get("search_text") or "Soporte Técnico"
        location = site.get("country") or "Costa Rica"
        skipped_ids = skip_source_job_ids or set()
        site_id = str(site.get("site_id") or "linkedin")

        cookies: Dict[str, str] = {}
        async with httpx.AsyncClient(
            headers=self.headers, timeout=20.0, follow_redirects=True
        ) as client:
            # 1) Listado por HTTP (el que hoy funciona: `div.base-card` +
            #    JSON-LD `ItemList`).
            tarjetas = await self._listar_http(client, search_term, location, pages)

            # 2) El navegador con la sesion de Brave suma lo que traiga
            #    encima (y es el unico que puede pasar un authwall). Si no
            #    hay navegador, no pasa nada: el listado HTTP ya esta.
            extra, cookies, muro_login = await self._listar_navegador(
                port, search_term, location, pages
            )
            if cookies:
                client.cookies.update(cookies)
            tarjetas = self._fusiona(tarjetas, extra)

            if not tarjetas:
                if muro_login:
                    raise RequiereLoginError(
                        mensaje_requiere_login(site_id)
                    )
                logger.warning("LinkedIn: el listado no devolvio avisos.")
                return LinkedInOffers([], jobs_skipped=0)

            basic_jobs = self._a_ofertas(tarjetas, skipped_ids)

            # Enriquecer con HTTP (guest + cookies)
            enriched_jobs = []
            for indice, job in enumerate(basic_jobs):
                if job.get("source_url"):
                    jid = _numeric_id(job.get("source_job_id"), job.get("source_url"))
                    details: Dict[str, Any] = {}
                    limitado = False
                    if jid:
                        details, limitado = await self._fetch_details_guest(client, jid)
                    if not details.get("description") and not limitado:
                        details = await self._fetch_details_http(client, job.get("source_url")) or details

                    job["job"]["description_raw"] = details.get("description") or job["job"]["description_raw"]
                    job["job"]["requirements_raw"] = details.get("requirements") or job["job"]["requirements_raw"]
                    job["job"]["salary_raw"] = details.get("salary") or job["job"]["salary_raw"]
                    if not job["job"]["date_published"] and details.get("date"):
                        job["job"]["date_published"] = _parse_date_relative(details["date"])

                # Separar descripción/requisitos si vienen juntos
                if job["job"]["description_raw"] and not job["job"]["requirements_raw"]:
                    job["job"]["description_raw"], job["job"]["requirements_raw"] = _split_requirements(
                        job["job"]["description_raw"]
                    )
                enriched_jobs.append(job)

                # El endpoint de detalle aguanta ~10 peticiones seguidas:
                # hay que espaciar las peticiones (medido 2026-11-05).
                if self.request_delay and indice < len(basic_jobs) - 1:
                    await asyncio.sleep(self.request_delay)

        logger.info("LinkedIn: %d ofertas enriquecidas", len(enriched_jobs))
        return LinkedInOffers(enriched_jobs, jobs_skipped=0)

    # ------------------------------------------------------------- listado
    @staticmethod
    def _url_listado(search_term: str, location: str, pagina: int) -> str:
        """URL del listado publico de la pagina ``pagina`` (1 = primera)."""
        url = (
            f"{LISTADO_URL}?keywords={quote_plus(search_term)}"
            f"&location={quote_plus(location)}"
        )
        if pagina > 1:
            url += f"&start={(pagina - 1) * RESULTADOS_POR_PAGINA}"
        return url

    async def _listar_http(
        self,
        client: httpx.AsyncClient,
        search_term: str,
        location: str,
        pages: int,
    ) -> List[Dict[str, Any]]:
        """Listado por HTTP simple (sin sesion)."""
        tarjetas: List[Dict[str, Any]] = []
        vistos: set[str] = set()
        for numero in range(1, pages + 1):
            url = self._url_listado(search_term, location, numero)
            try:
                response = await client.get(url)
            except Exception as exc:  # noqa: BLE001 - la red puede fallar
                logger.warning("LinkedIn: fallo HTTP en %s: %s", url, exc)
                break
            if response.status_code != 200:
                logger.warning(
                    "LinkedIn: HTTP %s en el listado (pagina %d).",
                    response.status_code, numero,
                )
                break
            nuevas = _listado_desde_html(response.text)
            filtradas = []
            for item in nuevas:
                clave = item.get("job_id") or item.get("link") or ""
                if not clave or clave in vistos:
                    continue
                vistos.add(clave)
                filtradas.append(item)
            if not filtradas:
                break
            tarjetas.extend(filtradas)
        return tarjetas

    async def _listar_navegador(
        self,
        port: int,
        search_term: str,
        location: str,
        pages: int,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str], bool]:
        """Listado con el navegador de Brave (sesion del usuario).

        Devuelve ``(tarjetas, cookies, hubo_muro_de_login)``. Si el
        navegador no esta disponible, NO es un error: el listado HTTP ya
        trajo los avisos.
        """
        tarjetas: List[Dict[str, Any]] = []
        cookies: Dict[str, str] = {}
        muro_login = False
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
                ctx = browser.contexts[0]
                page = await ctx.new_page()
                try:
                    await page.set_extra_http_headers(
                        {"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
                    )
                    for numero in range(1, pages + 1):
                        url = self._url_listado(search_term, location, numero)
                        await page.goto(url, wait_until="domcontentloaded")
                        await page.wait_for_timeout(2500)
                        if self._muro_login(page):
                            logger.warning(
                                "LinkedIn: authwall en el navegador (falta sesion)."
                            )
                            muro_login = True
                            break
                        nuevas = _listado_desde_html(await page.content())
                        if not nuevas:
                            break
                        tarjetas.extend(nuevas)
                finally:
                    await page.close()
                todas = await ctx.cookies()
                cookies = {
                    c["name"]: c["value"]
                    for c in todas
                    if "linkedin.com" in (c.get("domain") or "")
                }
        except Exception as exc:  # noqa: BLE001 - sin navegador, sin problema
            logger.warning(
                "LinkedIn: no se pudo usar el navegador (CDP %s): %s", port, exc
            )
        return tarjetas, cookies, muro_login

    @staticmethod
    def _fusiona(
        primera: List[Dict[str, Any]], segunda: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fusiona dos listados sin repetir aviso (mismo id o mismo enlace)."""
        resultado = list(primera)
        vistos = {
            item.get("job_id") or item.get("link")
            for item in primera
            if item.get("job_id") or item.get("link")
        }
        for item in segunda:
            clave = item.get("job_id") or item.get("link")
            if not clave or clave in vistos:
                continue
            vistos.add(clave)
            resultado.append(item)
        return resultado

    @staticmethod
    def _a_ofertas(
        tarjetas: List[Dict[str, Any]], skipped_ids: set[str]
    ) -> List[Dict[str, Any]]:
        """Tarjetas -> ofertas (respetando lo que el usuario descarto)."""
        ofertas: List[Dict[str, Any]] = []
        vistos: set[str] = set()
        for item in tarjetas:
            job_id = str(item.get("job_id") or item.get("link") or "")
            if not job_id or job_id in vistos:
                continue
            if job_id in skipped_ids:
                continue
            vistos.add(job_id)

            fecha = str(item.get("fecha_publicacion") or "")
            date_pub = fecha if re.match(r"^\d{4}-\d{2}-\d{2}", fecha) else _parse_date_relative(fecha)
            ubicacion = item.get("ubicacion_oferta") or ""
            ofertas.append({
                "source_job_id": job_id,
                "source_url": item.get("link"),
                "source_updated_at": date_pub,
                "job": {
                    "job_id": f"linkedin-{job_id}",
                    "title": item.get("titulo") or "",
                    "company": item.get("empresa") or "",
                    "location_raw": ubicacion,
                    "country": "CR",
                    **normalize_cr_location(ubicacion),
                    "work_mode": LinkedInFetcher._detect_work_mode(ubicacion),
                    "employment_type": None,
                    "date_published": date_pub,
                    "expires_at": None,
                    "posting_language": "undetermined",
                    "posting_language_origin": "unknown",
                    "description_raw": "",
                    "requirements_raw": "",
                    "salary_raw": "",
                },
                "raw_payload": item,
            })
        return ofertas


    @staticmethod
    def _detect_work_mode(location: str | None) -> str:
        if not location:
            return "unknown"
        loc = location.lower()
        if any(w in loc for w in ("remoto", "remote", "teletrabajo", "100% remoto")):
            return "remote"
        if any(w in loc for w in ("híbrido", "hibrido", "hybrid", "mixto", "semipresencial")):
            return "hybrid"
        if any(w in loc for w in ("presencial", "onsite", "oficina", "en sitio")):
            return "onsite"
        return "unknown"