# Package: `jobpulse_v15.migrations`

> Versioned SQLite schema definitions for JobPulse CR v1.5. Each `0NN_*.sql`
> file is one immutable, forward-only schema step applied in numeric order and
> tracked by `PRAGMA user_version` (current version: **28**).

## Overview

This directory holds the **entire database schema as an ordered sequence of
SQL migrations** — it contains no Python code and is never imported. The
application code (`db.py`) discovers these files, applies any whose number
exceeds the database's current `PRAGMA user_version`, and bumps `user_version`
after each one. Schema evolution therefore happens **only** by adding a new
numbered file; applied migrations are never edited and `ALTER` is never run by
hand.

The directory has two distinct kinds of migration:

| Kind | Examples | What it does |
| --- | --- | --- |
| **Schema (DDL)** | `001`–`016`, `018`, `022`, `024`, `027` | Create/alter tables, columns, indexes; occasionally rebuild a table to change a `CHECK` constraint. `010` is **mixed**: DDL plus DML (two `UPDATE concepto`, one `UPDATE job_requirements`, and an `INSERT ... SELECT` seeding `concepto_no_normalizado`). |
| **Data (DML / taxonomy)** | `017`, `019`, `020`, `021`, `023`, `025`, `026`, `028` | Seed or curate rows in `concepto`, `nivel_escala`, `job_requirements`, `candidate_profile_facts`; one-time data fixes. Taxonomy curation files are named `023_taxonomia_curacion_tanda_1`, `025_taxonomia_curacion_tanda_2`, `026_taxonomia_curacion_tanda_3` (there is no `02x_taxonomia_*` glob). |

## Public Interface

There is no callable API. The **integration contract** is the directory
convention itself:

- **Filename pattern**: `0NN_<descripcion_en_snake_case>.sql`, zero-padded to
  three digits. Ordering is lexical = numeric.
- **Migration number** `NN` must equal the target `user_version` for that step.
  Applying `0NN` sets `user_version = NN`.
- **Idempotence is declared only in some file headers** — it is **not** uniform:
  - `CREATE TABLE`/`CREATE INDEX` use `IF NOT EXISTS` only in part of the files
    (e.g. `001` ×12 tables/×13 indexes, `003`, `004`, `005`, `007`, `008`,
    `002` ×2, `013`, `016` ×5 tables/×6 indexes, `022` ×2 tables/×2 indexes
    **lack** it), so those steps are **not** replay-safe.
  - `ALTER TABLE ... ADD COLUMN` steps are **not** idempotent (SQLite fails if
    the column exists). Only `010`, `011`, `013` and `014` state this in their
    header; the `ALTER` steps in `002`, `004`, `006`, `008` and `015` carry no
    such note.
  - Files that **declare** an idempotence flag in the header: `010`, `011`,
    `013`, `014`, `017`, `019`, `020`, `021`, `023`, `025`, `026`, `028`.
  - `017`, `020`, `021`, `023`, `025`, `026` are **idempotent** data migrations
    (they only add rows that are missing, keyed by the `concepto` /
    `nivel_escala` primary keys). `019` is **not** purely additive: it also
    runs three mutating `UPDATE`s (`concepto`, `job_requirements`,
    `candidate_profile_facts`).
- **`-- jobpulse:transaccion-propia` marker** (first line of `022`): signals
  that the file manages its own `BEGIN`/`COMMIT` and toggles
  `PRAGMA foreign_keys`. Required because SQLite forbids changing
  `PRAGMA foreign_keys` inside an open transaction, which table-rebuild
  migrations need. `db.py` must **not** wrap such files in an outer transaction.

### Schema created (by migration)

| Migration | Objects introduced / changed |
| --- | --- |
| `001_initial_schema` | `source_platforms`, `source_sites`, `jobs`, `job_source_records`, `source_job_memory`, `source_runs`, `source_run_sites`, `job_analysis`, `job_requirements`, `job_field_status`, `user_job_state`, `applications` (+ indexes) |
| `002_analysis_source` | `job_analysis` source columns; `idx_job_analysis_current_status`, `idx_job_requirements_lookup` |
| `003_candidate_profile` | `candidate_profile_facts` |
| `004_candidate_profile_import_history` | `candidate_profile_imports`, `candidate_profile_import_snapshots`; extra fact columns |
| `005_job_manual_overrides` | `job_manual_overrides` |
| `006_job_skills_languages` | `jobs.skills`, `jobs.languages` (+ indexes) |
| `007_candidate_profile_harvard_sections` | Rebuilds `candidate_profile_facts` (Harvard CV sections) |
| `008_ciclo_vida` | `jobs.dup_of` (+ index) |
| `009_concepto_normalizacion` | `nivel_escala`, `concepto`, `concepto_no_normalizado` (+ seed rows) |
| `010_codigo_canonico_tipo` | `concepto.tipo`, `job_requirements.codigo_canonico`; seeds `concepto_no_normalizado` |
| `011_candidate_profile_facts_canonico` | `candidate_profile_facts.codigo_canonico` |
| `012_job_match` | `job_match` |
| `013_job_match_corrida_id` | Rebuilds `job_match` to add `corrida_id` |
| `014_job_match_columnas` | `job_match` counter columns (`cubiertos_count`, `faltantes_count`, `no_v_count`, `nc_count`, `total_req`, `evaluables`) |
| `015_job_match_valida` | `job_match.valida` (+ indexes) |
| `016_areas` | `area`, `area_regla`, `job_area`; rebuilds `candidate_profile_facts` and `job_match` (new `area`/`fuera_de_area` states) |
| `018_postulaciones` | `postulacion_senal`, `postulacion` (+ indexes) |
| `022_site_requiere_login` | Rebuilds `source_sites` and `source_run_sites`; **own transaction**. Note the different spellings: `source_sites.health_status` gains `'requiere_login'`, while `source_run_sites.status` gains `'requires_login'`. |
| `024_pipeline_etapa` | `pipeline_etapa` (+ indexes) |
| `027_job_match_decision` | `job_match_decision` (+ index) |

### Data migrations (taxonomy / one-time fixes)

| Migration | Effect |
| --- | --- |
| `017_educacion_granular` | Adds education `concepto` variants (master/MBA → posgrado, associate/technical → ciclo corto, "bachiller" → secundaria). |
| `019_google_workspace` | Corrects the erroneous `google-workspace` → `microsoft-365` alias in `concepto`, `job_requirements`, and profile facts; adds `active-directory` variant. |
| `020_conceptos_alineacion` | Adds missing skill/license concepts so previously invisible requirements gain a `codigo_canonico`. |
| `021_taxonomia_fuente` | Grows `concepto` from structured job fields (`jobs.skills`/`jobs.languages`): languages, aliases, new competencies. |
| `023` / `025` / `026` | Taxonomy curation tandas 1–3 (`023_taxonomia_curacion_tanda_1`, `025_taxonomia_curacion_tanda_2`, `026_taxonomia_curacion_tanda_3`): aliases + new concepts for the most-demanded queue entries. |
| `028_estudiante_avanzado` | Inserts the **"estudiante avanzado"** education level (escalón 3) into `nivel_escala`, shifts `concepto.nivel_orden` ≥ 3 up by one, **and rewrites two `nivel_escala` rows** (`universitaria` 3→4, `posgrado` 4→5) — that second shift is what completes the 1..5 ladder. One-time (non-idempotent) `+1` shift. |

## Invariants & Constraints

- **Forward-only, append-only**: an applied migration is never modified. Any
  schema change is a **new** `0NN_*.sql` file. `NN` must be strictly greater than
  the previous highest.
- **`user_version` is the single source of truth** for which migrations have
  run. There is no bookkeeping table.
- **Gaps are not allowed** in practice; the sequence is contiguous `001..028`.
- **Table rebuilds preserve data**: migrations that change a `CHECK` (`007`,
  `016`, `022`) copy **all** existing rows and never drop or merge data; they
  recreate indexes afterwards.
- **`foreign_keys` discipline**: only `022` disables/enables `PRAGMA
  foreign_keys`, and it does so outside any outer transaction (see the
  `jobpulse:transaccion-propia` marker).
- **Data migrations never touch `job_match`**: match states change only via a
  **new** Paso 5 run (`corrida_id`, previous runs `valida=0`), never an in-place
  `UPDATE`. This is stated in the headers of `027`/`028`.
- **Privacy invariant** (`018`): application-signal tables keep only minimal
  email derivatives (status, date, sender, subject, reference) — never the
  message body.
- **Business-rule coupling**: the education ladder seeded here (`nivel_escala`,
  `concepto.nivel_orden`) must stay consistent with
  `docs/REGLAS_NEGOCIO_EDUCACION.md` and the matching module.

## Dependencies

- **Applied by** `src/jobpulse_v15/db.py` (the caller, outside this directory).
  The CLI migrates the schema whenever it opens the DB. **`init-db` DOES
  migrate** (it calls `database.initialize()` and prints the resulting schema
  version); `backup` and `db check` do **not** migrate.
- **Read by** `matching.py`, `repository.py`, `analysis_flow.py`,
  `taxonomia.py`, `viabilidad.py`, `decisiones.py`, and the UI v2 — all consume
  the tables these files define.
- **Depends on** nothing outside SQLite; the taxonomies the DDL references
  (`area` seeds) are loaded from `src/jobpulse_v15/seeds/areas.json` via
  `init-areas`, not from these files.

## Usage

Applying migrations (requires the repository's Python entrypoint):

```powershell
$py = ".\.venv\Scripts\python.exe"
# Any CLI command that opens the DB migrates it and prints e.g.
#   [esquema] Se aplicaron las migraciones N-M
& $py -X utf8 -m jobpulse_v15 --help
# Integrity + FK check (does NOT migrate):
& $py -X utf8 -m jobpulse_v15 db check
```

To add a schema change: create `029_<descripcion>.sql`, and update the
hard-coded version assertions in the tests (search for `28`).

## Verification

Tests run on the **system** Python (the venv has no pytest):

```powershell
python -m pytest tests/ -q
```

Directly relevant suites: `tests/test_migraciones.py` (applies the full chain and
asserts `user_version`) and `tests/test_pipeline_metricas.py` (schedule/version
assumptions). Many tests build a temporary DB and apply all migrations in
`setUp`, so the suite takes minutes, not seconds.

## Notes / Caveats

- **Adding a migration requires updating version assertions**: `tests/test_migraciones.py`
  and `tests/test_pipeline_metricas.py` hard-code the current version (`28`);
  leaving them stale breaks the suite.
- **`jobs.posting_language` is `NOT NULL`** (tests use `undetermined`); `mixed`
  is a valid value.
- **`job_requirements` is keyed by `analysis_id`** (FK to `job_analysis`), not by
  `job_id` — never insert requirements with raw SQL; use
  `Repository.save_analysis`.
- **`concepto` has no `nombre`** column: it is `codigo_canonico` + `variante`.
- **Taxonomy curation is a data migration** (`02x_taxonomia_*`); never `UPDATE`
  `concepto` by hand. Use `taxonomia.demanda_corpus` to measure demand (the
  `veces` column of `concepto_no_normalizado` is rewritten on each curation).
- **`028` is intentionally non-idempotent**: its `nivel_orden + 1` shift is
  applied exactly once because `user_version` guarantees single execution.

### File inventory (28 migrations)

`001_initial_schema`, `002_analysis_source`, `003_candidate_profile`,
`004_candidate_profile_import_history`, `005_job_manual_overrides`,
`006_job_skills_languages`, `007_candidate_profile_harvard_sections`,
`008_ciclo_vida`, `009_concepto_normalizacion`, `010_codigo_canonico_tipo`,
`011_candidate_profile_facts_canonico`, `012_job_match`,
`013_job_match_corrida_id`, `014_job_match_columnas`, `015_job_match_valida`,
`016_areas`, `017_educacion_granular`, `018_postulaciones`,
`019_google_workspace`, `020_conceptos_alineacion`, `021_taxonomia_fuente`,
`022_site_requiere_login`, `023_taxonomia_curacion_tanda_1`,
`024_pipeline_etapa`, `025_taxonomia_curacion_tanda_2`,
`026_taxonomia_curacion_tanda_3`, `027_job_match_decision`,
`028_estudiante_avanzado`.
