# -*- coding: utf-8 -*-
"""Orquestador ÚNICO del pipeline (O12 · Ola 2.1).

Una sola implementación de cada etapa, para que CLI, UI clásica (solo los
pasos que ya delega), UI v2 y los scripts de la raíz den **el mismo estado** de
la base. Mismo patrón que ya resolvió la triplicación de `analysis_flow`:

| Etapa | Implementación única | Qué hace |
|---|---|---|
| `scrape` | `scraper.ejecutar_barrido` | barrido de los sitios (Brave bajo demanda) |
| `analisis` | `analysis_flow.extract_job_analysis` | análisis por reglas de los pendientes |
| `ia` | `ia_enrichment.pase_completo` | enriquecimiento IA (servidor bajo demanda) |
| `reanalisis` | `analysis_flow.reananalizar_con_campos_fuente` | integra `skills`/`languages` al análisis |
| `backfill` | `repository.backfill_requirements_canonico` | rellena `codigo_canonico` NULL (idempotente) |
| `paso5` | `matching.ejecutar_paso5` | corrida NUEVA de `job_match` |
| `evidencia` | `jobpulse_v15.evidencia` | genera y verifica el documento |

Reglas del proyecto que este módulo **no** cambia:

* el Paso 5 es siempre una **corrida nueva** (`corrida_id` nuevo; las previas
  `valida=0`), nunca un UPDATE;
* `IA_MAX_VACANTES` y demás límites son opt-in: sin valor no hay tope;
* la etapa `ia` con proveedor externo **no arranca** nada local, y la
  confirmación de privacidad la hace el CALLER (UI) antes de invocar;
* ninguna etapa borra ni funde datos.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

#: Todas las etapas, en el ORDEN en que se ejecutan.
ETAPAS: tuple[str, ...] = (
    "scrape",
    "analisis",
    "ia",
    "reanalisis",
    "backfill",
    "paso5",
    "evidencia",
)

#: Lo que corre un "Procesar" normal: sobre los avisos que ya están en la BD.
#: `scrape` necesita sitios y `backfill` recorre todos los requisitos, así que
#: se piden EXPLÍCITAMENTE.
ETAPAS_POR_DEFECTO: tuple[str, ...] = (
    "analisis",
    "ia",
    "reanalisis",
    "paso5",
    "evidencia",
)

#: Las que se pueden pedir sin argumentos extra.
ETAPAS_QUE_NECESITAN_ARGUMENTOS: dict[str, str] = {
    "scrape": "requiere `sites` (ids de sitio a barrer)",
}


def _noop(_texto: str) -> None:
    return None


def ejecutar(
    repository,
    *,
    etapas: Sequence[str] | None = None,
    progreso: Callable[[str], None] | None = None,
    evaluar_todo: bool = False,
    sites: Sequence[str] | None = None,
    pages: int = 2,
    port: int | None = None,
    max_vacantes: int | None = None,
    limite_analisis: int = 10000,
    db_path: str | Path | None = None,
    docs_dir: str | Path | None = None,
    salida_evidencia: str | Path | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Ejecuta las etapas pedidas y devuelve el resumen de cada una.

    ``etapas=None`` usa :data:`ETAPAS_POR_DEFECTO`. Un nombre desconocido es
    ``ValueError`` (nunca se ignora en silencio).

    Devuelve::

        {"ok": bool, "corrida": str | None, "detenido": bool,
         "etapas": {"analisis": {...}, "ia": {...}, ...},
         "errores": [str, ...]}

    Si una etapa lanza una excepción, se registra, se marca ``ok=False`` y se
    **detienen** las siguientes (no tiene sentido evaluar sobre un análisis que
    reventó). Un resultado de etapa con ``ok=False`` (p. ej. IA "atascada") NO
    aborta: el Paso 5 se corre igual, para que el usuario vea el estado real.
    """
    log = progreso or _noop
    pedidas = tuple(etapas) if etapas is not None else ETAPAS_POR_DEFECTO
    desconocidas = [e for e in pedidas if e not in ETAPAS]
    if desconocidas:
        raise ValueError(
            "Etapa(s) desconocida(s): %s (válidas: %s)"
            % (", ".join(desconocidas), ", ".join(ETAPAS))
        )
    ruta_db = Path(db_path) if db_path else Path(repository.database.path)
    resultados: dict[str, dict[str, Any]] = {}
    errores: list[str] = []
    corrida: str | None = None
    detenido = False

    for nombre in ETAPAS:
        if nombre not in pedidas:
            continue
        if should_stop is not None and should_stop():
            detenido = True
            log("— Pipeline detenido antes de la etapa %s." % nombre)
            break
        log("=== %s ===" % nombre.upper())
        try:
            resultado = _EJECUTORAS[nombre](
                repository,
                log,
                evaluar_todo=evaluar_todo,
                sites=sites,
                pages=pages,
                port=port,
                max_vacantes=max_vacantes,
                limite_analisis=limite_analisis,
                db_path=ruta_db,
                docs_dir=docs_dir,
                salida_evidencia=salida_evidencia,
                should_stop=should_stop,
            )
        except Exception as exc:  # noqa: BLE001 - se reporta, no se traga
            resultado = {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}
            errores.append("%s: %s" % (nombre, resultado["error"]))
        resultado.setdefault("ok", True)
        resultados[nombre] = resultado
        if resultado.get("corrida"):
            corrida = str(resultado["corrida"])
        if "error" in resultado:
            log("✗ %s: %s" % (nombre, resultado["error"]))
            break

    ok = not errores and all(r.get("ok", True) for r in resultados.values())
    return {
        "ok": ok,
        "corrida": corrida,
        "detenido": detenido,
        "etapas": resultados,
        "errores": errores,
    }


# ---------------------------------------------------------------------------
# Etapas
# ---------------------------------------------------------------------------
def _etapa_scrape(
    repository,
    log,
    *,
    sites,
    pages,
    port,
    db_path,
    should_stop,
    **_ignorados,
) -> dict[str, Any]:
    """Barrido de los sitios pedidos (sin sitios no hay nada que hacer)."""
    if not sites:
        return {"ok": False, "motivo": ETAPAS_QUE_NECESITAN_ARGUMENTOS["scrape"]}
    from jobpulse_v15 import scraper
    from jobpulse_v15.browser_manager import puerto_cdp_configurado

    def _evento(evento: scraper.Progreso) -> None:
        icono = {"inicio": "→", "fin": "✓", "error": "✗", "aviso": "·"}.get(
            evento.etapa, "·"
        )
        log(
            "%s [%d/%d] %s · %s %s"
            % (
                icono,
                evento.indice,
                evento.total,
                evento.plataforma,
                evento.site_id,
                evento.detalle,
            ).rstrip()
        )

    resumen = scraper.ejecutar_barrido(
        list(sites),
        pages=pages,
        port=port or puerto_cdp_configurado(),
        database_path=db_path,
        on_progress=_evento,
        should_stop=should_stop,
    )
    return {
        "ok": resumen.errores == 0 and not resumen.cancelado,
        "cancelado": resumen.cancelado,
        "sitios": len(resumen.resultados),
        "sitios_ok": resumen.sitios_ok,
        "jobs_found": resumen.jobs_found,
        "jobs_new": resumen.jobs_new,
        "jobs_duplicate": resumen.jobs_duplicate,
        "jobs_skipped": resumen.jobs_skipped,
        "errores": resumen.errores,
        "por_sitio": [
            {
                "site_id": r.site_id,
                "plataforma": r.plataforma,
                "estado": r.estado,
                "jobs_found": r.jobs_found,
                "jobs_new": r.jobs_new,
                "mensaje": r.mensaje,
            }
            for r in resumen.resultados
        ],
    }


def _etapa_analisis(
    repository,
    log,
    *,
    limite_analisis,
    should_stop=None,
    **_ignorados,
) -> dict[str, Any]:
    """Análisis por reglas de los avisos que aún no tienen análisis."""
    from jobpulse_v15.analysis_flow import extract_job_analysis

    pendientes = repository.search_jobs(
        review_reason="analysis_missing", limit=limite_analisis
    )
    log("%d aviso(s) sin análisis." % len(pendientes))
    ok = fallos = 0
    for job in pendientes:
        if should_stop is not None and should_stop():
            break
        try:
            extract_job_analysis(repository, str(job["job_id"]))
            ok += 1
        except (ValueError, sqlite3.Error) as exc:
            fallos += 1
            log("✗ %s: %s" % (job["job_id"], exc))
    log("Reglas: %d analizados, %d con error." % (ok, fallos))
    return {"ok": fallos == 0, "pendientes": len(pendientes), "analizados": ok,
            "fallos": fallos}


def _etapa_ia(
    repository,
    log,
    *,
    max_vacantes,
    db_path,
    **_ignorados,
) -> dict[str, Any]:
    """Pase IA completo (servidor bajo demanda; externo = no arranca nada).

    La CONFIRMACIÓN de privacidad la hace el caller (UI) antes de llamar: aquí
    solo se registra el aviso en el log. Sin IA configurada se OMITE sin
    romper el pipeline (el análisis por reglas ya se hizo).
    """
    import asyncio

    from jobpulse_v15 import ia_enrichment as iae
    from jobpulse_v15 import ia_estado as ie
    from jobpulse_v15.ia_servidor import asegurar_servidor

    cliente = iae.get_ia_client()
    if not cliente:
        log("IA no configurada (Configuración → IA); etapa omitida.")
        return {
            "ok": False,
            "estado": "omitido",
            "motivo": "IA no configurada (IA_PROVEEDOR/IA_BASE_URL/IA_MODEL)",
        }
    aviso = iae.aviso_privacidad(cliente)
    if aviso:
        log("⚠️ %s" % aviso)
    servidor = asegurar_servidor(on_log=log)
    try:
        antes = ie.snapshot_enriquecimiento(Path(db_path))
        respuesta = asyncio.run(
            iae.pase_completo(
                on_event=log, max_vacantes=max_vacantes, db_path=str(db_path)
            )
        )
    finally:
        if servidor is not None:
            servidor.detener()
    despues = ie.snapshot_enriquecimiento(Path(db_path))
    veredicto = ie.evaluar_ia(antes, despues, respuesta)
    log(ie.resumen_linea(veredicto))
    if not veredicto.get("ok"):
        log("⚠️ El enriquecimiento NO completó su trabajo (ver motivo).")
    return {
        "ok": bool(veredicto.get("ok")),
        "estado": veredicto.get("estado"),
        "motivo": veredicto.get("motivo"),
        "avance": veredicto.get("avance", {}),
        "stats_ia": respuesta,
    }


def _etapa_reanalisis(repository, log, *, should_stop=None, **_ignorados) -> dict[str, Any]:
    """Re-análisis de lo que quedó obsoleto.

    Dos motivos (O13 · Ola 4.1):
    * el aviso tiene `skills`/idiomas que su análisis no integró (Ola 1.1);
    * el TEXTO del aviso cambió (el scraper trajo más texto del que se
      analizó): el `text_hash` del análisis vigente ya no cuadra.
    """
    from jobpulse_v15.analysis_flow import (
        reananalizar_con_campos_fuente,
        reananalizar_texto_cambiado,
    )

    stats = reananalizar_con_campos_fuente(repository, on_progress=log)
    texto = reananalizar_texto_cambiado(repository, on_progress=log)
    log(
        "Re-análisis por texto nuevo: %d de %d aviso(s) re-analizado(s)."
        % (texto.get("reanalizados", 0), texto.get("candidatos", 0))
    )
    return dict(
        stats,
        texto_candidatos=texto.get("candidatos", 0),
        texto_reanalizados=texto.get("reanalizados", 0),
        ok=stats.get("errores", 0) == 0 and texto.get("errores", 0) == 0,
    )


def _etapa_backfill(repository, log, **_ignorados) -> dict[str, Any]:
    """Rellena `codigo_canonico` NULL (idempotente, solo NULL)."""
    with repository.database.connection() as connection:
        pendientes = connection.execute(
            "SELECT COUNT(*) FROM job_requirements WHERE codigo_canonico IS NULL"
        ).fetchone()[0]
    resultado = repository.backfill_requirements_canonico()
    log(
        "Backfill canónico: %d actualizado(s) de %d sin código."
        % (resultado.get("actualizados", 0), pendientes)
    )
    return {
        "ok": True,
        "sin_codigo": pendientes,
        "actualizados": resultado.get("actualizados", 0),
        "revisados": resultado.get("revisados", 0),
        "sin_concepto": resultado.get("sin_concepto", 0),
    }


def _etapa_paso5(
    repository,
    log,
    *,
    evaluar_todo,
    db_path,
    **_ignorados,
) -> dict[str, Any]:
    """Corrida NUEVA del Paso 5 (nunca UPDATE de la anterior)."""
    from jobpulse_v15 import matching

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        corrida, resultados = matching.ejecutar_paso5(
            connection, aplicar_filtro_areas=not evaluar_todo
        )
    finally:
        connection.close()
    por_estado = dict(Counter(r.estado for r in resultados))
    por_motivo = dict(Counter(r.motivo for r in resultados))
    log(
        "Paso 5: corrida %s · %d evaluada(s) · %s"
        % (
            corrida,
            len(resultados),
            ", ".join("%s=%d" % (k, v) for k, v in sorted(por_estado.items())),
        )
    )
    return {
        "ok": True,
        "corrida": corrida,
        "evaluadas": len(resultados),
        "por_estado": por_estado,
        "por_motivo": por_motivo,
    }


def _etapa_evidencia(
    repository,
    log,
    *,
    db_path,
    docs_dir,
    salida_evidencia,
    **_ignorados,
) -> dict[str, Any]:
    """Genera el documento de la corrida vigente y lo verifica por consulta."""
    from jobpulse_v15 import evidencia

    docs = Path(docs_dir) if docs_dir else evidencia.docs_dir_para(db_path)
    generado = evidencia.generar_evidencia(
        db_path=db_path, docs_dir=docs, salida=salida_evidencia, log=log
    )
    verificado = evidencia.verificar_evidencia(
        db_path=db_path, docs_dir=docs, doc=generado["ruta"], log=_noop
    )
    if verificado["ok"]:
        log("Evidencia OK: %d verificación(es) literal(es)." % verificado["verificaciones"])
    else:
        log("⚠️ Evidencia con %d discrepancia(s)." % len(verificado["fallos"]))
    return {
        "ok": bool(verificado["ok"]),
        "corrida": generado["corrida"],
        "documento": str(generado["ruta"]),
        "descartadas": generado["descartadas"],
        "no_confirmadas": generado["no_confirmadas"],
        "verificaciones": verificado["verificaciones"],
        "fallos": verificado["fallos"],
    }


_EJECUTORAS: Mapping[str, Callable[..., dict[str, Any]]] = {
    "scrape": _etapa_scrape,
    "analisis": _etapa_analisis,
    "ia": _etapa_ia,
    "reanalisis": _etapa_reanalisis,
    "backfill": _etapa_backfill,
    "paso5": _etapa_paso5,
    "evidencia": _etapa_evidencia,
}


def resumen_linea(resultado: Mapping[str, Any]) -> str:
    """Una línea legible del resultado completo (log/consola)."""
    partes = []
    for nombre in ETAPAS:
        etapa = resultado.get("etapas", {}).get(nombre)
        if not etapa:
            continue
        if "error" in etapa:
            partes.append("%s=ERROR" % nombre)
        elif nombre == "paso5":
            partes.append("paso5=%s" % etapa.get("corrida"))
        elif nombre == "ia":
            partes.append("ia=%s" % etapa.get("estado"))
        elif nombre == "reanalisis":
            partes.append("reanálisis=%d" % etapa.get("reanalizados", 0))
        elif nombre == "evidencia":
            partes.append("evidencia=%s" % ("OK" if etapa.get("ok") else "FALLOS"))
        elif nombre == "scrape":
            partes.append("scrape=%d nuevas" % etapa.get("jobs_new", 0))
        else:
            partes.append("%s=%s" % (nombre, "OK" if etapa.get("ok") else "—"))
    return ("PIPELINE: " + (" · ".join(partes) if partes else "sin etapas")) + (
        "" if resultado.get("ok") else "  ⚠️ CON PROBLEMAS"
    )
