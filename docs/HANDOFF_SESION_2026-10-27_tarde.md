# Handoff — Sesión 2026-10-27 (tarde): cierre O8/O9, listo para implementar

## TL;DR

Sesión de **cierre e investigación** (cero código O8). El usuario recordó que
el ciclo de vida "ya lo había resuelto antes": **tenía razón** — el mecanismo
existía COMPLETO en el proyecto v1.x y no se portó a v1.5. Se formalizaron
objetivos **O8** (ciclo de vida) y **O9** (UI), se corrigieron los docs con el
hallazgo, se tomaron las decisiones de diseño y **quedó el plan de 7 pasos
listo para implementar** (abajo). La próxima sesión empieza directo por el
paso 1, sin re-investigar.

## Lo que se hizo

- Hallazgo verificado leyendo el código de `D:\Proyectos\jobpulse_cr`
  (v1.x, congelado, SOLO lectura): `core/dedupe.py` (`clave_duplicado_exacto`,
  tokens normalizados ASCII/orden-insensible), `core/database.py`
  (`marcar_duplicados_exactos` → `dup_of` sin borrar filas + tombstones
  `jobs_excluidas` con clave empresa|título|ubicación + `purge_expired(dias)`
  TTL), `core/exclusiones.py` (`filtrar_offers` barrera de ingesta). v1.5 solo
  tiene `source_job_memory` por `(site_id, source_job_id)` = idempotencia de
  re-scrape del MISMO id, NO barrera de republicación.
- Matiz del usuario: lo que v1.x **NUNCA** resolvió es el **triage MANUAL**
  (marcar a mano revisado/aplicado) — esa mitad es **nueva de v1.5 y ya está
  implementada** (`user_job_state` + `applications` + diálogos). O8 = la unión:
  las piezas automáticas portadas alimentan lo que el usuario marcó.
- Decisions del usuario (cierre del día): defaults abajo. 6 commits hoy:
  `b784779` `1dd6359` `6a41e7d` `d436d8f` `c043742` `6207ead`. Tree limpia.

## Decisiones de diseño (Aprobado por el usuario)

1. **Flujo 100% UI** (nunca CLI). Recurrentes/aplicadas: **ocultas por
   defecto**, visibles solo con opt-in.
2. **Marcar revisado/aplicado = SIEMPRE manual** (sin autodetección) — ya
   existe, no se toca.
3. **Match de republicación**: compañía igual + **huella de descripción**
   exacta o ratio ≥ 0.92 (título NO como criterio primario — O5.4 lo probó
   con ANE "Confidencial").
4. **Herencia de estado al ingest**: la copia nace oculta
   (`skip_automatic=1` + nota de herencia) y `dup_of` apunta al original.
   NUNCA se borra ni se funden datos.
5. **Ventana de recurrentes**: configurable en pestaña Configuración
   (selector 1/2/3/6/12), **default 3 meses** (decidido). Ancla =
   `user_job_state.updated_at`; fuera de la ventana la copia entra como
   vacante NUEVA (re-aplicable).
6. **O8.4 retención**: también configurable en la misma pestaña; portar
   `purge_expired` como **OCULTAR (no borrar)**; default **6 meses
   (propuesto, no confirmado)**.
7. **O8.1 categorías**: el agente genera el borrador desde los 295 jobs
   (`tools/categorias_borrador.py`); usuario corrige después.
8. Duplicado EXACTO = auto (patrón probado v1.x); dudoso = revisión manual
   (`quality duplicates`).

## Estado de objetivos

| Objetivo | Estado |
|---|---|
| O1 enriquecimiento | ✅ completo (295/295) |
| O2 búsqueda data-first | 🟡 O2.1 locations Indeed + O2.2 filtro "Req." |
| O3 fetchers ATS | ⏳ |
| O4 calibración | ⏳ redefinir |
| O5 higiene | 🟢 solo O5.3 (re-barrido ~46 basura) |
| O6 perfil | 🟢 O6.3 matching + O6.4 dedupe semántico |
| O7 UI-first | ✅ (falta prueba de humo del usuario) |
| **O8 ciclo de vida** | 🔵 diseñado — implementar (plan abajo) |
| O9 optimización UI | ⏳ placeholder |

## Cómo retomar — PLAN DE 7 PASOS (implementar en la próxima sesión)

1. **`migrations/008_ciclo_vida.sql`**: `ALTER TABLE jobs ADD COLUMN dup_of
   TEXT` + índice. Patrón de descubrimiento: `db.py`
   (`^(\d{3})_[a-z0-9_]+\.sql$`). Nunca editar migraciones ya aplicadas.
2. **NUEVO `src/jobpulse_v15/ciclo_vida.py`** (solo stdlib):
   `huella_descripcion()` (lowercase + solo alfanuméricos — normalización
   O5.4), `clave_exacta()` (empresa|título|ubicación tokens
   orden-insensibles ASCII, None si falta ubicación — port de
   `core/dedupe.py` de v1.x), `_ratio` = difflib.SequenceMatcher (umbral
   0.92), `MESES_PERMITIDOS = (1, 2, 3, 6, 12)`, `preferencias()` leyendo
   `~/.jobpulse_v15/ui_config.json` (claves `ventana_republicaciones_meses`
   default 3, `retencion_puestos_meses` default 6),
   `evaluar_herencia(repository, job)` — solo hereda estados
   `reviewed`/`applied` (+`skip_automatic=1`); guard: skip si el job nuevo ya
   tiene estado manual; typing de Repository sin importarlo (evitar ciclo).
3. **`repository.py`**: métodos nuevos `estados_para_herencia(desde_iso)`
   (JOIN `user_job_state`+`jobs`, solo reviewed/applied) y
   `marcar_dup_of(job_id, original_job_id)` (UPDATE auditable, no funde);
   `search_jobs` (línea ~1522) kwargs `solo_vigentes: bool = False` +
   `ventana_retencion_meses: int | None = None` — condición tras el bloque de
   salario (~1690, ANTES de `levels_placeholders` ~1701); **orden de
   `conditions` = orden de `params`** (placeholders `?`). Lógica portada de
   v1.x `purge_expired`: NO (expires_at válida < hoy) AND NO (sin expires_at
   + date_published < corte) AND NO (sin fecha legible + first_seen_at <
   corte).
4. **`ingestion.py`** hook en `_persist_in_run` (~line 86, tras `save_job`
   cuando `is_new_source_record`): `evaluar_herencia` best-effort
   (try/except + `logger.warning`; el archivo NO tiene logger aún — añadir).
5. **`configuration_window.py`**: pestaña nueva 5 "Vacantes" (2 combobox
   meses desde `MESES_PERMITIDOS`); `_load_all_settings` (línea 664) cargar
   las 2 claves; **CRÍTICO: `_save_all` (línea 726) usa `_save_ui_config`
   que SOBREESCRIBE el dict completo (solo 4 keys de UI) → cambiar a
   load-merge-update-save o se pierden las demás claves**. Importar
   defaults/`MESES_PERMITIDOS` desde `ciclo_vida`.
6. **`ui.py`** línea ~812 (board): añadir `solo_vigentes=True` +
   `ventana_retencion_meses=` desde `ciclo_vida.preferencias()`.
7. **`tests/test_ciclo_vida.py`** (NUEVO): patrón de `tests/test_repository.py`
   (tempdir + Database + Repository + `register_platform("workday")` /
   `register_site("intel-cr")`; `save_job` dict mínimo
   job_id/title/company/city). Casos: huella/clave normalization; herencia
   exacta (clona estado + `dup_of` + oculta, `include_manually_skipped=False`
   la excluye); ratio ≥ 0.92; fuera de ventana (UPDATE
   `user_job_state.updated_at` viejo); dismissed/archived NO heredan;
   empresa distinta NO hereda; `solo_vigentes` (vencida/vieja/fresca);
   `preferencias()` round-trip parcheando `ciclo_vida.CONFIG_FILE`. NO
   instanciar `ConfigurationWindow` en tests (patrón
   `test_configuration_window.py`). Suite hermética:
   `python -m pytest tests/ -q` (pytest vive en el python del SISTEMA, no
   venv) → 244 tests + los nuevos.

Después del paso 7: commit por bloque coherente (migración+módulo, repo,
ingest+UI, tests) o un solo commit si prefiero — punto de partida limpio.

## Comandos y archivos clave

```powershell
# Arranque / UI / BD (SIEMPRE -X utf8)
.\jobpulse-v15.bat
.\.venv\Scripts\python.exe -m jobpulse_v15.ui
.\.venv\Scripts\python.exe -X utf8 tools\estado_bd.py
```

- v1.x (LEER solo): `D:\Proyectos\jobpulse_cr\core\dedupe.py`,
  `core\database.py` (línea 264 `marcar_duplicados_exactos`, 224
  `purge_expired`, 101 `jobs_excluidas`), `core\exclusiones.py`.
- v1.5 anclas: `repository.py` (`search_jobs` ~1522; condiciones/params
  1634–1700; `set_user_job_state` 1095; `get_job` 824),
  `ingestion.py` (`_persist_in_run` 74–120), `configuration_window.py`
  (`CONFIG_FILE` 43, `_load_all_settings` 664, `_save_all` 726, `_save_ui_config`
  57), `ui.py` (board 812; `open_configuration` 2062), `db.py` (migraciones).
- Sub-diseño completo con referencias exactas a v1.x:
  `DESARROLLO_v15.md` → bloque "O8 — sub-diseño" (§ tras la tabla §3).

## Datos de contexto

- BD activa: `data/jobpulse_v15.db` — 295 jobs (ANE 240, Indeed 30, CINDE 17,
  LinkedIn 7, Procomer 1). Identidad real en ANE = DESCRIPCIÓN, no
  título+empresa ("Confidencial"). `expires_at` solo ANE la llena.
- Config UI: `~/.jobpulse_v15/ui_config.json` (hoy solo 4 claves; se suman
  las 2 nuevas de O8).
- **Empezar sin cache**: la nueva sesión OpenCode arranca con contexto limpio
  (leer ESTE handoff primero). La caché IA de disco
  (`data/usuario/ia_cache/`) NO afecta a O8 (no hace llamadas IA); para
  aislarla en pruebas/benchmarks fijar `JOBPULSE_IA_CACHE` a otra carpeta o
  renombrarla (gotcha 1).
- v1.x congelado: SOLO lectura. La rama `fork-v15` del repo viejo jamás se
  pushea (password ANE pre-purga).

## Pendiente inmediato (orden propuesto)

1. Implementar O8 — 7 pasos de arriba (empieza la próxima sesión).
2. `tools/categorias_borrador.py` — borrador O8.1 desde los 295 jobs
   (usuario corrige).
3. Confirmar default de retención (6 meses propuesto) / prueba de humo O7.
4. Luego: O5.3 re-barrido basura · O2.1/O2.2 · O6.3/O6.4 · O9 · O3 · O4.
