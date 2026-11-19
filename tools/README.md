# tools

Manual operational and measurement scripts for the JobPulse CR v1.5 corpus:
status reporters, before/after extraction measurement, a local IA model A/B
benchmark, and two maintenance scripts that write to the live SQLite database.

**Kind:** flat leaf directory (10 scripts, no subdirectories, no `__init__.py`)
**Layer:** operator tooling, outside the installable package `src/jobpulse_v15/`
**Parent index:** [`../README.md`](../README.md)
**Subdirectories:** none

## Purpose

Nothing in `tools/` runs as part of the application, the CLI, or the UI v2.
Each script answers one operator question about the corpus that already lives
in `data/jobpulse_v15.db` — what the Paso 5 engine actually sees, how complete
the extraction is, what a run changed, which local IA model fills more fields —
so measurements are reproducible instead of ad-hoc SQL.

## Contents

| File | Reads | Writes DB | Summary |
|---|---|---|---|
| `estado_bd.py` | live DB | no | Corpus snapshot: job counts, table list, jobs per platform, missing `city`/`work_mode`, stale analyses, Paso 5 evidence freshness |
| `estado_extraccion.py` | live DB (read-only URI) | no | JSON snapshot of code extraction, taxonomy queue, structured fields and matching |
| `comparar_extraccion.py` | two JSON files | no | Diffs two `estado_extraccion.py` snapshots (ANTES vs DESPUES) |
| `cobertura_campos.py` | live DB | no | Field-coverage count and percentage per column |
| `progreso_enriquecimiento.py` | live DB | no | Missing count and % complete per field (critical + secondary) |
| `huecos_restantes.py` | live DB | no | Splits remaining gaps into unrecoverable (junk description) vs recoverable |
| `ver_sitio.py` | live DB | no | Dumps the `source_sites` configuration row(s) matching a pattern |
| `comparar_ia.py` | live DB, `:8081`/`:8082` `/metrics` | no | A/B benchmark of two local IA models on the same jobs: wall time, tok/s, fields filled |
| `corrida_medicion.py` | live DB | **yes** | Runs the real pipeline over the existing corpus (no scrape) |
| `limpiar_null.py` | live DB | **yes** | Rewrites the legacy literal `'null'` in `jobs.skills` / `jobs.languages` to SQL `NULL` |

## Public Interface

Scripts are invoked, never imported: `cobertura_campos.py`, `estado_bd.py`,
`limpiar_null.py` and `ver_sitio.py` run their whole body at import time (no
`main()` guard), so importing them executes their queries.

Canonical invocation — venv Python with UTF-8 output:

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py -X utf8 tools\<script>.py [args]
```

### `estado_bd.py` — corpus snapshot (read-only)

- **Invocation:** `python -X utf8 tools/estado_bd.py`
- **Output (stdout):** total jobs; jobs with `description_raw` longer than
  200 chars; table names; jobs per platform
  (`jobs ⋈ job_source_records ⋈ source_sites ⋈ source_platforms`); counts of
  jobs missing `city` and `work_mode`; number of analyses whose IA fields were
  never integrated (`analysis_flow.cuenta_analisis_obsoletos`); Paso 5 evidence
  state (`evidencia.estado_evidencia` → `al dia` / `DESACTUALIZADA (motivo)`,
  run id, document).
- **Exit code:** 0.
- **Boundary:** a non-zero "analisis obsoletos" means the Paso 5 engine sees
  fewer requirements than the posting has; it is a finding about the corpus,
  not an error of this script.

### `estado_extraccion.py` — extraction snapshot as JSON (read-only)

- **Invocation:**
  `python -X utf8 tools/estado_extraccion.py [--db RUTA] [etiqueta] [salida.json]`
- **Arguments:** `--db RUTA` must be the first two tokens of the command line
  (parsed before the label); `etiqueta` defaults to `estado`; `salida.json`
  makes the snapshot persist to disk (stdout still receives it).
- **Reads:** opens the database with a read-only URI (`file:…?mode=ro`) and
  applies **no** migrations, so it is safe against the real corpus.
- **Output:** the snapshot JSON, pretty-printed, and the line
  `guardado en <salida.json>` when a destination file was given.
- **Exit code:** 0.

### `comparar_extraccion.py` — snapshot diff (no DB)

- **Invocation:**
  `python -X utf8 tools/comparar_extraccion.py <antes.json> <despues.json>`
- **Input:** two snapshots produced by `estado_extraccion.py` (see the shared
  key contract below).
- **Output:** six blocks — requirements visible to the engine, taxonomy,
  requirements by category, by origin, structured fields, matching — each with
  signed deltas (`%+d`).
- **Exit codes:** `2` when fewer than two arguments are given (it prints its own
  docstring as usage); `0` otherwise.
- **Boundary:** unchanged code coverage between the two snapshots does not by
  itself mean "no improvement": if the run grew the corpus (more postings with
  requirements, more structured fields), coverage of code can stay flat while
  the corpus grows.

### `cobertura_campos.py` — field coverage (read-only)

- **Invocation:** `python -X utf8 tools/cobertura_campos.py`
- **Output:** `TOTAL JOBS: n` followed by nine check lines
  (`work_mode` resolved, `work_mode = unknown` (legitimately), `city`,
  `region`, `date_published`, `employment_type`, `salary_min`, `skills`,
  `languages`), each as `count (integer percentage)`.
- **Exit code:** 0.
- **Boundary:** the percentage is integer division over the job count, so an
  empty `jobs` table raises `ZeroDivisionError`.

### `progreso_enriquecimiento.py` — enrichment completion (read-only)

- **Invocation:** `python -X utf8 tools/progreso_enriquecimiento.py`
- **Input:** the database at `<repo>/data/jobpulse_v15.db` (path hardcoded
  relative to this file; `Database()` is not used).
- **Output:** header `BD: <name> | jobs: n`, then one line per field with
  `faltantes` and `% completo`.
- **Exit codes:** `1` when the database file does not exist; `0` otherwise.
- **Semantics:** critical fields (`city`, `region`, `work_mode`,
  `date_published`) are only evaluated over jobs with a non-empty
  `description_raw`; secondary fields (`employment_type`, `salary_raw`,
  `skills`, `languages`) are evaluated over all jobs. A field counts as missing
  when it is NULL, blank, or lowercased in `('null','none','unknown')`.

### `huecos_restantes.py` — gap triage (read-only)

- **Invocation:** `python -X utf8 tools/huecos_restantes.py`
- **Input:** the database at `<repo>/data/jobpulse_v15.db` (path hardcoded;
  `Database()` is not used). It reconfigures stdout to UTF-8 itself.
- **Output:** a table of seven gap categories (`city`, `region`,
  `work_mode 'unknown'`, `languages`, `skills`, `salary` with source text,
  `salary` without source text) with `total` and how many of those are junk;
  then the list of jobs with a missing `city` **and** a usable description
  (`job_id`, `title`, `location_raw`, description length).
- **Junk threshold:** `LENGTH(description_raw) < 200`.
- **Exit code:** 0.

### `ver_sitio.py` — site configuration dump (read-only)

- **Invocation:** `python -X utf8 tools/ver_sitio.py [patron]`
- **Arguments:** `patron` is a SQL `LIKE` pattern applied to `source_sites.site_id`;
  it defaults to `%procomer%`.
- **Output:** the `PRAGMA table_info(source_sites)` column list, then every
  matching row as `column: value` pairs, including `site_config_json`.
- **Exit code:** 0.

### `comparar_ia.py` — local IA model A/B (no DB writes)

- **Invocation:** `python tools/comparar_ia.py` — no arguments; the script
  reconfigures stdout to UTF-8 itself.
- **Fixed comparison set:**
  `("gemma4-e2b", "http://127.0.0.1:8081", "gemma4-e2b-qat")` and
  `("qwen3.5-2b", "http://127.0.0.1:8082", "qwen3.5-2b")`, with
  `N_POR_GRUPO = 2` jobs per gap type.
- **Selection:** two jobs per gap type (`work_mode='unknown'`; missing `city`
  with non-empty `location_raw`; missing `salary_min` with non-empty
  `salary_raw`; empty `languages`), all with `LENGTH(description_raw) > 200`;
  rows are read with plain `sqlite3` and then loaded through
  `Repository.get_job`, so the pipeline sees the same shape it always does.
- **Method:** per model, an `ia_enrichment.verificar_servidor_ia` preflight
  (a model whose server does not answer is skipped, and the other one still
  runs), then `ia_enrichment.enrich_job_fields` on each selected job. Token
  totals are the deltas of the llama.cpp `/metrics` counters
  (`tokens_predicted`, `tokens_prompt`) around each run.
- **Output:** per job and per model (`seconds`, filled fields), then a side-by-side
  comparison and a summary (wall time, tok/s, fields filled, `jobs_ok`), plus
  "MAS RAPIDO" / "MAS CAMPOS LLENADOS" when both models completed.
- **Requires:** two llama.cpp servers on `:8081` and `:8082`. A model whose
  server does not answer is **skipped** and the other one still runs
  (`tools/comparar_ia.py:145-157`) — a missing server is not a hard error.
- **Arguments:** the script has no `argparse` and no `sys.argv` validation; extra
  arguments are silently ignored (`tools/comparar_ia.py:18-25,134-166`).
- **Side effects:** it overwrites `JOBPULSE_IA_CACHE` with
  `data/comparacion_cache` **before** importing `ia_enrichment`, so the
  comparison is never served from the real IA cache; the cache directory is the
  only thing written. Extracted fields are printed and never persisted.

### `corrida_medicion.py` — pipeline run over the current corpus (writes)

- **Invocation:**
  `python -X utf8 tools/corrida_medicion.py [--sin-ia] [--db RUTA]`
- **Stages:** `("analisis", "ia", "reanalisis", "backfill", "paso5", "evidencia")`;
  `--sin-ia` removes the `ia` stage (the slow one). There is **no** `scrape`
  stage, so the network and the scrapers are never involved.
- **Behaviour:** prepends `<repo>/src` to `sys.path` (works without an editable
  install) and calls `pipeline.ejecutar(repo, etapas=…, db_path=…, progreso=log)`
  — the same orchestrator used by the CLI (`run_full_flow.py`) and by the UI v2
  "Procesar" button. **⚠ Not identical stage list:** the UI button explicitly
  includes `backfill` (`src/jobpulse_v15/ui_v2/tabs/scraping.py:403-413`),
  whereas `corrida_medicion.py` selects its own stage list and the pipeline's
  default stage list excludes `backfill` (`tools/corrida_medicion.py:33,52-54`;
  `src/jobpulse_v15/pipeline.py:49-58`). Each stage is logged with a
  `HH:MM:SS` timestamp.
- **Output:** `=== INICIO`/`=== FIN`, then `corrida_pipeline`, `corrida_paso5`,
  `ok`, `errores` and `pipeline.resumen_linea(resultado)`.
- **Exit codes:** `0` when the run reports `ok`; `1` otherwise.
- **Side effects:** **writes to the database.** Paso 5 always creates a NEW run
  in `job_match` (previous runs become `valida=0`), and analyses and IA fields
  are updated. Back up first
  (`python -X utf8 -m jobpulse_v15 backup --output data\backups\X.db`), or pass
  `--db RUTA` to measure against a copy instead of the real corpus.

### `limpiar_null.py` — legacy `'null'` cleanup (writes)

- **Invocation:** `python -X utf8 tools/limpiar_null.py`
- **Output:** the before/after counts of `skills='null'` and `languages='null'`,
  then the current `jobs sin skills` count.
- **Side effects:** when a non-zero count is found, it executes
  `UPDATE jobs SET skills = NULL WHERE skills = 'null'` and the same for
  `languages`. It takes no backup of its own.

### Shared JSON contract: `estado_extraccion.py` → `comparar_extraccion.py`

`estado_extraccion.py` is the only producer of this file format and
`comparar_extraccion.py` reads every one of its keys, so the two must change
together:

```text
etiqueta, avisos,
requisitos_vigentes, requisitos_con_codigo, requisitos_sin_codigo,
cobertura_codigo_pct, variantes_distintas_con_codigo,
codigos_distintos_usados, avisos_sin_ningun_requisito,
conceptos_en_taxonomia, cola_taxonomia,
por_categoria{<cat>: {total, con_codigo, sin_codigo}}, por_origen{<origin>: n},
campos{<campo>: {llenos, pendientes}},
match_corrida, match_estados{<estado>: n}, educacion_no_confirmada
```

## Invariants

- `tools/` is manual tooling: each script is run by file path with the venv
  Python and none of them is part of the application flow (scrape → analysis →
  IA → matching), which the CLI and the UI v2 drive through
  `src/jobpulse_v15/`.
- The working corpus is `data/jobpulse_v15.db`; it is not in version control, so
  a fresh clone has no corpus to measure. `Database.initialize()` can create or
  migrate an empty database in its place (`src/jobpulse_v15/db.py:39,118-153`).
- **Only `corrida_medicion.py` and `limpiar_null.py` write *data*.** Every
  other script is read-only **with respect to the corpus**, **but**:
  `estado_bd.py:8`, `cobertura_campos.py:5`, `ver_sitio.py:7`,
  `limpiar_null.py:5` and `comparar_ia.py:72` call `Database.initialize()`,
  which applies pending migrations and updates `PRAGMA user_version`
  (`src/jobpulse_v15/db.py:118-153`). `estado_extraccion.py` is explicitly the
  one that opens the DB read-only and skips migrations.
- `estado_extraccion.py` and `comparar_extraccion.py` are used as a pair; the
  snapshot keys above are their shared interface.
- Gap and eligibility thresholds are fixed constants in the source:
  `description_raw` of at least 200 characters defines a usable description, and
  anything shorter is classified as unrecoverable junk by `huecos_restantes.py`.
- Three scripts hardcode the database path as `<repo>/data/jobpulse_v15.db` and
  bypass `Database()`: `huecos_restantes.py`, `progreso_enriquecimiento.py` and
  `comparar_extraccion.py`. **⚠ `comparar_ia.py` does NOT bypass it**: it
  constructs `Database(str(db_path))` and invokes `db.initialize()`
  (`tools/comparar_ia.py:71-73`). The rest open it through `Database()`.
- `comparar_ia.py` must be allowed to set `JOBPULSE_IA_CACHE` before
  `ia_enrichment` is imported; reordering those two lines would make the
  benchmark read yesterday's cached answers and measure nothing.

## Side Effects and Boundaries

- **Database writes:** `corrida_medicion.py` (a new `job_match` run plus
  analysis/IA updates) and `limpiar_null.py` (in-place `UPDATE` on `jobs`).
  **Schema writes:** `estado_bd.py`, `cobertura_campos.py`, `ver_sitio.py`,
  `limpiar_null.py` and `comparar_ia.py` call `Database.initialize()`, which
  may apply pending migrations and bump `PRAGMA user_version`.
- **Filesystem writes:** `comparar_ia.py` writes its isolated IA cache under
  `data/comparacion_cache`; `estado_extraccion.py` writes only the JSON file
  named on the command line; `corrida_medicion.py` also writes
  `docs/PASO5_EVIDENCIA_<fecha>.md` through its `evidencia` stage
  (`tools/corrida_medicion.py:33,52-54`, `src/jobpulse_v15/pipeline.py:477-495`,
  `src/jobpulse_v15/evidencia.py:692-725`).
- **Network:** only `comparar_ia.py` talks to anything (the two llama.cpp
  servers). No script in this directory scrapes the web or starts a browser.
- **Not a verification gate:** the output of `tools/` is diagnostic. The
  auditable Paso 5 gate lives in `generar_evidencia_paso5.py` /
  `verificar_evidencia.py`; `estado_bd.py` merely reports the freshness of that
  evidence.
- `ver_sitio.py` prints every column of the matching `source_sites` rows,
  including per-site configuration, which can contain site-specific filters.

## Dependencies

| Direction | Dependency |
|---|---|
| Internal package | `jobpulse_v15.db.Database`, `jobpulse_v15.repository.Repository`, `jobpulse_v15.pipeline`, `jobpulse_v15.ia_enrichment`, `jobpulse_v15.ia_api.IAClient`, `jobpulse_v15.evidencia`, `jobpulse_v15.analysis_flow.cuenta_analisis_obsoletos` |
| External libraries | `httpx` (only `comparar_ia.py`); standard library `sqlite3`, `json`, `asyncio`, `re`, `time`, `argparse`, `pathlib`, `sys` |
| Data | `data/jobpulse_v15.db`; two `estado_extraccion.py` snapshots for `comparar_extraccion.py` |
| Runtime | venv Python with the package available (`pip install -e .`), always with `-X utf8` when DB text is printed; two llama.cpp servers on `:8081`/`:8082` for `comparar_ia.py` |

## Verification

These are manual scripts; their result is the printed report, read by an
operator. No linter, formatter or type check is configured in this project, so
the correctness gate is the regression suite, which runs on the **system**
Python (the venv has no pytest):

```powershell
python -m pytest tests/ -q
```

Smoke-check the read-only reporters against the live database:

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py -X utf8 tools\estado_bd.py
& $py -X utf8 tools\estado_extraccion.py smoke smoke.json
& $py -X utf8 tools\comparar_extraccion.py smoke.json smoke.json
```

## Related Documents

- [`../AGENTS.md`](../AGENTS.md) — project instructions, the operating rules for
  `tools/` and the database, and the `-X utf8` requirement when printing DB text.
- `../docs/PLAN_MEJORAS.md` — the backlog these measurements feed.
- `../docs/HANDOFF_SESION_*.md` — the most recently recorded measurements
  (schema version, taxonomy queue, current Paso 5 run).
