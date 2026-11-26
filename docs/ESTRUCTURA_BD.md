# Estructura de la BD — `jobpulse_v15`

> Creado **2026-11-26** a partir de `data/jobpulse_v15.db` (esquema **28**).
>
> **⚠️ Regla de mantenimiento**: este documento describe el **esquema**.
> **Hay que actualizarlo con cada migración nueva**
> (`src/jobpulse_v15/migrations/0NN_*.sql` → `PRAGMA user_version`). Un
> esquema cambiado sin actualizar este doc deja a la siguiente sesión con el
> mapa viejo.
>
> Para regenerar el listado de tablas/columnas/índices (solo lectura):
> `.\.venv\Scripts\python.exe -X utf8 tools\esquema_bd.py`
>
> Los **recuentos de filas** son una instantánea con fecha (§5): cambian en
> cada corrida. La **estructura** (§4) solo cambia con migraciones.

---

## 1. Resumen

| | |
|---|---|
| Archivo | `data/jobpulse_v15.db` (no está en git) |
| Esquema (`PRAGMA user_version`) | **28** |
| Tablas | **27** |
| Índices | **38** |
| Vistas / triggers | 0 / 0 |

---

## 2. Cadena de flujo (por claves foráneas)

```
source_platforms (14)
   └─ source_sites (129)
         ├─ source_runs (129) ── source_run_sites (129)
         ├─ source_job_memory (736)          ← memoria de dedupe
         └─ job_source_records (736)         ← crudo por sitio
                ↓
             jobs (736)  ◄── job_manual_overrides (0)
          ↙        ↓         ↘
   job_area(736)  user_job_state(7)   job_analysis (735, is_current)
   area(20)←area_regla(51)                 │
                                    ↙               ↘
                       job_requirements(2956)   job_field_status(3675)
                                    ↑
                 concepto(775) ↔ concepto_no_normalizado(1150)
                 nivel_escala(11)

candidate_profile_facts (48) ──┐
   candidate_profile_imports(2)│
   candidate_profile_import_snapshots(0)
                               ├─→ job_match (6615 = 9 corridas × 735)
                               │        └─ job_match_decision (29)
                               └─→ (viabilidad se calcula al vuelo, sin tabla)

postulacion(0) · postulacion_senal(0) · applications(0)   ← Fase D, vacías
pipeline_etapa (23)                                        ← métricas por etapa
```

---

## 3. Capas

| # | Capa | Tablas | Qué guarda |
|---|---|---|---|
| 1 | **Fuentes / scraping** | `source_platforms` · `source_sites` · `source_runs` · `source_run_sites` · `source_job_memory` · `job_source_records` | Plataformas, sitios registrados, corridas de scrape, memoria de dedupe y crudo |
| 2 | **Corpus** | `jobs` · `job_area` · `area` · `area_regla` | El aviso crudo + su clasificación de área |
| 3 | **Análisis** | `job_analysis` · `job_requirements` · `job_field_status` | Análisis vigente, requisitos extraídos, estado por campo del pase IA |
| 4 | **Taxonomía** | `concepto` · `concepto_no_normalizado` · `nivel_escala` | Variantes → código canónico + cola de pendientes + escalas ordenadas |
| 5 | **Perfil** | `candidate_profile_facts` · `candidate_profile_imports` · `candidate_profile_import_snapshots` | Hechos del candidato (singleton) e importaciones de CV |
| 6 | **Matching (Paso 5)** | `job_match` · `job_match_decision` | Corridas del matching + firmas de la 2ª persona |
| 7 | **Postulaciones** | `postulacion` · `postulacion_senal` · `applications` | Estado de postulación, señales derivadas, aplicaciones (⚠️ 3 tablas, ver §6) |
| 8 | **Estado / métricas** | `user_job_state` · `pipeline_etapa` · `job_manual_overrides` | Descartes manuales, métricas por etapa, sobrescrituras |

---

## 4. Estructura por tabla

> Convención: `[PK]` clave primaria · `NOT NULL` · `DEFAULT=…` ·
> `FK → tabla.col`.

### 4.1 Fuentes / scraping

**`source_platforms`** (8 col) — plataformas.
`platform_id` PK · `name` NN · `provider_type` NN (`browser`/`api`/`rss`) ·
`default_language` · `default_config_json` NN `DEFAULT='{}'` · `enabled` NN
`DEFAULT=1` · `created_at` NN · `updated_at` NN.

**`source_sites`** (14 col) — sitios registrados. FK → `source_platforms.platform_id`.
`site_id` PK · `platform_id` NN · `site_name` NN · `company_name` · `base_url` NN ·
`country` · `enabled` NN `DEFAULT=1` · `run_groups_json` NN `DEFAULT='[]'` ·
`site_config_json` NN `DEFAULT='{}'` · `health_status` NN `DEFAULT='unknown'` ·
`consecutive_zero_runs` NN `DEFAULT=0` · `review_required` NN `DEFAULT=0` ·
`created_at` NN · `updated_at` NN.

**`source_runs`** (6 col) — corridas de scrape.
`run_id` PK · `started_at` NN · `finished_at` · `status` NN `DEFAULT='running'` ·
`run_kind` NN `DEFAULT='full'` · `summary`.

**`source_run_sites`** (11 col) — resultado por sitio en cada corrida.
FK → `source_sites.site_id`, `source_runs.run_id` (CASCADE).
`(run_id, site_id)` PK · `status` NN `DEFAULT='running'` · `jobs_found` NN ·
`jobs_valid` NN · `jobs_new` NN · `jobs_duplicate` NN · `error_message` ·
`review_required` NN `DEFAULT=0` · `started_at` NN · `finished_at`.

**`source_job_memory`** (6 col) — visto previo por (sitio, aviso fuente).
FK → `source_sites.site_id`.
`(site_id, source_job_id)` PK · `first_seen_at` NN · `last_seen_at` NN ·
`last_detail_fetch_at` · `content_hash`.

**`job_source_records`** (10 col) — registro crudo del aviso en su sitio.
FK → `jobs.job_id` (CASCADE), `source_sites.site_id`.
`(site_id, source_job_id)` PK · `job_id` NN · `source_url` · `raw_payload_json` ·
`source_updated_at` · `first_seen_at` NN · `last_seen_at` NN ·
`last_detail_fetch_at` · `content_hash`.

### 4.2 Corpus

**`jobs`** (27 col) — el aviso (sin FK; raíz del corpus).
`job_id` PK · `title` NN · `company` · `location_raw` · `country` · `region` ·
`city` · `work_mode` · `employment_type` · `schedule` ·
`posting_language` NN `DEFAULT='undetermined'` ·
`posting_language_origin` NN `DEFAULT='unknown'` ·
`date_published` · `expires_at` · `salary_raw` · `salary_min` · `salary_max` ·
`salary_currency` · `salary_period` · `description_raw` · `requirements_raw` ·
`first_seen_at` NN · `last_seen_at` NN · `updated_at` NN ·
`skills` · `languages` · `dup_of`.

**`job_area`** (5 col) — clasificación del aviso por área.
FK → `area.area_codigo` (CASCADE), `jobs.job_id` (CASCADE).
`(job_id, area_codigo)` PK · `confianza` NN `DEFAULT='titulo'` · `evidencia` ·
`clasificado_at` NN.

**`area`** (5 col) — catálogo de áreas.
`codigo` PK · `nombre` NN · `descripcion` · `orden` NN `DEFAULT=0` ·
`activa` NN `DEFAULT=1`.

**`area_regla`** (6 col) — reglas de clasificación. FK → `area.area_codigo` (CASCADE).
`regla_id` PK · `area_codigo` NN · `patron` NN · `fuente` NN `DEFAULT='titulo'` ·
`prioridad` NN `DEFAULT=0` · `activa` NN `DEFAULT=1`.

### 4.3 Análisis

**`job_analysis`** (10 col) — análisis vigente del aviso.
FK → `jobs.job_id` (CASCADE), `source_sites.source_site_id`.
`analysis_id` PK · `job_id` NN · `text_hash` NN · `extractor_version` NN ·
`analysis_status` NN · `is_current` NN `DEFAULT=1` · `analyzed_at` NN ·
`error_message` · `source_site_id` · `source_config_hash`.

**`job_requirements`** (16 col) — requisitos extraídos.
FK → `job_analysis.analysis_id` (CASCADE).
`requirement_id` PK · `analysis_id` NN · `category` NN · `value_code` ·
`value_text` NN · `qualifier` · `requirement_level` NN · `education_status` ·
`minimum` · `maximum` · `unit` · `evidence` · `origin` NN · `confidence` ·
`created_at` NN · `codigo_canonico`.

**`job_field_status`** (4 col) — estado por categoría del pase IA.
FK → `job_analysis.analysis_id` (CASCADE).
`(analysis_id, category)` PK · `field_status` NN · `checked_at` NN.

### 4.4 Taxonomía

**`concepto`** (7 col) — variante → código canónico.
`(categoria, variante)` PK · `codigo_canonico` NN · `origen` NN ·
`nivel_orden` · `activa` NN `DEFAULT=1` · `tipo` NN `DEFAULT='existencia'`.

**`concepto_no_normalizado`** (5 col) — cola de variantes sin resolver.
`(categoria, texto, origen)` PK · `veces` NN `DEFAULT=1` ·
`codigo_canonico_sugerido`.

**`nivel_escala`** (3 col) — escalas ordenadas (educación, idioma…).
`(categoria, codigo)` PK · `orden` NN.

### 4.5 Perfil del candidato

**`candidate_profile_facts`** (14 col) — hechos del perfil (singleton).
FK → `candidate_profile_imports.source_import_id` (SET NULL).
`profile_fact_id` PK · `category` NN · `value_code` NN · `value_text` NN ·
`qualifier` · `education_status` · `numeric_value` · `unit` · `notes` ·
`created_at` NN · `updated_at` NN · `origin` NN `DEFAULT='manual'` ·
`source_import_id` · `codigo_canonico`.

**`candidate_profile_imports`** (3 col) — importaciones de CV.
`profile_import_id` PK · `source_name` NN · `imported_at` NN.

**`candidate_profile_import_snapshots`** (12 col) — estado previo antes de importar.
FK → `candidate_profile_imports.profile_import_id` (CASCADE).
`(profile_import_id, category, value_code)` PK · `was_present` NN ·
`value_text` · `qualifier` · `education_status` · `numeric_value` · `unit` ·
`notes` · `previous_origin` · `previous_source_import_id`.

### 4.6 Matching (Paso 5)

**`job_match`** (16 col) — resultado por (aviso, corrida).
FK → `jobs.job_id` (CASCADE).
`(job_id, corrida_id)` PK · `estado` NN · `puntaje` · `cubiertos` · `faltantes` ·
`motivo` · `cobertura` · `evaluado_at` NN `DEFAULT=datetime('now')` ·
`cubiertos_count` · `faltantes_count` · `no_v_count` · `nc_count` ·
`total_req` · `evaluables` · `valida` NN `DEFAULT=1`.

**`job_match_decision`** (9 col) — firmas de la 2ª persona.
FK → `jobs.job_id` (CASCADE).
`id` PK · `job_id` NN · `dimension` NN · `veredicto` NN · `criterio` NN ·
`revisor` NN · `fecha` NN · `text_hash` NN · `corrida_id`.

### 4.7 Postulaciones

**`postulacion`** (5 col). FK → `jobs.job_id` (CASCADE).
`job_id` PK · `estado` NN · `portal` NN `DEFAULT=''` · `ultima_fecha` NN `DEFAULT=''` ·
`actualizado_en` NN.

**`postulacion_senal`** (12 col) — señales derivadas (correo/Workday).
FK → `jobs.job_id` (SET NULL).
`senal_id` PK · `job_id` · `portal` NN `DEFAULT='otro'` · `source_job_id` NN ·
`source_url` NN · `estado` NN · `fecha` NN `DEFAULT=''` · `remitente` NN ·
`asunto` NN · `titulo` NN · `empresa` NN · `detectado_en` NN.

**`applications`** (8 col) — ¿aplicaciones legacy?
`application_id` PK · `job_id` NN · `application_status` NN · `applied_at` ·
`next_action_at` · `notes` · `created_at` NN · `updated_at` NN. **Sin FK.**

### 4.8 Estado / métricas / overrides

**`user_job_state`** (9 col) — estado manual del usuario por aviso.
`job_id` PK · `title_snapshot` NN · `company_snapshot` · `source_url_snapshot` ·
`user_status` NN · `skip_automatic` NN `DEFAULT=1` · `notes` ·
`created_at` NN · `updated_at` NN. **Sin FK.**

**`pipeline_etapa`** (11 col) — métricas por etapa de `pipeline.ejecutar`.
`id` PK · `corrida_id` NN · `etapa` NN · `ok` NN · `duracion_ms` NN ·
`avisos` NN `DEFAULT=0` · `requisitos` NN `DEFAULT=0` · `errores` NN `DEFAULT=0` ·
`detalle_json` · `iniciado_en` NN · `terminado_en` NN. **Sin FK.**

**`job_manual_overrides`** (5 col) — sobrescrituras manuales de campo.
FK → `jobs.job_id` (CASCADE).
`(job_id, field_name)` PK · `source_value_json` NN · `override_value_json` NN ·
`updated_at` NN.

---

## 5. Instantánea de datos — **2026-11-26** (corrida `20261111_074200`)

> Los recuentos cambian en cada corrida; reproduce con
> `tools\esquema_bd.py` y `tools\checkpoint_objetivos.py`.

**Tablas (filas)**: `applications` 0 · `area` 20 · `area_regla` 51 ·
`candidate_profile_facts` 48 · `candidate_profile_import_snapshots` 0 ·
`candidate_profile_imports` 2 · `concepto` 775 · `concepto_no_normalizado` 1150 ·
`job_analysis` 735 · `job_area` 736 · `job_field_status` 3675 ·
`job_manual_overrides` 0 · `job_match` 6615 · `job_match_decision` 29 ·
`job_requirements` 2956 · `job_source_records` 736 · `jobs` 736 ·
`nivel_escala` 11 · `pipeline_etapa` 23 · `postulacion` 0 ·
`postulacion_senal` 0 · `source_job_memory` 736 · `source_platforms` 14 ·
`source_run_sites` 129 · `source_runs` 129 · `source_sites` 129 ·
`user_job_state` 7.

**Corpus (`jobs`, 736)**: título/empresa/país 736 · ciudad 570 (**166 sin
ciudad**) · `salary_min` 126 · `expires_at` 120 (**27 vencidos**) ·
`skills` 733 · `languages` 709 · `description_raw` 735 ·
`requirements_raw` **186** · `dup_of` **0**.

**Áreas**: 20 activas; las 736 vacantes **todas clasificadas** —
`otros` 179 · `ventas` 113 · `informatica` 84 · `produccion` 55 ·
`administracion` 53 · `ingenieria` 45 · `almacenamiento` 41 · `alimentacion` 29.
`area_regla`: **51 reglas, todas `fuente='titulo'`**.

**Requisitos (2956)**: skill 1490 · language 826 · experience 308 ·
education 260 · license 72 → **0 sin `codigo_canonico`**.

**Taxonomía**: `concepto` — skill 679 variantes/319 códigos · education 35/4 ·
language 33/11 · license 25/1 · experience 3/1. La cola
`concepto_no_normalizado` (1150) es **100 % `skill`**.

**Matching**: **9 corridas** (`20261107_225916` … `20261111_074200`), solo
`20261111_074200` con `valida=1` (735 filas). Vigente:
`revisar_a_mano` 385 · `calificada` 202 · `descartada` 101 ·
`datos_insuficientes` 36 · `sin_requisitos` 11.

**Perfil (48 facts)**: skill 23 · experience 9 · certification 6 · contact 5 ·
education 2 · language 2 · summary 1. Con `codigo_canonico`: skill/language/
education/license (27); **sin código: 21** (experience/certification/contact/
summary). **Áreas 0 · licencias 0.**

**Fuentes**: 14 plataformas (4 `browser`: ane, elempleo, indeed, linkedin ·
9 `api`: ashby, cinde, greenhouse, harvie, lever, procomer, recruitee, workable,
workday · 1 `rss`: successfactors). 129 sitios — workday 51 · workable 46 ·
greenhouse 8 · ashby 7 · successfactors 4 · recruitee 3 · lever 3 ·
+1 cada uno (procomer, linkedin, indeed, harvie, elempleo, cinde, ane).
`review_required` = 0 en todos.

**Pipeline**: `pipeline_etapa` — analisis 4 (ok 3) · backfill 4 · evidencia 4 ·
ia 2 · paso5 4 · reanalisis 4 · scrape 1.

**Estado usuario**: `user_job_state` 7, todas `dismissed`.

---

## 6. Deudas / alertas detectadas en el análisis

1. **Tres tablas de postulaciones, todas en 0** — `postulacion`,
   `postulacion_senal`, `applications`. Falta decidir cuál es **canónica**
   antes de la Fase D del plan (hoy `applications` ni siquiera tiene FK).
2. **`area_regla` solo por `titulo`** — 179 vacantes cayeron en `otros`.
3. **`requirements_raw` en 186/736** — buscar requisitos solo ahí pierde
   datos; el texto real está en `description_raw` (735).
4. **`user_job_state` = 7 `dismissed`** — el usuario solo descartó 7 avisos.
5. **`pipeline_etapa`**: `scrape` solo 1 corrida; `ia` solo 2.
6. **21 facts de perfil sin `codigo_canonico`** — existen pero el motor no
   los lee (solo lee skill/language/education/license).

---

## 7. Tablas que toca el flujo «mejores puestos»

| Fase | Tablas |
|---|---|
| A — perfil | `candidate_profile_facts`, `concepto`, `area` (flujo «Completar perfil», UI v2) |
| B — corpus | `source_*`, `jobs`, `job_area`, `job_analysis`, `job_requirements`, `job_field_status`, `concepto_no_normalizado` |
| C — Paso 5 | `job_match`, `job_match_decision`, `job_analysis`, `job_requirements` |
| D — postulaciones | `postulacion`, `postulacion_senal`, `applications` (vacías) |
| Revisión | (viabilidad se calcula al vuelo, sin tabla) |

---

## 8. Cómo actualizar este documento

1. **Con cada migración nueva** (`0NN_*.sql` + `PRAGMA user_version`):
   - regenerar el listado: `… -X utf8 tools\esquema_bd.py`;
   - revisar §4 (estructura) y §2 (cadena FK) y corregir lo que cambió;
   - actualizar el **número de esquema** de §1.
2. **Con cada corrida relevante**: actualizar §5 (instantánea) o marcarla
   como obsoleta; los recuentos no bloquean nada, pero una instantánea vieja
   engaña.
3. **Al detectar una deuda nueva**: añadirla a §6.
4. Si una tabla **se crea/borra/cambia de columnas** y este doc no se toca,
   se considera el cambio **incompleto**.
