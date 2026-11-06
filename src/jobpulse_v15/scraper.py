# -*- coding: utf-8 -*-
"""Barrido de scraping reutilizable (SIN Tk): lo usan la UI v2 y los scripts.

Es la pieza de dominio que permite **lanzar un barrido desde la interfaz**:

- resuelve el fetcher de cada plataforma (import perezoso: importar los 14
  adaptadores al arrancar la UI es lento y no hace falta);
- respeta ``source_sites.enabled`` (lo mismo que pausó la pestaña
  Configuración: una fuente pausada no entra en la corrida);
- respeta ``site_config["pages"]`` y las ofertas descartadas a mano
  (``user_job_state.skip_automatic``);
- abre Brave **solo si hace falta** y lo cierra **solo si esta corrida lo
  abrió** (O7.2): el Brave del usuario nunca se toca;
- registra cada corrida en ``source_runs`` vía ``IngestionService``.

REGLA: el llamador debe estar FUERA de un event loop (``fetch_and_import``
usa ``asyncio.run``). Desde la UI se ejecuta en un hilo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

# platform_id -> "módulo:Clase" (import perezoso).
FETCHERS: dict[str, str] = {
    "ane": "jobpulse_v15.ane:AneFetcher",
    "ashby": "jobpulse_v15.ashby:AshbyFetcher",
    "cinde": "jobpulse_v15.cinde:CindeFetcher",
    "elempleo": "jobpulse_v15.elempleo:ElempleoFetcher",
    "greenhouse": "jobpulse_v15.greenhouse:GreenhouseFetcher",
    "harvie": "jobpulse_v15.harvie:HarvieFetcher",
    "indeed": "jobpulse_v15.indeed:IndeedFetcher",
    "lever": "jobpulse_v15.lever:LeverFetcher",
    "linkedin": "jobpulse_v15.linkedin:LinkedInFetcher",
    "procomer": "jobpulse_v15.procomer:ProcomerFetcher",
    "recruitee": "jobpulse_v15.recruitee:RecruiteeFetcher",
    "successfactors": "jobpulse_v15.successfactors:SuccessFactorsFetcher",
    "workable": "jobpulse_v15.workable:WorkableFetcher",
    "workday": "jobpulse_v15.workday:WorkdayFetcher",
}

# Estados posibles de un sitio dentro del barrido.
ESTADO_OK = "ok"
ESTADO_ERROR = "error"
ESTADO_PAUSADO = "pausado"
ESTADO_SIN_FETCHER = "sin_fetcher"
ESTADO_NO_EXISTE = "no_existe"
ESTADO_CANCELADO = "cancelado"
# O13 · Ola 3.3: el sitio pide iniciar sesion (NO esta roto).
ESTADO_REQUIERE_LOGIN = "requiere_login"


@dataclass(frozen=True)
class Progreso:
    """Evento de progreso del barrido (lo consume la UI en un hilo)."""

    indice: int
    total: int
    site_id: str
    plataforma: str
    etapa: str      # inicio | fin | error | aviso
    detalle: str = ""


@dataclass(frozen=True)
class ResultadoSitio:
    """Resultado de un sitio dentro del barrido."""

    site_id: str
    plataforma: str
    estado: str
    jobs_found: int = 0
    jobs_new: int = 0
    jobs_duplicate: int = 0
    jobs_skipped: int = 0
    mensaje: str = ""


@dataclass
class ResumenBarrido:
    """Resumen de la corrida completa."""

    resultados: list[ResultadoSitio] = field(default_factory=list)
    cancelado: bool = False

    @property
    def jobs_found(self) -> int:
        return sum(r.jobs_found for r in self.resultados)

    @property
    def jobs_new(self) -> int:
        return sum(r.jobs_new for r in self.resultados)

    @property
    def jobs_duplicate(self) -> int:
        return sum(r.jobs_duplicate for r in self.resultados)

    @property
    def jobs_skipped(self) -> int:
        return sum(r.jobs_skipped for r in self.resultados)

    @property
    def errores(self) -> int:
        return sum(1 for r in self.resultados if r.estado == ESTADO_ERROR)

    @property
    def sitios_ok(self) -> int:
        return sum(1 for r in self.resultados if r.estado == ESTADO_OK)


def instanciar_fetcher(platform_id: str) -> Any | None:
    """Instancia el fetcher de la plataforma; None si no hay adaptador."""
    referencia = FETCHERS.get(platform_id)
    if not referencia:
        return None
    modulo, _, clase = referencia.partition(":")
    try:
        import importlib

        return getattr(importlib.import_module(modulo), clase)()
    except Exception:  # noqa: BLE001 - un adaptador roto no debe tumbar el barrido
        return None


def plataforma_de_sitio(site: dict[str, Any]) -> str:
    """Plataforma efectiva del sitio (``platform_id`` o ``site_config.adapter``)."""
    config = site.get("site_config") or {}
    return str(site.get("platform_id") or config.get("adapter") or "")


def ejecutar_barrido(
    site_ids: Sequence[str],
    *,
    pages: int = 2,
    port: int = 9222,
    dias: int = 30,
    database_path: str | Path | None = None,
    on_progress: Callable[[Progreso], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> ResumenBarrido:
    """Barre los sitios indicados y devuelve el resumen de la corrida.

    - ``pages``: páginas por defecto; cada sitio usa la suya de
      ``site_config["pages"]`` si la tiene.
    - ``port``: puerto CDP para las plataformas de navegador.
    - ``on_progress``: recibe :class:`Progreso` (en el hilo del worker: la UI
      debe encolarlo, nunca tocar Tk aquí).
    - ``should_stop``: si devuelve True, el barrido termina **después** del
      sitio en curso (no se corta un fetch a medias).
    """
    from jobpulse_v15.db import Database
    from jobpulse_v15.ingestion import IngestionService
    from jobpulse_v15.repository import Repository
    from jobpulse_v15.scrape_dispatch import construir_llamada

    base = Database(database_path) if database_path else Database()
    base.initialize()
    repo = Repository(base)
    service = IngestionService(repo)

    # 1) Resolver sitios ANTES de abrir el navegador (si un sitio no existe
    #    o está pausado, no se toca nada más).
    planes: list[tuple[str, str, str]] = []
    for site_id in site_ids:
        sitio = repo.get_site(site_id)
        if sitio is None:
            planes.append((site_id, "", ESTADO_NO_EXISTE))
            continue
        plataforma = plataforma_de_sitio(sitio)
        if not sitio.get("enabled"):
            planes.append((site_id, plataforma, ESTADO_PAUSADO))
            continue
        planes.append((site_id, plataforma, ""))

    resumen = ResumenBarrido()
    total = len(planes)

    # 2) Brave: solo si algún sitio elegido lo necesita (O7.2).
    manager = None
    necesita = any(
        plataforma in {"ane", "indeed", "linkedin", "elempleo"}
        for _sid, plataforma, estado in planes if not estado
    )
    if necesita:
        from jobpulse_v15.browser_manager import asegurar_brave, cdp_vivo
        if cdp_vivo(port):
            _avanzar(on_progress, Progreso(0, total, "", "", "aviso",
                                           f"Brave CDP ya vivo en {port}"))
        else:
            manager = asegurar_brave(port)
            _avanzar(on_progress, Progreso(0, total, "", "", "aviso",
                                           f"Brave abierto por la UI (CDP {port})"))

    try:
        for indice, (site_id, plataforma, estado) in enumerate(planes, start=1):
            if should_stop is not None and should_stop():
                resumen.cancelado = True
                break
            if estado:
                resumen.resultados.append(
                    ResultadoSitio(site_id, plataforma, estado,
                                   mensaje=_mensaje_estado(estado)))
                _avanzar(on_progress, Progreso(indice, total, site_id,
                                               plataforma, "fin",
                                               _mensaje_estado(estado)))
                continue

            sitio = repo.get_site(site_id) or {}
            fetcher = instanciar_fetcher(plataforma)
            if fetcher is None:
                resumen.resultados.append(ResultadoSitio(
                    site_id, plataforma, ESTADO_SIN_FETCHER,
                    mensaje="No hay adaptador para esta plataforma."))
                _avanzar(on_progress, Progreso(indice, total, site_id,
                                               plataforma, "error",
                                               "Sin adaptador para la plataforma"))
                continue

            config = sitio.get("site_config") or {}
            paginas = int(config.get("pages", pages) or pages)
            omitidos = repo.list_skipped_source_job_ids(site_id)
            llamada = construir_llamada(
                plataforma, fetcher, sitio, pages=paginas, port=port,
                dias=dias, skip_source_job_ids=omitidos,
            )
            _avanzar(on_progress, Progreso(indice, total, site_id, plataforma,
                                           "inicio", f"{paginas} pág."))
            try:
                crudo = service.fetch_and_import(
                    site_id, llamada, run_kind=plataforma)
            except Exception as exc:  # noqa: BLE001 - un sitio no tumba la corrida
                mensaje = f"{type(exc).__name__}: {exc}"
                resumen.resultados.append(ResultadoSitio(
                    site_id, plataforma, ESTADO_ERROR, mensaje=mensaje))
                _avanzar(on_progress, Progreso(indice, total, site_id,
                                               plataforma, "error", mensaje))
                continue
            resultado = ResultadoSitio(
                site_id,
                plataforma,
                ESTADO_OK,
                jobs_found=int(crudo.get("jobs_found", 0) or 0),
                jobs_new=int(crudo.get("jobs_new", 0) or 0),
                jobs_duplicate=int(crudo.get("jobs_duplicate", 0) or 0),
                jobs_skipped=int(crudo.get("jobs_skipped", 0) or 0),
            )
            if crudo.get("requires_login"):
                # El sitio pide sesion: no es un error ni un sitio roto.
                resultado = ResultadoSitio(
                    site_id,
                    plataforma,
                    ESTADO_REQUIERE_LOGIN,
                    mensaje=str(crudo.get("mensaje") or "El sitio exige iniciar sesion."),
                )
            resumen.resultados.append(resultado)
            _avanzar(on_progress, Progreso(
                indice, total, site_id, plataforma, "fin",
                f"{resultado.jobs_found} encontradas · {resultado.jobs_new} nuevas"
                if resultado.estado == ESTADO_OK
                else resultado.mensaje,
            ))
    finally:
        # O7.2: solo se cierra el Brave que ESTA corrida abrió.
        if manager is not None:
            try:
                manager.stop_brave_sync()
            except Exception:  # noqa: BLE001
                pass
    return resumen


def _avanzar(on_progress: Callable[[Progreso], None] | None,
             progreso: Progreso) -> None:
    if on_progress is None:
        return
    try:
        on_progress(progreso)
    except Exception:  # noqa: BLE001 - un listener roto no corta el barrido
        pass


def _mensaje_estado(estado: str) -> str:
    return {
        ESTADO_PAUSADO: "Sitio pausado (no entra en la corrida).",
        ESTADO_NO_EXISTE: "El sitio no existe en la BD.",
        ESTADO_SIN_FETCHER: "No hay adaptador para esta plataforma.",
        ESTADO_CANCELADO: "Cancelado.",
        ESTADO_REQUIERE_LOGIN: "El sitio exige iniciar sesion.",
    }.get(estado, estado)
