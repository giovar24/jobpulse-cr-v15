# jobpulse_v15

> Núcleo del proyecto: pipeline (scrape → análisis → IA → matching), motor del
> Paso 5, scrapers, capa IA y la UI v2. Paquete instalable con entry point de
> consola `jobpulse-v15` → `jobpulse_v15.cli:main`.

**Tipo:** Peanut (directorio con código propio y subdirectorios con contrato)
**Hijos:** [`migrations/`](migrations/README.md) · [`providers/`](providers/README.md) · [`ui_v2/`](ui_v2/README.md)
**Sin código:** `seeds/` (JSON/CSV semilla: `areas.json`, `ats_cr.json`, `workday_cr.json`, `successfactors_cr.json`, `division_territorial_cr.csv`, `lugares_cr.csv`)

## Propósito

`jobpulse_v15/` implementa todo el dominio de JobPulse CR v1.5 sobre SQLite: la
ingesta de ofertas, el análisis por reglas, el enriquecimiento con IA, el motor
de matching del Paso 5 y su evidencia auditable, la taxonomía de conceptos, el
perfil del candidato, el ranking ATS y la viabilidad técnica, y la UI v2. El CLI
(`cli.py`) y la UI v2 son las dos fachadas y comparten las mismas
implementaciones (`analysis_flow.py`, `pipeline.py`, `matching.py`).

## Interfaz pública

### Orquestación y persistencia

| Módulo | Contrato |
|---|---|
| `pipeline.py` | `ejecutar(repository, *, etapas, progreso, evaluar_todo, sites, pages, port, max_vacantes, limite_analisis, db_path, docs_dir, salida_evidencia, should_stop)` encadena las etapas con UNA implementación cada una. `ETAPAS_POR_DEFECTO = ("analisis","ia","reanalisis","paso5","evidencia")` (sin `scrape`/`backfill`); `ETAPAS_QUE_NECESITAN_ARGUMENTOS = {"scrape": …}`; `resumen_linea(resultado)`. Una etapa desconocida es `ValueError`. |
| `pipeline_metricas.py` | Fuente única de `ETAPAS = ("scrape","analisis","ia","reanalisis","backfill","paso5","evidencia")`; `PREFIJO_CORRIDA = "pipe_"`; `registrar_etapa`, `consultar_corrida(s)`; `contadores_etapa` traduce cada etapa a `{avisos, requisitos, errores}`. |
| `repository.py` | `Repository` (persistencia) y `job_review_reasons`: `save_job` (upsert atómico jobs + records + memoria), `save_analysis`, `search_jobs`, `record_site_result`, `finish_run`, `compare_jobs_to_candidate_profile`, `candidate_profile_status`, `backfill_requirements_canonico`, `get_potential_duplicate_groups`. Conjuntos cerrados: `REQUIREMENT_CATEGORIES`, `FIELD_STATUSES`, `ANALYSIS_STATUSES`, `REQUIREMENT_LEVELS`, `REQUIREMENT_ORIGINS`, `PROFILE_FACT_CATEGORIES`, `USER_JOB_STATUSES`, `APPLICATION_STATUSES`, `JOB_MANUAL_OVERRIDE_FIELDS`. Vocabulario de motivos de revisión: `JOB_REVIEW_REASON_CODES`, `JOB_REVIEW_FIELD_PREFIXES`. |
| `db.py` | `Database` (BD por defecto `data/jobpulse_v15.db`), `Database.connection()` (context manager con `PRAGMA foreign_keys=ON`), `schema_version()`, `check_integrity()`, `backup_to()`, `initialize()` (aplica migraciones; respeta el marcador `-- jobpulse:transaccion-propia`); `MigrationError`; `_MIGRATION_NAME` exige `NNN_nombre.sql`. |
| `analysis.py` | Extractor por reglas: `RuleBasedExtractor.extract(text) -> ExtractionResult` (ValueError si el texto está vacío); `EXTRACTOR_VERSION = "rules-2"`; catálogos `_SKILLS`/`_LANGUAGES`. |
| `analysis_flow.py` | Implementación ÚNICA del análisis (CLI + UI + orquestador): `extract_job_analysis`, `preparar_analisis`, `avisos_con_campos_sin_integrar`, `avisos_con_texto_cambiado`, `reananalizar_con_campos_fuente`, `reananalizar_texto_cambiado`, `cuenta_analisis_obsoletos`, `analisis_refleja_campos`; `VERSION_ANALISIS`. |
| `ingestion.py` | `IngestionService` (`import_offers`, `fetch_and_import`, `_validate_offers`); `IngestionError(run_id, message)` (ambos argumentos obligatorios). Un `RequiereLoginError` produce corrida `requires_login` (no `error`). |
| `seed_ats.py` | `cargar_directorio` / `registrar_directorio(repository, …)` siembran los tableros ATS CR desde `seeds/*.json`; `PLATAFORMAS`, `PLATAFORMAS_SOPORTADAS`, `_GRUPO_DIRECTOS`. |
| `caches.py` | `estado_caches`/`estado_ia`, `limpiar`/`limpiar_ia` (devuelven `ResultadoLimpieza`), `archivos_huerfanos_ia`; `PATRON_CACHE_IA = ^[0-9a-f]{32}\.json$`, `CLAVE_IA`, `TITULO_IA`, `InfoArchivo`. |
| `exports.py` | `write_job_search_csv`, `_safe_csv_cell` (neutraliza celdas tipo fórmula); `PROFILE_COMPATIBILITY_LABELS`. |
| `diagnostico.py` | `diagnostico()` (solo lectura) y `ReporteDiagnostico`, `resumen_corto`. |
| `location_utils.py` | `normalize_cr_location`, `normalize_work_mode` (unknown si no reconoce), `normalize_employment_type`, `extract_date_from_source_updated`. |

### Matching, viabilidad, evidencia, decisiones

| Módulo | Contrato |
|---|---|
| `matching.py` | Motor del Paso 5. `EvaluadorPaso5(connection, *, aplicar_filtro_areas=True)` con `evaluar_job`, `requisitos_efectivos`, `evaluar_educacion`, `nivel_efectivo_fact`, `cumple_language`/`cumple_license`/`cumple_experience`. Funciones `ejecutar_paso5`, `guardar_resultados`, `confirmar_requisito_universitario`, `nivel_educativo_del_texto`, `porcentaje_estudios_parciales`, `porcentaje_avance_fact`. Constantes `UMBRAL_COBERTURA=0.60`, `UMBRAL_PUNTAJE=0.80`, `UMBRAL_ESTUDIANTE_AVANZADO=80.0`, escalera `NIVEL_SECUNDARIA=1`…`NIVEL_POSGRADO=5`, `ESTADO_*`, `MOTIVO_*`, `PRIORIDAD_MOTIVOS`. Dataclasses `Requisito`, `Resultado`, `ConfirmacionEducacion`. |
| `viabilidad.py` | Ajuste técnico 0-100 (no probabilidad): `calcular_viabilidades`, `evaluar_viabilidad`, `resumen_bandas`, `a_fila`, `puntuar_componentes`; bandas `BANDA_APLICAR` (≥85) / `BANDA_REVISAR` (80-85) / `BANDA_NO_PRIORITARIO` / `BANDA_SIN_DATOS` / `BANDA_VETO`; umbrales `UMBRAL_APLICAR=85.0`, `UMBRAL_REVISAR=80.0`; `PESOS_CATEGORIA`, `PESO_NIVEL`; estados `ESTADO_CUMPLE/FALTA/NO_VERIFICABLE/NO_CONFIRMADO/BLOQUEANTE`. |
| `evidencia.py` | `generar_evidencia`, `verificar_evidencia`, `estado_evidencia`, `corrida_vigente`, `doc_por_defecto`; citas LITERALES contra `jobs`; datos `MEDICION`, `PROMOVIDAS_13`. |
| `decisiones.py` | Firmas de la segunda persona (tabla `job_match_decision`): `guardar_decision`, `decision_vigente`, `cargar_firma`, `aplicar_firma` (rechaza citas `«…»` no literales), `validar_citas`, `texto_aviso`, `hash_texto`/`hash_aviso` (en memoria) y `texto_aviso_en_base`/`hash_aviso_en_base` (aviso ya guardado); `DIMENSION_EDUCACION`, `VEREDICTOS = ("bloqueo_real","no_bloqueo","dudoso")`. |
| `ats.py` | Ranking ATS 0-100 (ranking, no calificación): `ats_score`, `rank_with_ats`, `ranking_ats`, `componentes_ats`, `perfil_ats_desde_facts`, `cobertura_skills`; `PESOS_RANKING`, `UMBRALES_RANKING`, `DEFAULT_WEIGHTS`, `VEREDICTO_THRESHOLDS`, `SKILL_LEXICON`. |

### Taxonomía, idiomas, perfil, áreas, ciclo de vida, postulaciones

| Módulo | Contrato |
|---|---|
| `taxonomia.py` | `demanda_corpus(connection)`, `curar(connection, *, aplicar=False, limite=50)`. |
| `conceptos.py` | `mapa_conceptos`, `resolver(connection, requirements)`, `encolar_sin_concepto` (único punto de entrada de la cola), `es_variante_encolable`; `CATEGORIAS_CONCEPTO`. |
| `skills_fuente.py` | `requisitos_de_fuente`, `parsear_skills`, `parsear_languages`, `mapa_normalizado`, `clasificar`; `ORDEN_CATEGORIAS`. |
| `idiomas.py` | `detectar_idioma_del_aviso` (determinista), `normalizar_nivel`, `orden_nivel`, `codigo_canonico_del_idioma`, `idioma_en_skill`; `NIVELES_CEFR`, `CODIGO_IDIOMA`. |
| `salario.py` | `declara_salario`, `contexto_salario`, `predicado_sql_hueco`, `registrar_funciones`; `PALABRAS_SALARIO`, `VENTANA_MONTO=80`. |
| `areas.py` | `sembrar_taxonomia`, `clasificar_texto`, `clasificar_oferta`, `clasificar_todas`, `conteo_por_area`, `areas_del_perfil`, `es_fuera_de_area`; `AREA_OTROS="otros"`. |
| `ubicaciones_cr.py` | Jerarquía territorial CR (país → provincia → cantón → distrito), leída de `seeds/lugares_cr.csv` y `seeds/division_territorial_cr.csv`; `nombre_canonico`, `resolver_direccion` (usadas por el CLI en `location normalize`). |
| `ciclo_vida.py` | `evaluar_herencia`, `corte_de_ventana`, `corte_de_retencion`, `preferencias`, `guardar_preferencias`; `UMBRAL_RATIO=0.92`, `ESTADOS_HEREDABLES=("reviewed","applied")`, `MESES_PERMITIDOS`. |
| `candidate_profile.py` | `read_cv_text`, `extract_candidate_profile`; límites `MAX_CV_FILE_BYTES` (15 MB), `MAX_PDF_PAGES=100`, `SUPPORTED_CV_SUFFIXES={.docx,.pdf,.txt}`. |
| `profile_model.py` | `facts_from_harvard_json`, `facts_desde_perfil_dict`, `suggestion_to_fact`, `fact_*`, `parse_*_notes`; `SECCIONES_CV`. |
| `postulaciones.py` | `clasificar`, `clasificar_mensajes`, `estado_mas_avanzado`, `sin_respuesta`, `Senal` (PURO, sin red); `ESTADOS_POSTULACION`, `DOMINIOS_PORTAL`. |
| `correo_postulaciones.py` | `recolectar_senales`, `ConfigCorreo`, `mensaje_a_senal`, `leer_mensajes`; solo derivados mínimos (el cuerpo nunca se guarda). |
| `workday_postulaciones.py` | `recolectar_aplicaciones`, `parsear_json_aplicaciones`, `parsear_html_aplicaciones`, `patrones_candidato`, `mapear_estado`; `ErrorWorkdayPostulaciones`. |

### IA

| Módulo | Contrato |
|---|---|
| `ia_api.py` | Cliente OpenAI-compatible: `IAClient` (`chat`, `achat`, `chat_json`, `listar_modelos`, `disponible`, `es_local`, `hash_vacante`), `PRESETS` (openrouter, nvidia, google, ollama, ollama-local, lmstudio, custom), `ProviderPreset`, `PROMPT_VERSION="v3"`, `CACHE_DIR` (`JOBPULSE_IA_CACHE`), `opt_int`, errores `IAError`/`IAModeloError`/`IACuotaError`/`IAPeticionError`. |
| `ia_enrichment.py` | `run_ia_enrichment`, `pase_completo`, `enrich_job_fields`, `enrich_job`, `reananalizar_tras_ia`, `work_mode_por_patrones`, `verificar_servidor_ia`, `aviso_privacidad`, `tope_vacantes`, `MAPEO_SAVE`; esquemas/prompts por campo. |
| `ia_estado.py` | `snapshot_enriquecimiento`, `evaluar_ia`, `avance`; `CRITICOS`, `SECUNDARIOS`, `BASURA`. |
| `ia_servidor.py` | `asegurar_servidor`, `arrancar_servidor`, `ServidorIA.detener`, `servidor_arriba`, `es_endpoint_local`, `comando_llama`. |
| `cv_ia.py` | `extraer_cv_ia`, `sanea_harvard`, `PROMPT_SISTEMA`. |
| `instalacion_ia.py` | `descargar_modelo`, `instalar_llamacpp`, `estado_modelo`, `verificar_integridad`, `diagnostico`; `REPO_MODELO`, `ARCHIVOS_MODELO` (Gemma 4 E2B QAT). |

### Scraping

| Módulo | Contrato |
|---|---|
| `scraper.py` | `FETCHERS` (14 plataformas → `"módulo:Clase"`, import perezoso), `instanciar_fetcher`, `plataforma_de_sitio`, `ejecutar_barrido(...) -> ResumenBarrido`; estados `ESTADO_OK/ERROR/PAUSADO/SIN_FETCHER/NO_EXISTE/CANCELADO/REQUIERE_LOGIN`; dataclasses `Progreso`, `ResultadoSitio`, `ResumenBarrido`. |
| `scrape_dispatch.py` | `construir_llamada`, `necesita_navegador`; `_CON_PAGINAS`, `_CON_PUERTO = {ane, indeed, linkedin, elempleo}`. |
| `workday.py`, `greenhouse.py`, `ashby.py`, `lever.py`, `recruitee.py`, `workable.py`, `successfactors.py`, `harvie.py` | Un `*Fetcher.fetch(...) -> *Offers` por plataforma ATS (API/RSS pública, sin navegador); cada `*Offers` es una `list` con atributo `jobs_skipped`. `harvie.py` consulta `https://heyharvie.com/api/candidate/jobs` y no tiene subcomando CLI propio (solo vía `ejecutar_barrido` / `run_ats_scrapes.py`). |
| `cinde.py`, `procomer.py` | API pública (GraphQL / REST), sin navegador. |
| `ane.py`, `indeed.py`, `linkedin.py`, `elempleo.py` | Scrapers de navegador: reciben el `port` CDP del caller; `ane.AneFetcher.fetch` y `fetch_detalles_conocidos` (re-barrido por URL). |
| [`providers/`](providers/README.md) | Portales con login/Cloudflare (contrato propio). |

### Navegador y credenciales

| Módulo | Contrato |
|---|---|
| `browser_manager.py` | `BraveManager` (arranca Brave con CDP y conecta Playwright), `asegurar_brave`, `get_browser_context`, `cdp_vivo`, `puerto_cdp_configurado` (`BRAVE_CDP_PORT`, def. 9222), `perfiles_disponibles`, `detectar_brave`. |
| `sesion_navegador.py` | `guardar_cookies`/`leer_cookies`/`hay_sesion`/`borrar_sesion` y variantes sync/async; sesiones en `data/usuario/sesiones/` (secreto). |
| `credenciales.py` | `credencial`, `upsert_credencial`, `borrar_credencial`, `lista_sitios_login`, `registrar_requerimiento`, `agregar_sitio_login`, `quitar_sitio_login`; passwords SOLO en el keyring de Windows; datos en `data/empresas/`. |
| `ane_login.py` | `login_ane(port: int = 9222) -> Dict[str, str]` (crea la `page` de Playwright internamente), `cerrar_brave_ordenado`, `CFG` (selectores ANE). |
| `requiere_login.py` | `RequiereLoginError`, `mensaje_requiere_login`. |

### Entrada

| Módulo | Contrato |
|---|---|
| `cli.py` | `main() -> int` (entry point `jobpulse-v15`): grupos `init-db`, `schema-version`, `backup`, `db`, `platform`, `site`, `init-sources`, `init-areas`, `areas`, `taxonomy`, `pipeline`, `credenciales`, `login`, `run`, `analysis`, `decision`, `quality`, `ingest`, `scrape`, `search`, `location`, `enrich`, `viabilidad`, `postulaciones`. `load_dotenv()` al importar. Casi todos los comandos migran el esquema al abrir la BD (`[esquema] Se aplicaron las migraciones N-M (base: <ruta>)`). |
| `__main__.py` | `python -m jobpulse_v15` → `cli.main()`. |
| `__init__.py` | `__version__ = "1.5.0"`. |

## Invariantes

- **`preferred` no bloquea** y los requisitos/hechos **sin `codigo_canonico` se ignoran en silencio** (`matching` filtra `codigo_canonico IS NOT NULL`) → perfil invisible ⇒ `sin_requisitos`.
- **Umbrales congelados del Paso 5** (`0.60` cobertura / `0.80` puntaje) y **corrida nueva siempre** (`job_match`: la anterior queda `valida=0`, nunca `UPDATE`).
- **Nunca se descarta por falta de información**: sin datos ⇒ `no_verificable` / `revisar_a_mano`.
- **La firma de la segunda persona solo aplica cuando el motor quedó en `no_confirmado`** y está anclada al `sha256` del texto; una cita `«…»` debe ser literal del aviso.
- **Viabilidad ≠ contratación**: un rechazo nunca etiqueta aptitud; ≥1 requisito `required` faltante topa la banda en `revisar`.
- **Privacidad**: de correo/portal solo derivados mínimos (estado, fecha, remitente, asunto, referencia); el cuerpo del mensaje nunca se guarda; passwords solo en el keyring / `.env` (nunca en el repo).
- **IA local o externa intercambiable**: con endpoint externo no se arranca nada local y se exige confirmación de privacidad; `llama-server`/Brave se arrancan bajo demanda y se apagan **solo si este proceso los abrió** (política O7.3).
- **Los scrapers de navegador nunca crean un navegador**: reciben el `port` CDP; `scraper.ejecutar_barrido` abre Brave bajo demanda y lo cierra solo si lo abrió.
- **El escalón educativo** sigue la escalera de 5 niveles (1 secundaria … 5 posgrado); el 80 % es umbral exigido en aviso y perfil.
- **Idioma del aviso**: el requisito de idioma es el idioma en que está escrito el aviso, salvo que el aviso pida idiomas.

## Efectos secundarios

- **BD SQLite** `data/jobpulse_v15.db`: escrituras en `jobs`, `job_analysis`/`job_requirements`/`job_field_status`, `source_runs`/`source_run_sites`, `job_match`, `pipeline_etapa`, `candidate_profile_facts`, `job_match_decision`, `concepto_no_normalizado`, `job_area`, `postulacion_senal`/`postulacion`.
- **Archivos**: `.env` (IA/navegador), `~/.jobpulse_v15/ui_config.json`, `data/empresas/*.json`, `data/usuario/sesiones/*.json`, `data/usuario/ia_cache/` (raíz configurable con `JOBPULSE_IA_CACHE`), `docs/PASO5_EVIDENCIA_*.md`, CSVs.
- **Red**: scrapers (httpx/urllib + CDP), cliente IA (`{base_url}/chat/completions`, `/models`), IMAP de postulaciones. `workday.py` NO usa navegador: consume la API con `urllib.request`.
- **Procesos/OS**: arranca/para `llama-server` y Brave (solo si los abrió), keyring de Windows, `webbrowser.open`, `pip install` del instalador IA.

## Dependencias

- **Hijos:** [`migrations/`](migrations/README.md), [`providers/`](providers/README.md), [`ui_v2/`](ui_v2/README.md).
- **Externas** (`pyproject.toml`): `lxml`, `pypdf`, `python-docx`, `httpx[http2]`, `playwright`, `beautifulsoup4`, `python-dotenv`, `aiosqlite`, `keyring`; extras `[dev]` (pytest, pytest-asyncio) y `[ia]` (openai, huggingface_hub).
- **Semillas:** `seeds/` (áreas, directorio ATS CR, división territorial y lugares CR).

## Verificación

pytest corre en el **python del sistema** (el `.venv` no trae pytest):

```powershell
python -m pytest tests/ -q
python -m pytest tests/test_matching.py -q
```

Suite completa ~20-25 min: muchos tests crean una BD temporal y aplican las 28
migraciones en `setUp`.
