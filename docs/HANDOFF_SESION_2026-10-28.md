# Handoff — Sesión 2026-10-28: veredicto de enriquecimiento + filtro de paso 4 (grilla no queda vacía)

## TL;DR

Sesión de **cierre y estabilización del flujo O7** (scrape → reglas → IA → comparar perfil). Se implementó el **veredicto de enriquecimiento** (`ia_estado.py`): el flujo ya no asume que la IA terminó, mide la BD antes/después del pase y decide `completado` / `parcial` / `sin_trabajo` (OK) vs `atascado` / `fallido`. Se arregló la **grilla vacía del paso 4**: el filtro `matched` hardcodeado devolvía 0 jobs (370/447 análisis son `partial`), ahora `elegir_filtro_compatibilidad()` usa `matched` si existe y si no muestra todos los vigentes. Se agregó objetivo **O10 (mejorar filtros)** a DESARROLLO_v15.md. Suite: **293 tests, todos verdes**. Tree limpia salvo scripts de diagnóstico desechables.

## Lo que se hizo

- **Nuevo `src/jobpulse_v15/ia_estado.py`**: `snapshot_enriquecimiento()` (huecos por campo, separando recuperables vs desc. basura `<200` chars), `avance()` (solo deltas positivos), `evaluar_ia()` (5 estados), `resumen_linea()`. La BD manda sobre las stats de `pase_completo`.
- **`run_full_flow.py`** (CLI end-to-end): paso 3 mide antes/después, imprime veredicto, devuelve `bool`, exit 0/1, toast ✅/⚠️. Incluye `clean_run.py` para limpieza de corrida de prueba (`clean_run.py SI`).
- **`src/jobpulse_v15/ui.py`**: paso 3 del flujo y botón "Enriquecer" muestran el veredicto en el diálogo y status bar.
- **`src/jobpoulse_v15/ui.py` paso 4 (grid vacío)**: `elegir_filtro_compatibilidad(conteo)` → `matched` si existe, si no `Cualquiera` (todos los vigentes); loguea vigentes de totales, ocultas por ventana O8 (6 meses), conteo por estado, filtro aplicado; status bar `Flujo completo — IA <estado> | filtro: <etiqueta>`.
- **DESARROLLO_v15.md**: tabla O1→O10, agregado **O10 Mejorar filtros de búsqueda y compatibilidad** (🟡 diseñado).
- **`tests/test_ia_estado.py`** (13 tests) + **`tests/test_ui.py`** (4 tests `TestElegirFiltroCompatibilidad`). Suite total **293 passed, 44 subtests**.
- Commit `c98302e` (veredicto IA) y `4662f66` (grid paso 4).

## Decisiones de diseño (esta sesión)

1. **La BD es fuente de verdad para el éxito/fallo del enriquecimiento** — `pase_completo()` devuelve stats optimistas; si la BD no avanzó con huecos recuperables pendientes → `atascado` (fallo). La descripción basura no cuenta como fallo (la IA no puede extraer de ella).
2. **Paso 4 nunca deja la grilla vacía**: si `matched = 0`, muestra todos los vigentes (`Cualquiera`) y explica por qué en el diálogo (análisis `partial` por diseño conservador del analizador).
3. **Filtros desechables no se commitean**: `monitor_ia.py`, `status_ia.py`, `vigilar_enriquecimiento.py`, `quick_check.py`, `check_enriched.py`, `_diag_*.py`, `_prog_ia.py` son herramientas de diagnóstico de esta sesión; no forman parte del producto.

## Estado de objetivos (tabla O1–O10)

| Objetivo | Estado |
|---|---|
| O1 enriquecimiento IA | ✅ completo (veredicto IA integrado 28-10) |
| O2 búsqueda data-first | 🟡 O2.1 locations Indeed + O2.2 filtro "Req." |
| O3 fetchers ATS | ⏳ |
| O4 calibración gate-vs-IA | ⏳ redefinir |
| O5 higiene de datos | 🟢 solo O5.3 (re-barrido ~46 basura) |
| O6 perfil del candidato | 🟢 O6.3 matching + O6.4 dedupe semántico |
| O7 operación UI-first | ✅ completo (servidor bajo demanda, toast, veredicto) |
| O8 ciclo de vida | 🔵 diseñado — plan de 7 pasos listo (no implementado aún) |
| O9 optimización UI | ⏳ placeholder |
| **O10 mejorar filtros** | 🟡 diseñado (`elegir_filtro_compatibilidad` implementado 28-10) |

## Cómo retomar

```powershell
# Arranque UI (SIEMPRE -X utf8)
.\.venv\Scripts\python.exe -m jobpulse_v15.ui

# BD
.\.venv\Scripts\python.exe -X utf8 tools\estado_bd.py

# Tests (python del SISTEMA, no venv)
python -m pytest tests/ -q

# Servidor IA bajo demanda (lo abre la UI al hacer "Enriquecer")
.\ia-server.bat  # solo si se quiere pre-arrancar

# Limpieza de corrida de prueba
.\.venv\Scripts\python.exe -X utf8 clean_run.py SI
```

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/jobpulse_v15/ia_estado.py` | Veredicto de enriquecimiento (nuevo) |
| `run_full_flow.py` | CLI end-to-end scrape→reglas→IA→veredicto (nuevo) |
| `clean_run.py` | Limpieza de corrida de prueba (nuevo) |
| `src/jobpulse_v15/ui.py` | Paso 3 veredicto + paso 4 filtro elegido (modificado) |
| `tests/test_ia_estado.py` | 13 tests de `ia_estado` (nuevo) |
| `tests/test_ui.py` | 4 tests `TestElegirFiltroCompatibilidad` (modificado) |
| `DESARROLLO_v15.md` | Objetivos O1-O10 + O10 filtros (modificado) |
| `AGENTS.md` | Estado de referencia actualizado (ya actualizado) |

## Datos de contexto

- IA server: puerto **8081**, modelo `gemma4-e2b-qat`; política O7.3 = arranca bajo demanda, detiene solo lo que abrió.
- BD: `data/jobpulse_v15.db` — 447 jobs (última corrida). 423 vigentes (ventana 6 meses O8), 24 ocultas por `date_published` viejo (Workday/Indeed re-publican con fecha antigua).
- En paso 4: `matched=0`, `needs_review=290`, `no_required=128`, `not_registered=5` → filtro aplicado = `Cualquiera`.
- Tests con system python (`python -m pytest`), app con venv `.\.venv\Scripts\python.exe -X utf8`.
- v1.x congelado en `D:\Proyectos\jobpulse_cr` — SOLO lectura, nunca modificar.

## Pendiente inmediato

1. **O8 — implementar plan de 7 pasos** (migración 008 `dup_of`, `ciclo_vida.py`, `repository.py` `solo_vigentes`/`ventana_retencion_meses`, `ingestion.py` herencia, `configuration_window.py` pestaña Vacantes, `ui.py` board `solo_vigentes`, `tests/test_ciclo_vida.py`). Referencia exacta en DESARROLLO_v15.md §O8 sub-diseño y handoff 2026-10-27.
2. **O10 filtros pendientes**: `solo_vigentes` (`date_published` vs `last_seen_at`), visibilidad opt-in recurrentes/aplicadas, columna "Req." (O2.2).
3. Luego: O5.3 re-barrido basura · O2.1/O2.2 · O6.3/O6.4 · O9 · O3 · O4.

## Commits de esta sesión

- `c98302e` feat(ia): veredicto de enriquecimiento integrado al flujo (exito/fallo)
- `4662f66` fix(ui): paso 4 del flujo deja la grilla vacía → filtro elegido sobre datos
