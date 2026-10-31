"""Adaptador Workday CXS para una sola fuente habilitada de v1.5."""

from html.parser import HTMLParser
from http.client import HTTPException
import json
import logging
import re
import time
import unicodedata
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen


logger = logging.getLogger("jobpulse.workday")


PAGE_SIZE = 20
MAX_PAGES = 10
_WORKDAY_HOST = re.compile(
    r"^(?P<tenant>[a-z0-9-]+)\.(?P<cluster>wd\d+)\.myworkdayjobs\.com$",
    re.IGNORECASE,
)
_REQUISITION_ID = re.compile(r"([A-Za-z]{2}\d{6,})[_\-]?\w*$")
_COSTA_RICA_PROVINCES = {
    "alajuela": "Alajuela",
    "cartago": "Cartago",
    "guanacaste": "Guanacaste",
    "heredia": "Heredia",
    "limon": "Limón",
    "puntarenas": "Puntarenas",
    "san jose": "San José",
}
# Provincias cuyo nombre tambien es el de una ciudad/distrito: con ese unico
# dato no se puede saber a cual se refiere, asi que no se guarda nada.
# Guanacaste queda fuera (no hay ciudad llamada Guanacaste) y por eso su
# provincia si se puede dar por buena.
_PROVINCIAS_AMBIGUAS_CON_CIUDAD = {
    "alajuela",
    "cartago",
    "heredia",
    "limon",
    "puntarenas",
    "san jose",
}

# Canton -> provincia, SOLO para cantones cuyo nombre no se repite en otra
# provincia. Lista explicita y no exhaustiva: se usa para completar la
# provincia cuando el texto ya trae el canton y no menciona la provincia.
# Un nombre que no este aqui deja la provincia como esta (nunca se adivina).
#
# Deliberadamente FUERA: "Lagunilla" (hay Lagunilla en Alajuela y en Heredia;
# los avisos de Thermo Fisher dicen "Ultra Park II, Lagunilla (Heredia)"),
# "San José"/"Alajuela"/... (provincia y ciudad comparten nombre) y los
# distritos que se repiten entre provincias.
_COSTA_RICA_CANTONES = {
    "grecia": "Alajuela",
    "santa ana": "San José",
    "san antonio de belen": "Heredia",
    "belen": "Heredia",
    "liberia": "Guanacaste",
    "escazu": "San José",
}

# Workday separa la ubicacion con coma, guion o barra segun el tablero.
_SEPARADORES_UBICACION = re.compile(r"[,\-/–]")

# Fragmentos que NO son un lugar y que antes se colaban como ciudad.
_RUIDO_UBICACION = re.compile(
    r"\b(?:costa\s*rica|remote|remoto|virtual|home\s*office|hybrid|h[ií]brido"
    r"|latin\s*america|latam|global\s*service\s*center|multi-?loc)\b",
    re.IGNORECASE,
)


class WorkdayFetchError(RuntimeError):
    """Workday devolvio una respuesta no valida o un error HTTP/transporte."""


class WorkdayOffers(list[dict[str, Any]]):
    """Ofertas del tablero, junto con el total de anuncios omitidos por estado."""

    def __init__(
        self, offers: list[dict[str, Any]], *, jobs_skipped: int = 0
    ) -> None:
        super().__init__(offers)
        self.jobs_skipped = jobs_skipped


class _HtmlTextParser(HTMLParser):
    _BLOCK_TAGS = {
        "br", "div", "li", "p", "section", "tr", "ul", "ol", "h1", "h2", "h3"
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        _ = attrs
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


class WorkdayFetcher:
    """Consulta solo el tablero Workday configurado en el registro del sitio."""

    def __init__(self, *, timeout: float = 20.0, request_delay: float = 0.15) -> None:
        if timeout <= 0:
            raise ValueError("timeout debe ser mayor que cero.")
        if request_delay < 0 or request_delay > 5:
            raise ValueError("request_delay debe estar entre 0 y 5 segundos.")
        self.timeout = timeout
        self.request_delay = request_delay

    def fetch(
        self,
        site: dict[str, Any],
        *,
        pages: int = 1,
        search_text: str | None = None,
        skip_source_job_ids: set[str] | None = None,
    ) -> WorkdayOffers:
        if isinstance(pages, bool) or not isinstance(pages, int):
            raise ValueError("pages debe ser un entero.")
        if pages < 1 or pages > MAX_PAGES:
            raise ValueError(f"pages debe estar entre 1 y {MAX_PAGES}.")

        tenant, cluster, board = self._parse_board_url(site.get("base_url"))
        config = site.get("site_config") or {}
        if not isinstance(config, dict):
            raise ValueError("La configuracion Workday debe ser un objeto.")
        query = search_text or config.get("search_text") or "Costa Rica"
        if not isinstance(query, str) or not query.strip():
            raise ValueError("search_text debe contener texto.")
        country = site.get("country") or config.get("country") or "CR"
        country_query = config.get("country_query") or "Costa Rica"
        if not isinstance(country_query, str) or not country_query.strip():
            raise ValueError("country_query debe contener texto.")

        api_url = (
            f"https://{tenant}.{cluster}.myworkdayjobs.com"
            f"/wday/cxs/{quote(tenant, safe='')}/{quote(board, safe='')}"
        )
        postings = self._list_postings(api_url, query.strip(), pages)
        offers = []
        skipped = 0
        seen_ids = set()
        skipped_ids = skip_source_job_ids or set()
        for posting in postings:
            location_text = self._optional_text(posting.get("locationsText"))
            external_path = self._required_text(
                posting.get("externalPath"), "externalPath"
            )
            if (
                location_text
                and country_query.casefold() not in location_text.casefold()
            ):
                continue
            listing_source_id = self._listing_source_job_id(posting, external_path)
            if listing_source_id in skipped_ids:
                skipped += 1
                continue
            detail = self._fetch_detail(api_url, external_path)
            if self.request_delay:
                time.sleep(self.request_delay)
            info = detail.get("jobPostingInfo")
            if not isinstance(info, dict):
                raise WorkdayFetchError(
                    f"El detalle de Workday para {external_path!r} "
                    "no incluye jobPostingInfo."
                )
            detail_location = self._optional_text(info.get("location"))
            full_location = detail_location or location_text
            if not full_location:
                raise WorkdayFetchError(
                    f"El anuncio {external_path!r} no informa ubicacion."
                )
            if country_query.casefold() not in full_location.casefold():
                continue

            title = self._optional_text(info.get("title")) or self._optional_text(
                posting.get("title")
            )
            if not title:
                raise WorkdayFetchError(
                    f"El anuncio Workday {external_path!r} no informa titulo."
                )
            source_id = self._source_job_id(info, external_path)
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)
            description = self._html_to_text(
                self._optional_text(info.get("jobDescription")) or ""
            )
            origin = f"https://{tenant}.{cluster}.myworkdayjobs.com"
            source_url = self._optional_text(info.get("externalUrl"))
            if not source_url:
                source_url = f"{origin}/{quote(board, safe='')}{external_path}"
            date_published = self._optional_text(info.get("startDate"))

            job: dict[str, Any] = {
                "job_id": f"workday-{source_id}",
                "title": title,
                "company": site.get("company_name") or site.get("site_name"),
                "location_raw": full_location or None,
                "country": country,
                **self.normalize_location(full_location, country, country_query),
                "work_mode": "unknown",
                "employment_type": self._optional_text(info.get("timeType")),
                "date_published": date_published,
                "posting_language": "undetermined",
                "posting_language_origin": "unknown",
                "description_raw": description or None,
            }
            raw_payload = {"listing": posting, "detail": detail}
            offers.append(
                {
                    "source_job_id": source_id,
                    "source_url": source_url,
                    "source_updated_at": date_published,
                    "job": job,
                    "raw_payload": raw_payload,
                }
            )
        return WorkdayOffers(offers, jobs_skipped=skipped)

    @staticmethod
    def _listing_source_job_id(
        posting: dict[str, Any], external_path: str
    ) -> str | None:
        for key in ("jobPostingId", "jobRequisitionId"):
            value = posting.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        basename = unquote(external_path.rstrip("/").split("/")[-1])
        match = _REQUISITION_ID.search(basename)
        if match:
            return match.group(1)
        return basename or None

    @staticmethod
    def normalize_location(
        location: str, country: str, country_query: str
    ) -> dict[str, str | None]:
        """Extrae ciudad/provincia de los formatos que usa Workday en Costa Rica.

        Acepta cualquier separador (``,`` ``-`` ``/``), no solo la coma, y
        busca la provincia en cualquier posicion: los tableros escriben
        ``"Alajuela, Costa Rica"``, ``"Costa Rica - Alajuela"``,
        ``"Heredia Costa Rica"`` y ``"Guanacaste / Liberia / Liberia"``.

        Regla de oro: no se adivina. Si el texto solo dice el nombre de una
        provincia que tambien es nombre de ciudad (``"San Jose, Costa Rica"``)
        no se guarda NADA, porque no se sabe a cual se refiere. La provincia
        solo se da por cierta cuando la posicion la desambigua (``"Costa Rica
        - Alajuela"``, pais delante) o cuando la acompania un canton conocido.
        """
        country_code = country.strip().casefold()
        query = country_query.strip().casefold()
        if country_code not in {"cr", "cri"} or query != "costa rica":
            return {"city": None, "region": None}

        def province_key(value: str) -> str:
            normalized = unicodedata.normalize("NFKD", value)
            return "".join(
                character
                for character in normalized
                if not unicodedata.combining(character)
            ).casefold().strip()

        # El pais y los terminos de modalidad no son lugares: se descartan
        # antes de partir para no guardar ciudad="Remote".
        limpio = _RUIDO_UBICACION.sub(" ", location)
        partes = [
            parte.strip(" .;:()")
            for parte in _SEPARADORES_UBICACION.split(limpio)
        ]
        partes = [parte for parte in partes if len(parte) > 1]
        if not partes:
            return {"city": None, "region": None}

        indice_provincia: int | None = None
        for indice, parte in enumerate(partes):
            if province_key(parte) in _COSTA_RICA_PROVINCES:
                indice_provincia = indice
                break

        # Los tableros que escriben el pais delante ("Costa Rica - Alajuela")
        # solo ponen la provincia despues: ahi la posicion la desambigua.
        pais_delante = province_key(location).startswith(query)

        city: str | None = None
        region: str | None = None

        if indice_provincia is None:
            # "Canton, Costa Rica": el texto no nombra ninguna provincia.
            city = partes[0]
        elif indice_provincia == 0:
            # "Provincia / Canton / Distrito" o "Provincia, Central, Pais".
            # La ciudad solo se toma si es un canton CONOCIDO: lo que sigue a
            # la provincia puede ser una planta ("Wet Plant") o una agrupacion
            # ("Central"), y eso no es una ciudad.
            for parte in partes[1:]:
                if province_key(parte) in _COSTA_RICA_CANTONES:
                    city = parte
                    break
            if city is not None or pais_delante:
                region = _COSTA_RICA_PROVINCES[province_key(partes[0])]
            elif province_key(partes[0]) not in _PROVINCIAS_AMBIGUAS_CON_CIUDAD:
                region = _COSTA_RICA_PROVINCES[province_key(partes[0])]
        else:
            # "Canton, Provincia, Costa Rica" (formato clasico).
            city = partes[0]
            region = _COSTA_RICA_PROVINCES[province_key(partes[indice_provincia])]

        if region is None and city is not None:
            # El canton es conocido y su provincia es un dato fijo.
            region = _COSTA_RICA_CANTONES.get(province_key(city))
        return {"city": city, "region": region}

    def _list_postings(
        self, api_url: str, search_text: str, pages: int
    ) -> list[dict[str, Any]]:
        postings_by_path: dict[str, dict[str, Any]] = {}
        for page in range(pages):
            response = self._request_json(
                f"{api_url}/jobs",
                method="POST",
                payload={
                    "appliedFacets": {},
                    "limit": PAGE_SIZE,
                    "offset": page * PAGE_SIZE,
                    "searchText": search_text,
                },
            )
            postings = response.get("jobPostings")
            if not isinstance(postings, list):
                raise WorkdayFetchError(
                    "La respuesta de Workday no contiene una lista jobPostings."
                )
            if not postings:
                break
            for index, posting in enumerate(postings):
                if not isinstance(posting, dict):
                    # Anuncio promocional u entrada malformada: se omite y no
                    # mata el barrido del tablero completo.
                    logger.warning(
                        "Workday: jobPostings[%d] no es objeto; omitido.", index
                    )
                    continue
                external_path = self._optional_text(posting.get("externalPath"))
                if not external_path:
                    logger.warning(
                        "Workday: jobPostings[%d] sin externalPath (%r); omitido.",
                        index,
                        posting.get("title"),
                    )
                    continue
                postings_by_path[external_path] = posting
            if len(postings) < PAGE_SIZE:
                break
        return list(postings_by_path.values())

    def _fetch_detail(self, api_url: str, external_path: str) -> dict[str, Any]:
        if "/job/" not in external_path:
            raise WorkdayFetchError(
                f"externalPath de Workday no contiene /job/: {external_path!r}."
            )
        token = unquote(external_path.split("/job/", 1)[1]).strip("/")
        if not token:
            raise WorkdayFetchError("externalPath de Workday no contiene un ID.")
        encoded_token = "/".join(quote(part, safe="") for part in token.split("/"))
        response = self._request_json(
            f"{api_url}/job/{encoded_token}",
            method="GET",
        )
        return response

    def _request_json(
        self,
        url: str,
        *,
        method: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = (
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
            if payload is not None
            else None
        )
        request = Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "JobPulse-CR-v1.5",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except HTTPError as exc:
            raise WorkdayFetchError(
                f"Workday devolvio HTTP {exc.code} para {url}."
            ) from exc
        except (URLError, TimeoutError, OSError, HTTPException) as exc:
            raise WorkdayFetchError(
                f"No se pudo conectar con Workday para {url}: {exc}"
            ) from exc

        try:
            decoded = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WorkdayFetchError(
                f"Workday devolvio JSON invalido para {url}."
            ) from exc
        if not isinstance(decoded, dict):
            raise WorkdayFetchError(
                f"Workday devolvio una respuesta no-objeto para {url}."
            )
        return decoded

    @staticmethod
    def _parse_board_url(base_url: Any) -> tuple[str, str, str]:
        if not isinstance(base_url, str):
            raise ValueError("El sitio debe tener una URL Workday.")
        parsed = urlsplit(base_url)
        try:
            host = parsed.hostname or ""
            has_invalid_port = parsed.port is not None
        except ValueError:
            host = ""
            has_invalid_port = True
        host_match = _WORKDAY_HOST.fullmatch(host.lower())
        segments = [unquote(part) for part in parsed.path.split("/") if part]
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or has_invalid_port
            or host_match is None
            or not segments
            or any(part in {".", ".."} for part in segments)
        ):
            raise ValueError(
                "URL Workday invalida; se espera "
                "https://<tenant>.wd<n>.myworkdayjobs.com/<board>."
            )
        return (
            host_match.group("tenant"),
            host_match.group("cluster"),
            segments[0],
        )

    @staticmethod
    def _source_job_id(info: dict[str, Any], external_path: str) -> str:
        for key in ("jobPostingId", "jobRequisitionId"):
            value = info.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        basename = unquote(external_path.rstrip("/").split("/")[-1])
        match = _REQUISITION_ID.search(basename)
        if match:
            return match.group(1)
        if basename:
            return basename
        raise WorkdayFetchError(
            f"No se pudo obtener una identidad estable desde {external_path!r}."
        )

    @staticmethod
    def _html_to_text(markup: str) -> str:
        parser = _HtmlTextParser()
        parser.feed(markup)
        parser.close()
        return parser.text()

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        text = WorkdayFetcher._optional_text(value)
        if text is None:
            raise WorkdayFetchError(f"El registro Workday no tiene {field}.")
        return text

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return None
        text = " ".join(value.split())
        return text or None
