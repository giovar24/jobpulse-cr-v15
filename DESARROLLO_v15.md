# JobPulse CR v1.5 — Guía de Desarrollo y Estado del Proyecto

> **Propósito**: Documento único de referencia para continuar el desarrollo si se cambia de IA/agente.
> Contiene: comparación arquitecturas, pasos ejecutados, pendientes, objetivos y comandos clave.

> **⚠️ CONVENCIÓN DE SESIONES (obligatoria)**: cuando el usuario dice "vamos a otra sesión", se debe
> **escribir `docs/HANDOFF_SESION_YYYY-MM-DD.md`** antes de cerrar, con la misma estructura del handoff
> de 2026-10-25: TL;DR, lo que se hizo, decisiones de diseño, estado de objetivos (tabla), cómo retomar
> (comandos), archivos clave, datos de contexto y pendiente inmediato. La sesión nueva debe **empezar
> leyendo el handoff más reciente** para no arrastrar contexto acumulado.

---

## 1. COMPARACIÓN ARQUITECTURAL: PRINCIPAL vs v1_5

| Aspecto | **Principal (raíz)** | **v1_5 (fork)** | Notas |
|---------|---------------------|-----------------|-------|
| **BD** | `data/jobs.db` (SQLite simple) | `data/jobpulse_v15.db` (migraciones versionadas, FK, `integrity_check`, backup atómico) | v1_5 es **más robusta** |
| **Persistencia** | `core/database.py` + `save_jobs()` | `Repository.save_job()` + `IngestionService` (runs, health tracking, dedupe atómico) | v1_5 **auditable y transaccional** |
| **Scrapers** | `providers/boards/` + `providers/directos/` (clases `BaseProvider`) | Módulos planos `ane.py`, `cinde.py`, `workday.py`... con `fetch(site, ...) → XxxOffers` | v1_5 **declarativo y testeable** |
| **Orquestación** | `main.py` (asyncio.gather, fases hardcoded en `BARRIDOS`) | CLI `scrape <provider> --site/--group` + `IngestionService.fetch_and_import()` | v1_5 **modular, cada fuente independiente** |
| **Fuentes** | Hardcoded en `main.py` | Declarativas: `platform add` + `site add` (JSON config, sin credenciales) | v1_5 **config en BD, no en código** |
| **Dedupe** | `core/dedupe.py` (boards vs directos cross-source) | `job_field_status` + `source_job_memory` + review manual (no automerge) | v1_5 **más conservador** |
| **Búsqueda** | Semántica (embeddings) + ATS score + keywords | SQL estructurada (texto + filtros + requisitos + `profile_compatibility`) + embeddings (`search_engine.py`) | Paridad razonable |
| **IA/Embeddings** | `sentence-transformers` + `core/ia_api.py` (Gemini/NVIDIA/OpenRouter) | `ia_api.py` (OpenAI-compatible) + **enriquecimiento IA local** (`ia_enrichment.py`, Gemma en 8081) + `ia_calibracion.py` | ✅ Cliente externo + pase IA local |
| **CV Parsing** | `cv2profile.py` + `reporte_cv.py` (PDF→perfil Harvard/ATS completo) | Editor harvard-ats-v1 (`ui_perfil.py`) + reglas + **pase IA `cv_ia.py`** (E2E Gemma/Gemini, integrado al asistente de import) | ✅ Gap cerrado (O6.2) |
| **Auth/Session** | `core/browser_manager.py` + `hacer_login.py` + `credenciales.py` + `providers/login/` | ✅ FASE 3 completa: `browser_manager` + `credenciales` (keyring) + `providers/login/auto_login.py` + `browser_sites.py` | Cerrado |
| **Scheduler** | `recordatorio.py` + `jobpulse.cmd` (login + recordatorio Windows) | Parcial: launcher `jobpulse-v15.bat` (venv + IA + Brave CDP + UI); sin recordatorio | Gap medio |
| **Tests** | 7 unitarios (texto, dedupe, gate) | 25 suites / 358 tests + 44 subtests (pytest, python del sistema) | v1_5 **mejor cobertura** |
| **UI** | Streamlit (`app.py`) legacy + Tkinter (`ui.py`) completa | Tkinter (`ui.py`) completa (filtros, edición, seguimiento, perfil, calidad, duplicados, admin fuentes) | Similares |

---

## 2. ESTADO ACTUAL DE v1_5 (2026-10-26)

### ✅ YA IMPLEMENTADO Y FUNCIONAL

| Componente | Archivo(s) | Estado |
|------------|------------|--------|
| BD + migraciones (7 esquemas) | `db.py`, `migrations/001-007.sql` | ✅ Completo |
| `Repository` (CRUD sitios, jobs, analysis, profile) | `repository.py` | ✅ Completo |
| `IngestionService` (runs, health, validación, idempotencia) | `ingestion.py` | ✅ Completo |
| CLI base (`init-db`, `backup`, `db check`, `platform`, `site`, `run`, `search`, `quality`, `ingest`, `location`) | `cli.py` | ✅ Completo |
| Scrapers API-only | `workday.py`, `greenhouse.py`, `ashby.py`, `lever.py`, `recruitee.py`, `workable.py`, `successfactors.py` | ✅ Completo + tests |
| Análisis estructurado (`rules-1`) | `analysis.py` | ✅ Completo |
| UI Tkinter completa | `ui.py` | ✅ Completa |
| Tests (13 suites) | `tests/test_*.py` | ✅ Pasan |
| Config declarativa (platform/site) | `repository.py` + CLI | ✅ Funcional |

### ✅ Scrapers CR browser (antes EN PROGRESO — completados 2026-10-24/25)

ANE, CINDE, Procomer, LinkedIn e Indeed: lógica portada E integrados con la CLI
(`scrape ane|cinde|procomer|linkedin|indeed`), la UI y `run_scrapes.py`; los
browser reciben `port` CDP del caller (nunca crean navegador).

### ❌ PENDIENTE (gaps reales al 2026-10-26)

| Componente | Prioridad | Notas |
|------------|-----------|-------|
| **Dedupe cross-source (boards ↔ directos)** | 🟡 Alta | Hoy solo idempotencia misma-fuente + `quality duplicates` (revisión manual); `dup_of` previsto, sin columna |
| **Scheduler / recordatorio Windows** | 🟢 Media | Launcher `jobpulse-v15.bat` ya existe; falta portar `recordatorio.py` |
| **O2 / O3 / O4** (ATS + ranking en búsqueda UI; validar 7 fetchers ATS huérfanos; calibración gate-vs-IA) | 🟡 | O2.2 ✅ y O3 ✅ cerrados el 2026-11-04 · O4 sigue sin objeto (el `gate` ya no existe: el motor es `matching.py`) → **proponer cerrarlo como *superseded*** |
| **Operación UI-first / servidores bajo demanda (O7)** | ✅ Resuelto (2026-10-27) | La UI gestiona Brave (abre/cierra en el barrido) y el servidor IA (botón "Enriquecer", pase IA de CV) bajo demanda |

---

## 3. PLAN DE EJECUCIÓN (ORDEN DE PRIORIDAD)

### FASE 1: Scrapers Browser + API CR (Semana 1-2) — **COMPLETADO**
**Objetivo**: Traer el 80%+ de vacantes de Costa Rica.

| Tarea | Archivo(s) | Comando CLI | Estado |
|-------|------------|-------------|--------|
| Completar ANE fetcher + CLI | `ane.py`, `cli.py` | `scrape ane --site ane-cr --pages 15 --port 9222` | ✅ 100% |
| Completar CINDE fetcher + CLI | `cinde.py`, `cli.py` | `scrape cinde --site cinde-cr --pages 10` | ✅ 100% |
| Completar Procomer fetcher + CLI | `procomer.py`, `cli.py` | `scrape procomer --site procomer-cr --pages 5` | ✅ 100% |
| Completar LinkedIn fetcher + CLI | `linkedin.py`, `cli.py` | `scrape linkedin --site linkedin-cr --pages 2 --port 9222` | ✅ 100% |
| Completar Indeed fetcher + CLI | `indeed.py`, `cli.py` | `scrape indeed --site indeed-cr --pages 2 --port 9222` | ✅ 100% |
| **Bootstrap fuentes CR** | `cli.py` (comando `init-sources`) | `jobpulse-v15 init-sources` | ✅ **Completo** |

**Patrón obligatorio para cada fetcher**:
```python
def fetch(self, site: dict, *, pages: int, search_text: str | None, 
          skip_source_job_ids: set[str] | None, port: int | None = None, **kwargs) -> XxxOffers:
    # 1. Validar params
    # 2. Si browser: conectar a CDP en `port` (pasado por caller)
    # 3. Scrapear → lista de dicts con keys: source_job_id, source_url, source_updated_at, job, raw_payload
    # 4. job dict con TODOS los campos normalizados (ver schema en repository.py)
    # 5. Devolver XxxOffers(offers, jobs_skipped=N)
```

### FASE 2: Capa de Inteligencia (Semana 2-3) — **COMPLETADO**
| Tarea | Archivo(s) | Notas |
|-------|------------|-------|
| `ia_api.py` | **Nuevo** | ✅ Cliente LLM compatible OpenAI (OpenRouter/NVIDIA/Gemini/Ollama/LM Studio/llama.cpp) |
| `search_engine.py` | Nuevo | Embeddings locales + cache incremental + expansión ES↔EN |
| `ats.py` | Nuevo | Score ponderado (skills 40%, título 30%, exp 15%, educ 7.5%, idiomas 7.5%) |
| `gate.py` | Nuevo | Gate Fecha Y Relevancia → staging + curado |
| `ia_calibracion.py` | Nuevo | Pearson/Spearman/MAE gate vs IA + umbral sugerido |
| `cv_analysis.py` | Nuevo | Extractores regex + embeddings para CV → perfil Harvard/ATS |
| `cv2profile.py` | Nuevo | CLI: `cv2profile.py "cv.pdf" --save`; conv CV → profile dict JSON |

### FASE 3: Auth/Session/Browser Manager — **COMPLETADO**
| Tarea | Archivo(s) | Notas |
|-------|------------|-------|
| `browser_manager.py` | Nuevo/portado | Lanza Brave CDP, comparte cookies, host_resolver_rules |
| `credenciales.py` | **Nuevo/portado** | ✅ Almacén local (gitignored) + lista sitios login + auto-login fallback |
| `providers/login/auto_login.py` | **Nuevo/portado** | ✅ SSO Google (Indeed/LinkedIn), CAPTCHA/2FA detection, fallback manual |
| `providers/login/browser_sites.py` | **Nuevo/portado** | ✅ Cloudflare Turnstile + login-wall, modos DOM/API |

**Tests:** 127/127 pasan

### FASE 4: Dedupe Cross-Source + Bootstrap + Scheduler (Semana 4)
| Tarea | Archivo(s) | Notas |
|-------|------------|-------|
| Dedupe boards↔directos | `ingestion.py` o job post-ingest | Prioridad ATS empresa; marca `dup_of` sin borrar |
| `init-sources` command | `cli.py` | Registra plataformas + sitios CR por defecto |
| `recordatorio.py` | Portado | Login startup + recordatorio Windows (Task Scheduler) |
| `jobpulse-v15.cmd` | Nuevo | Launcher UI + corrida con un clic |

### OBJETIVOS O1–O10 (lista canónica) + O11–O14 (2026-11-05)

> Cada handoff de sesión lleva su copia de esta tabla con el estado al cierre.
>
> **Metas replanteadas el 2026-11-05** (ver `docs/PLAN_MEJORAS.md` para el
> detalle y el orden de ejecución). La prioridad real ya no es "más features"
> sino **que la UI dé los mismos números que la CLI** y **que la IA no esté
> atada a la máquina del usuario**:
>
> | Orden | Meta | Por qué |
> |---|---|---|
> | 1 | **O12** — paridad CLI/UI (una sola implementación del pipeline) | La UI deja 231 avisos `sin_requisitos` vs 11 de la CLI: el resultado que ve el usuario no es el real |
> | 2 | **O13** — recuperar fuentes (LinkedIn, Elempleo, login-wall de ANE) | Dos plataformas dan 0 avisos por DOM roto; ANE pierde la cookie de sesión |
> | 3 | **O11/O14** — IA externa y límites opt-in | Hecho: otro usuario sin GPU puede usar el enriquecimiento |
> | 4 | O5.3, O6.4, O8.2/O8.4, O9 | Calidad de datos y UI (-impacto medio) |
> | 5 | O4 (`superseded`), embeddings en viabilidad, upsert de análisis | Se pueden dejar de último (mucho esfuerzo, poco efecto inmediato) |

| Objetivo | Qué es | Estado |
|---|---|---|
| **O1** Enriquecimiento IA | Pase IA (Gemma local) llenando huecos: city/region/work_mode/employment_type/salary/skills/languages | ✅ **COMPLETO (27-10, 44 min; O7.3 E2E: servidor subió → pasó → se apagó solo)**. Resultado: skills 100%, date_published 100%, region 95.6%, employment_type 95.3%, languages 95.3%, city 91.9% (residuo = remotos / lat_raw de Indeed sin normalizar), work_mode 53.6% (137 'unknown': 46 basura O5.3 + 91 honestos sin mención), salary_raw 117 = fuente SIN texto salarial (irrecuperable). Los ciclos 2+ son replays de caché (ver gotcha: failed ≠ error) |
| **O2** Afinar la búsqueda | ~~ATS + gate + ranking semántico~~ **Redefinido por el usuario (2026-10-27): la precisión viene de la data extraída** → completar O1 (huecos). Alcance operativo: **O2.1** normalizar locations crudas de Indeed ("Heredia, Provincia de Heredia" → city/region); **O2.2** filtro UI "solo con requisitos obligatorios" + columna "Req." (aprobado por el usuario, estaba pospuesto) — **✅ COMPLETO (2026-11-04)**: definición única en `Repository.search_jobs` (`req_obligatorios` = requisitos `required` del análisis vigente) + filtro `solo_requisitos_obligatorios`; columna "Req." y casilla en UI clásica, UI v2 y CLI (`search --solo-requisitos-obligatorios`); motor semántico **DORMIDO por decisión** (nicho: texto libre ES↔EN) | 🟡 **O2.2 cerrado (04-11)** · el motor semántico sigue en pie solo como ranking ATS en la UI v2 (no es filtro) · `ats.py`/`gate.py`/`ia_calibracion.py` sin callers |
| **O3** Fetchers ATS huérfanos | Validar los 7 fetchers ATS (workday, greenhouse, ashby, lever, recruitee, workable, successfactors) con tableros reales · **y resolver la salud de los sitios**: 129 sitios cargados, 62 marcados `needs_review` (61 con 0 resultados en racha + 1 con error) sin resolver | ✅ **COMPLETO (2026-11-04)**: los 7 fetchers ya validados con tableros reales (7/7 plataformas activas) · la revisión manual se resolvió con `site mark-reviewed --all-needs-review` (nuevo flag; `mark_site_reviewed` reinicia el rache de ceros, `clean_run.py` reinicia la salud de los sitios) · BD real: 0 pendientes, 0 raches, 535 avisos intactos. Ojo: **el 0 no siempre es legítimo** (`workday-intel` devolvía 2 ofertas CR en vivo con 13 ceros acumulados) — los raches altos venían de corridas borradas por `clean_run`, que no reiniciaba la salud |
| **O4** Calibración gate-vs-IA | Pearson/Spearman/MAE + umbral sugerido (`ia_calibracion.py`) | ⏳ depende de O1+O2 |
| **O5** Higiene de datos | O5.1 ✅ auditoría/huecos · O5.3 re-barrido de los ~14-19 jobs con descripción basura (login-wall) · **O5.4 ✅ CERRADO (2026-10-27)**: análisis por **huella de descripción** (en ANE el título+empresa NO es identidad — "Confidencial"); solo 4/120 del lote 26-10 eran republicaciones → **las 4 viejas marcadas `dismissed` con nota** (parejas 121034/121185, 121026/121184, 121025/121183, 120958/121094), las nuevas quedan activas; grupos misma-empresa+misma-ciudad (INAMU ×3, SALESLAND ×2) = **plazas múltiples, decisión del usuario, intactos**; multi-sede (INAMU 8 ciudades, HIPERMASCOTAS 2 tiendas) = vacantes reales | 🟢 solo queda O5.3 |
| **O6** Perfil del candidato | O6.1 editor ✅ · O6.2 capa IA de CVs + integración UI ✅ · **O6.3 matching afinado (niveles/CEFR) ✅ CERRADO (2026-10-29)** — ver bloque "O6.3 — Matching (Paso 5)" más abajo · O6.4 dedupe semántico del perfil (slugs ES/EN del mismo hecho: normalizar al importar vs. decidir en diálogo — pendiente decisión del usuario) | 🟢 O6.1/O6.2/O6.3 cerrados · O6.4 pendiente decisión |
| **O7** Operación UI-first (servidores bajo demanda) | La app arranca/detiene lo que necesita; el usuario no toca CLI ni launchers | ✅ **completo (2026-10-27)** |
| **O8** Ciclo de vida de la vacante | Plan previo del usuario (recordado 2026-10-27; formalizado tras investigar el estado real del código). **O8.1 categorías de puestos ✅ PRIMERA VERSIÓN (2026-10-30)** — resuelto como **taxonomía de ÁREAS DE EMPLEO**: 20 áreas definidas por el SISTEMA en la BD (`area` + `area_regla`, migración `016_areas.sql`, semilla versionada `seeds/areas.json` con 51 reglas), clasificación por **TÍTULO** con reglas por **prioridad** (empate en la prioridad máxima → `otros`) y el perfil solo **marca/desmarca** (pestaña "Áreas de empleo" → `candidate_profile_facts.category='area'`). El borrador de categorías con IA (`tools/categorias_borrador.py`) deja de hacer falta: las categorías son **declarativas y versionadas**. El filtro en el MOTOR del Paso 5 (estado `fuera_de_area`) es de O10 (ver bloque "O8.1/O10 — Filtro por ÁREA de empleo") · **O8.2 recurrentes y aplicadas ocultas por defecto (decisión del usuario 27-10, refinada con ejemplo Concentrix)**: ⚠️ **ESTABA RESUELTO en v1.x (tombstones + `dup_of`, ver sub-diseño) y NO se portó**; hoy la republicación nace con ID nuevo y el estado manual del ID viejo NO se arrastra. Diseño aprobado: **matching por compañía + huella de descripción** (el título NO como criterio primario — O5.4 demostró falsos: 13 coincidencias solo-título NO eran republicaciones y grupos mismo-título eran plazas distintas). Al INGERIR una copia nueva que coincida (huella exacta o ratio ≥ ~0.92) con una ya marcada reviewed/applied → **la copia hereda el estado manual automáticamente** (nace oculta + nota de herencia con el ID origen; datos intactos — regla de repo actualizada 27-10: duplicado EXACTO = auto, patrón de v1.x; dudoso = manual). Margen incierto (ratio medio) → `quality duplicates` (dedupe conservador intacto). Opt-in en UI para mostrar repetidas/ya aplicadas; marcar aplicado = SIEMPRE manual. Y la ocultación NO es perpetua: **ventana temporal definida por el usuario en la pestaña de Configuración** (selector 1/2/3/6 meses, etc. — decisión del usuario 27-10; ancla = `updated_at` del estado del original): la copia solo hereda el estado (y queda oculta) si el estado del original tiene MENOS de la ventana; si el original ya la supera, la copia entra como vacante NUEVA (nuevo ciclo, re-aplicable). Default DECIDIDO por el usuario (27-10): **3 meses** (persistencia en `ui_config.json`, pestaña nueva "Vacantes" de Configuración; selector 1/2/3/6/12) · **O8.3 registro de aplicados** ✅ YA EXISTE: estado "Aplicada" en el diálogo de estado (excluye de búsqueda por defecto vía skip_automatic) + tabla `applications` (planned → applied → recruiter_contact → interview → offer, con applied_at + next_action_at + notas) + diálogo Seguimiento por vacante · **O8.4 de-baja automática por tiempo** ⚠️ **EXISTÍA en v1.x (`purge_expired`, ver sub-diseño) y NO se portó**: en v1.5 la búsqueda no filtra por edad ni vigencia (`expires_at` SOLO ANE lo llena; `gate.es_vigente` dormido sin callers) → portar como **OCULTAR, no borrar** (v1.x borraba filas): vencidas por `expires_at`, sin vencimiento → fuera de la ventana de publicación, sin fecha legible → TTL por `created_at`; ventana configurable en la MISMA pestaña "Vacantes" (decisión 27-10; default propuesto: 6 meses) | 🔵 diseñado 27-10 — implementación = portación de v1.x |
| **O9** Optimización de UI | Ajustes de interfaz pedidos por el usuario y siempre pospuestos — alcances por definir (después de O2-redefinido) | ⏳ placeholder |
| **O10** Mejorar filtros de búsqueda y compatibilidad | El paso 4 del flujo filtraba `matched` a ciegas → grilla vacía (0 jobs cuando 370/447 análisis son `partial`). `ui.elegir_filtro_compatibilidad()` usa `matched` si existe y si no muestra todos los vigentes, explicando por qué. **Filtro por ÁREA ✅ (2026-10-30)**: combo "Área" + casilla "Solo áreas de mi perfil" + columna "Área" en la UI principal, y filtro en el MOTOR del Paso 5 (estado `fuera_de_area`, motivo `fuera_de_area_del_perfil`; "evaluar todo" = `run_paso5.py --evaluar-todo`). Pendiente: refinar `solo_vigentes` (uso `date_published` vs `last_seen_at`), visibilidad opt-in de recurrentes/aplicadas (O8.2). La columna "Req." (O2.2) ya no está pendiente: **✅ 2026-11-04**. | 🟡 `elegir_filtro_compatibilidad` (28-10) + filtro por área (30-10) + columna/filtro "Req." (04-11) implementados |
| **O11** IA externa / motor intercambiable | Que el enriquecimiento (y las tareas futuras) funcionen con **cualquier** motor OpenAI-compatible, no solo con llama.cpp en esta máquina: Ollama **Cloud** (acceso gratis), Ollama local, LM Studio, OpenRouter, NVIDIA, Gemini o `custom`. Mismo cliente, mismo pase, sin código duplicado | ✅ **COMPLETO (2026-11-05)**: `ia_servidor.es_endpoint_local()` (con endpoint externo no se arranca nada local) · degradación `json_schema` → `json_object` → sin `response_format` ante el rechazo del proveedor (400/422) · `IA_MODEL=auto` autodetecta el modelo con `GET /models` · presets **unificados** (`ia_api.PRESETS` es la fuente única que ven las dos UIs) · aviso de privacidad + confirmación (UI) y `--confirmar-externo` (CLI) · preflight con mensaje según local/externo. **39 tests nuevos** (`tests/test_ia_externa.py`, incl. end-to-end por HTTP) |
| **O12** Paridad CLI/UI (una sola implementación del pipeline) | La UI debe dar **los mismos números** que la CLI. Hoy NO: la UI analysis **antes** de la IA y nunca re-analiza, así que los campos estructurados (`jobs.skills`/`languages`) nunca se convierten en requisitos → 231 avisos `sin_requisitos` (vs 11) y 32 calificadas de menos | 🟡 **OLAS 1 Y 2 COMPLETAS (2026-11-05)** · Ola 1: **1.1** re-análisis incremental (`analysis_flow.reananalizar_con_campos_fuente`, cableado en CLI/UI clásica/UI v2) · **1.2** badge + contador exacto (`cuenta_analisis_obsoletos` confirma en seco: 67 candidatos SQL = **0 obsoletos reales**) · **1.3** guarda `askyesnocancel` antes del Paso 5 · **1.4** evidencia como módulo (`jobpulse_v15.evidencia`, scripts = envoltorios, UI v2 con botón "Evidencia" e indicador "al día") · **1.5** login ANE con cierre ordenado (`Browser.close` por CDP) y `--mantener-abierto`. Ola 2: **2.1** orquestador `jobpulse_v15.pipeline` (una implementación por etapa; `run_full_flow.py` = envoltorio) · **2.2** botón "Procesar" (UI v2) · **2.3** botón "Enriquecer IA" (UI v2, con confirmación de privacidad) · **2.4** paso 3.5 en la UI clásica. **Medición sobre copia de la BD real: `sin_requisitos` 231 → 11 (−220)**; test de paridad UI/CLI sobre dos bases idénticas |
| **O13** Cobertura de fuentes (que el barrido traiga los avisos que existen) | **LinkedIn** daba 0 avisos (DOM nuevo: `/jobs/search-results/` con clases ofuscadas, sin `div.base-card` ni `/jobs/view/`) · **Elempleo** daba 0 avisos (falso muro de login del encabezado, empresa fuera de `datalayertag`, filtro de país mirando el cantón) · **ANE** perdía la cookie de sesión porque `login_ane.py` cerraba el Brave que abrió (**arreglado en O12 · 1.5**: cierre ordenado + `--mantener-abierto`; **y en O13**: la cookie es de sesión y Chromium no la persiste → se guarda aparte) · la salud de sitios no distingue "login-wall" de "selector roto" | 🟢 **OLA 3 COMPLETA (2026-11-06)**: LinkedIn reescrito (HTTP + `div.base-card` + JSON-LD, rate-limit 1,5 s) → **60 avisos**; Elempleo → **3 avisos**; `requires_login` (migración **022**, 🔑 en la UI v2, no cuenta en la racha de ceros); `jobpulse_v15.sesion_navegador` guarda/restaura la sesión de ANE en `data/usuario/sesiones/`; **verificado con dos barridos seguidos** (24 avisos cada uno) y con Brave cerrado y reabierto |
| **O14** Control del coste de la IA (límites opt-in, nunca fijos) | Que el usuario pueda poner y **quitar** límites: `IA_MAX_LLAMADAS` (llamadas por corrida), `IA_RPM` (requests por minuto) y `IA_MAX_VACANTES` (**avisos por corrida**). Vacío = sin tope. El tope de avisos **no puede ser un valor fijo**: subirlo o bajarlo según el presupuesto y la cuota | ✅ **COMPLETO (2026-11-05)**: los tres límites son opt‑in y ajustables desde `.env` **y** desde "Configuración → IA externa" en las dos UIs; el presupuesto por corrida se consume a lo largo de los ciclos (no se reinicia); `0` o un valor no numérico = sin tope (con aviso, no con crash) |

**O7 — sub-objetivos (implementados 2026-10-27, tras el barrido fallido desde la UI):**

- **O7.1 Fix `BraveManager`** ✅ — `--user-data-dir` a la **raíz** `User Data` + `--profile-directory={perfil}`; `stop_brave_sync()`, `cdp_vivo()`, `asegurar_brave()` (devuelve manager solo si él abrió) y `PLATAFORMAS_NAVEGADOR` en `browser_manager.py`. Corrige también el botón "Login manual" de Configuración y el CLI `login`.
- **O7.2 Brave auto-gestionado en el barrido** ✅ — al "Ejecutar barrido" con sitios de navegador, la UI verifica CDP y abre Brave si hace falta; al terminar lo cierra **solo si ella lo abrió** (en `finally`: sobrevive a errores de sitios); aviso claro si Brave diario impide abrir CDP.
- **O7.3 Servidor IA bajo demanda** ✅ — `jobpulse_v15.ia_servidor.py` (única fuente del comando: `asegurar_servidor()`/`ServidorIA.detener()`, solo apaga lo que él encendió); **botón "Enriquecer"** en la UI (orquesta `ia_enrichment.pase_completo`, compartida con `run_enriquecimiento.py`); pase IA de CV con servidor bajo demanda (`ui_perfil.py`); el launcher `.bat` ya NO pre-arranca la IA.
- **O7.4 Re-login ANE desde la UI** ✅ — botón "Re-login ANE" en el diálogo de Corrida; lógica en `jobpulse_v15.ane_login.py` (paquete); `login_ane.py` queda como wrapper CLI que abre/cierra Brave solo si hace falta.
- **Criterio de éxito** ✅ — abrir la app → "Ejecutar barrido" → "Enriquecer" → cerrar. Cero CLI, cero launcher obligatorio, cero `ECONNREFUSED 9222`.

**O6.3 — Matching de requisitos vs. perfil (Paso 5) — ✅ CERRADO 2026-10-29:**

Módulo real: **`src/jobpulse_v15/matching.py`** (no scripts ad-hoc). Herramientas de
verificación en la raíz: `run_paso5.py` (runner, `--dry` opcional),
`evidencia_descartadas.py` (evidencia literal), `resumen_bloqueo.py` (resumen del
bloqueo), `verificar_corridas.py` (trazabilidad). Evidencia completa versionada en
`docs/PASO5_EVIDENCIA_2026-10-29.md`.

- **Esquema**: migraciones `009`–`014` (concepto canónico + `job_match` + `corrida_id`
  + columnas de conteo) y **`015_job_match_valida.sql`** (columna `valida` + índices).
  `job_match` tiene PK `(job_id, corrida_id)`.
- **Regla de corridas**: cada cambio de regla escribe una **corrida nueva**; las
  anteriores quedan con `valida = 0`. Nunca se hace `UPDATE` in-place de una corrida
  emitida (los `UPDATE` in-place de la sesión 29-10 morning corrompieron la
  trazabilidad: por eso existen 7 corridas de 447 filas y solo la última es vigente).
- **Precedencia de estados**: `descartada` (bloqueante confirmado) >
  `revisar_a_mano` (universitario obligatorio NO confirmado) > `datos_insuficientes`
  (cobertura < 0.60) > `revisar_a_mano` (otros faltantes) > `calificada`
  (puntaje ≥ 0.80) > `baja_compatibilidad`. Umbrales **sin cambio** (0.60 / 0.80).
- **Bloqueante educativo (regla acordada con el usuario)**: `descartada` solo si el
  **texto completo** (`requirements_raw` + `description_raw`) confirma un título
  universitario **obligatorio**, **sin negación y sin alternativa**.
  En cualquier otro caso → `revisar_a_mano` con motivo `educacion_no_confirmada`.
  "bachiller" NO es universitario en CR (es secundaria); "licenciatura" sí;
  "bachillerato universitario" SÍ es universitario.
  Negación: 30 chars antes / 45 después. Alternativa: 40 antes / 110 después + la
  cláusula completa (viñeta/frase) y la cláusula siguiente.
- **La OBLIGATORIEDAD la decide el TEXTO, no solo `requirement_level`** (decisión del
  29-10 tras medir la muestra): la cláusula que exige el título ("Required
  Qualifications", "Minimum/Basic Qualifications", "must have", "degree or above",
  "Requisitos") bloquea aunque el extractor lo marque `ambiguous`/`inferred`; si el
  texto solo lo prefiere ("Preferred") NO bloquea. El encabezado de la sección de
  requisitos cuenta aunque vaya en su propia viñeta ("Qualifications\nBachelor's…").
- **Alcance por GRUPO de enumeración** (decisión 29-10 noche): la negación, el
  suavizador y la obligatoriedad se aplican al **grupo** de títulos unidos por
  "or"/"/"/"y", NO a la cláusula completa. Así "Bachelor's/University degree,
  Master's degree preferred" EXIGE el bachelor's (la coma corta el alcance del
  "preferred") mientras que "Bachelor's or Master's degree preferred" NO exige
  ninguno de los dos.
- **Negación DURA vs. SUAVIZADOR** (motivos distintos): "is preferred but not
  required" → `negacion` (manda la negación); un encabezado "Preferred
  Qualifications" → `suave` (nuevo valor de `motivo`).
- **Excepción "equivalente"**: "or equivalent field of study / discipline / degree"
  NO es una vía alternativa (sigue exigiendo un título universitario, cambia la
  carrera). "or advanced coursework / advanced university studies" SÍ es vía
  alternativa → no se descarta. "alternatively, N years of relevant professional
  experience" SÍ es vía alternativa (falso descarte corregido).
- **Estudiante activo** (`titulo_universitario_en_curso_requerido`): "currently
  pursuing", "must be enrolled", "students pursuing", "active university student"
  es un criterio DISTINTO del título completado; se cumple solo si el perfil registra
  un hecho educativo con `education_status='pursuing'`.
- **Semántica de la AUSENCIA de `education_status`** (decidida 29-10 noche, punto 3
  del bloqueante):
  - el perfil registra hechos educativos y NINGUNO dice `pursuing` → se sabe que la
    persona NO está registrada como estudiante activo → **"no cumple"** → la vacante
    se descarta con motivo `titulo_universitario_en_curso_requerido`;
  - el perfil NO registra NINGÚN hecho educativo (o ninguno con nivel) → la dimensión
    educativa **NO es verificable** → nunca se descarta por falta de información: la
    vacante va a `revisar_a_mano` con el motivo `educacion_no_verificable`.
- **Motivos** (`PRIORIDAD_MOTIVOS`): `titulo_universitario_en_curso_requerido` >
  `titulo_universitario_requerido` > `educacion_no_confirmada` >
  `educacion_no_verificable` > `educacion_no_cumple` > `skill_faltante` >
  `idioma_no_comparable` > `experiencia_no_verificable` > `licencia_no_comparable` >
  `cobertura_insuficiente`.
  `educacion_no_confirmada` = obligatorio que el texto NO confirma;
  `educacion_no_verificable` = el perfil no registra hechos educativos (no hay
  información para afirmar "no cumple");
  `educacion_no_cumple` = el perfil no alcanza el nivel pedido (requisito no
  obligatorio: no bloquea, se deja para revisión).
- **Corrida vigente `20261029_205348`** (447 vacantes): calificada 102 ·
  revisar_a_mano 94 (19 `educacion_no_confirmada` + 57 `educacion_no_cumple` +
  11 `skill_faltante` + 4 `experiencia_no_verificable` + 3 `licencia_no_comparable`) ·
  sin_requisitos 141 · **descartada 80**
  (56 `titulo_universitario_requerido` + 24 `titulo_universitario_en_curso_requerido`) ·
  datos_insuficientes 30. Las 6 corridas previas quedan `valida = 0`.
- **MEDICIÓN AMPLIADA del grupo `educacion_no_cumple` (43 casos, 29-10 noche)**:
  la muestra inicial (5/10) no cerraba el bloqueante. Se amplió a **43 casos**
  (estrato A = las 13 promovidas, todas; estrato B = 30 sistemáticas de las 93
  restantes) revisados **uno por uno** contra la frase literal del aviso:
  - estrato A: 12/13 eran bloqueos reales → **1 falso descarte** (A2
    `workday-Accounts-Payable-Representative_J-020440`: "… and 1+ year of relevant
    experience; alternatively, 3+ years of relevant professional experience") →
    corregido por la regla "alternativamente = vía alternativa";
  - estrato B: 14/30 eran bloqueos reales que el motor NO detectaba → promovidos;
  - proporción de bloqueos reales: **26/43 ≈ 60 %** (la muestra inicial daba 5/10 =
    50 %) → **la regla se sostiene, NO estaba sobreajustada**;
  - contra el ground truth manual la regla acierta **43/43** (26/26 promovidas +
    17/17 no promovidas).
  - evidencia: `docs/PASO5_EVIDENCIA_2026-10-29.md` §6 (tabla + frase literal de los
    43 casos) y §4/§5 (las 80 `descartada` y las 19 `educacion_no_confirmada`).
- **Verificación POR CONSULTA**: `verificar_evidencia.py` comprueba que cada
  `descartada` y cada `educacion_no_confirmada` de la corrida vigente aparece en el
  documento de evidencia **con frase literal** y que esa frase es substring literal
  de `jobs.requirements_raw` + `jobs.description_raw` (no un resumen). Resultado:
  **112 verificaciones, 0 fallos** (80 + 19 + las 13 promovidas de la corrida
  `183231`).
- **Revisión manual del bloqueante (HECHA, 29-10)**: las 20
  `revisar_a_mano / educacion_no_confirmada` se revisaron una por una con evidencia
  literal → **19 no bloqueantes** (alternativa o negación) y **1 bloqueo real**
  (`workday-Supplier-Quality-Engineer-III_31162905`: "Bachelor's degree in
  engineering, Science, or equivalent field of study") → corregido por la regla.
  Los 90 `educacion_no_cumple` restantes NO son bloqueos: el texto no obliga.
- **Falsos descartes corregidos** (10, todos con evidencia literal): negación
  ("No university degree required"), alternativas ("or its equivalent",
  "Associate's or bachelor's degree", "Bachelor's degree or certification",
  "equivalent practical experience may be considered", "or an equivalent
  combination…", "or other technical/scientific experience", "or advanced
  university studies", "alternatively, 3+ years of relevant professional
  experience"). Delta de la corrida `183231` → `205348`: 37 cambios (36 nuevas
  `descartada` + 1 salida: A2).
- **Tests**: `tests/test_matching.py` (65 casos, incluidos 19 regresiones con frases
  literales de la BD + la clase `TestSemanticaEducationStatus`) +
  `tests/test_database.py` (versión de esquema dinámica:
  fallaba con `8` fijo desde la migración 009). Suite completa: **358 tests verdes**.

**Pendiente del Paso 5**: las 19 `revisar_a_mano / educacion_no_confirmada`
quedan **ABIERTAS**: el veredicto previo era del autor de la regla (sesgo) y se
descarta; la revisión la firma una segunda persona con el texto completo
(`docs/PASO5_REVISION_PENDIENTES.md`, sin veredictos) y antes hay que decidir 3
reglas de negocio (advanced university studies / two year college / 80 % de la
carrera). Después: tabla `job_match_decision` + decisiones finales + UI + export
(Paso 7).

**O8.1 / O10 — Filtro por ÁREA de empleo (✅ 2026-10-30):**

Módulo real: **`src/jobpulse_v15/areas.py`** (tests: `tests/test_areas.py`). La
taxonomía la define el **sistema** y vive en la BD; el perfil solo marca/desmarca.

- **Esquema**: migración **`016_areas.sql`** (esquema v16) → tablas `area`,
  `area_regla`, `job_area`; reconstrucción de `candidate_profile_facts` (CHECK
  `category` + `'area'`) y de `job_match` (CHECK `estado` + `'fuera_de_area'`),
  copiando sus filas (48 facts / 3576 filas de `job_match`) y recreando 5
  índices. `check_integrity` → ok, 0 violaciones FK.
- **Taxonomía**: **20 áreas** (19 del sistema + `otros`) sembradas desde
  `src/jobpulse_v15/seeds/areas.json` (versionado) con **51 reglas**. Comandos:
  `init-areas [--classify]`, `areas list`, `areas classify [--dry-run]`.
- **Clasificación por TÍTULO**, la **MISMA para cualquier fuente** (Workday,
  ANE, Indeed, LinkedIn, Elempleo, Harvie, CINDE, Procomer). Gana la regla de
  mayor **prioridad**; si dos áreas empatan en la prioridad máxima el aviso es
  **ambiguo** → `otros`. La descripción NO clasifica (en miles de caracteres
  cualquier palabra aparece por casualidad): la pasada por descripción queda
  como informativa futura (confianza `descripcion`, nunca excluye).
- **Se clasifica al INGESTAR**: `Repository.save_job` clasifica cada vacante
  nueva (`job_area`), así un puesto nuevo de cualquier fuente queda clasificado
  solo; `areas classify` reclasifica todo en lote cuando cambian las reglas.
- **Perfil**: pestaña **"Áreas de empleo"** en `ui_perfil.py` → casillas por
  área (muestra el nº de vacantes) + botón "Guardar áreas"; lo marcado se
  guarda como hechos `candidate_profile_facts.category='area'`. **Sin áreas
  marcadas no hay filtro** (se evalúa todo).
- **En el MOTOR del Paso 5** (`matching.py`): la oferta de otra área queda con
  estado **`fuera_de_area`** (motivo `fuera_de_area_del_perfil`) y **NO se
  evalúan sus requisitos**; la corrida sigue escribiendo **una fila por
  vacante** (auditable). "Evaluar todo" = `run_paso5.py --evaluar-todo`.
- **Conservador por diseño**: `otros` (ambiguo o sin encaje) y las ofertas sin
  clasificar **SIEMPRE se evalúan** — una clasificación dudosa nunca oculta
  una oferta.
- **UI principal**: combo "Área" + casilla "Solo áreas de mi perfil" + columna
  "Área" en la tabla.
- **Medición real** (447 vacantes, `GROUP BY` sobre la BD): 447/447 clasificadas
  → informática 92 · producción 43 · ventas 42 · administración 38 ·
  **otros 34** (32 sin encaje + 2 ambiguos: "Payroll, Time & Benefits
  Specialist", "Recepcionista Hospital Curridabat") · alimentación 32 · servicio
  20 · logística 18 · automotriz 17 · ingeniería 16 · marketing 16 · salud 15 ·
  almacén 14 · calidad 12 · mantenimiento 12 · RR.HH. 10 · legal 7 · educación
  5 · seguridad 4 · construcción 0. **Sin áreas marcadas los resultados son
  IDÉNTICOS a la corrida vigente** (104 calificada / 90 revisar_a_mano / 82
  descartada / 30 datos_insuficientes / 141 sin_requisitos) → no hizo falta
  corrida nueva. Con "todo menos informática" se excluyen exactamente las 92;
  con solo "administración" se excluyen 375 (se evalúan 72).
- **Tests**: `tests/test_areas.py` (20 tests + 21 subtests, con títulos
  LITERALES de la BD real) + test de UI de marcar/desmarcar en
  `tests/test_ui.py`. Suite completa: **393 tests verdes**.

**O8 — sub-diseño (2026-10-27): PORTAR el mecanismo que v1.x ya tenía resuelto** (el usuario lo recordó y hizo revisar el código; hallazgo confirmado):

El ciclo de vida existía en el proyecto v1.x (`D:\Proyectos\jobpulse_cr`,
congelado — solo leerlo) y NO se portó a v1.5:

- `core/database.py → marcar_duplicados_exactos()`: marcaba `dup_of` con la
  `clave_duplicado_exacto(empresa|título|ubicación)` de `core/dedupe.py`
  (tokens normalizados/orden-insensible/ASCII; None si falta ubicación);
  canónico = provider directo más antiguo, SIN borrar filas, idempotente;
  las copias `dup_of` no gastaban cuota IA (main.py).
- `core/database.py → jobs_excluidas` (tombstones) + `core/exclusiones.py`:
  barrera de ingesta `filtrar_offers()` — un puesto excluido y borrado NO
  resucitaba cuando el board lo republicaba con job_id nuevo, porque el
  tombstone es por CLAVE empresa|título|ubicación, no por job_id.
- `core/database.py → purge_expired(dias=30)`: TTL de vigencia — vencidas
  por `expires_at` (ANE lo trae); sin vencimiento → `date_published` fuera
  de la ventana; sin fecha legible → TTL por `created_at`.

**Por qué v1.5 resucita republicaciones**: solo se portó
`source_job_memory` por `(site_id, source_job_id)` — idempotencia de
re-scrape del MISMO id, no barrera de republicación; ni `dup_of`, ni
tombstones, ni `purge_expired` existen en v1.5 (migración pendiente).

**Adaptaciones v1.5 (decisiones del usuario 27-10)** — portar el patrón,
no el código literal:

1. Además de la clave empresa|título|ubicación de v1.x → **huella de
   descripción** (ANE publican como "Confidencial": O5.4 demostró que es
   el criterio primario; título solo como pista).
2. La republicación coincide → **hereda el ESTADO manual** (reviewed/
   applied + skip_automatic + nota de herencia) en vez del modelo v1.x de
   exclusión permanente de contenido; y **oculta, no borra** (otra regla
   v1.5).
3. La ocultación respeta la **ventana de meses configurable en
   Configuración** (nueva decisión; v1.x no tenía ventana ni pestaña).
4. Coincidencia DUDOSA (ratio medio) → `quality duplicates` (nunca
   auto): regla conservadora intacta.
5. **Lo que v1.x NO tenía (el vacío señalado por el usuario)**: el triage
   MANUAL — marcar a mano revisado/aplicado. Eso YA está en v1.5
   (`user_job_state` + diálogo de estado + `applications` + Seguimiento):
   es la mitad nueva. O8 cierra el ciclo conectando ambas mitades: las
   piezas automáticas portadas alimentan los estados manuales que ya
   existe (la republicación hereda LO QUE EL USUARIO MARCÓ).

---

## 4. COMANDOS CLAVE PARA DESARROLLO

```powershell
# === ENTORNO ===
cd D:\Proyectos\v1_5
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\playwright install chromium  # para scrapers browser

# === BD ===
.\.venv\Scripts\python.exe -m jobpulse_v15 init-db
.\.venv\Scripts\python.exe -m jobpulse_v15 db check

# === FUENTES ===
# Bootstrap CR (12 plataformas + 5 sitios, idempotente):
.\.venv\Scripts\python.exe -m jobpulse_v15 init-sources

# Alta manual de plataformas/sitios NUEVOS (p. ej. otro tablero ATS):
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add --id ane --name "ANE/Brete" --provider-type browser --default-language es
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add --id cinde --name "CINDE Jobs" --provider-type api --default-language es
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add --id linkedin --name "LinkedIn" --provider-type browser --default-language es
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add --id indeed --name "Indeed CR" --provider-type browser --default-language es
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add --id procomer --name "Procomer" --provider-type api --default-language es
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add --id workday --name "Workday" --provider-type api --default-language en

# Sitios
.\.venv\Scripts\python.exe -m jobpulse_v15 site add --id ane-cr --platform ane --name "ANE Costa Rica" --url https://www.ane.cr --country CR --group boards
.\.venv\Scripts\python.exe -m jobpulse_v15 site add --id cinde-cr --platform cinde --name "CINDE Jobs" --url https://cindejobs.com --country CR --group boards
.\.venv\Scripts\python.exe -m jobpulse_v15 site add --id linkedin-cr --platform linkedin --name "LinkedIn CR" --url https://www.linkedin.com/jobs/search/ --country CR --group boards --config '{"search_text": "Soporte Técnico", "pages": 2}'
.\.venv\Scripts\python.exe -m jobpulse_v15 site add --id indeed-cr --platform indeed --name "Indeed CR" --url https://cr.indeed.com/jobs --country CR --group boards --config '{"search_text": "Soporte Técnico", "pages": 2}'
.\.venv\Scripts\python.exe -m jobpulse_v15 site add --id procomer-cr --platform procomer --name "Procomer CR" --url https://talento.procomer.com --country CR --group boards --config '{"search_text": "Soporte", "pages": 5}'

# === SCRAPING ===
# Brave DEBE estar corriendo con CDP en puerto 9222 para scrapers browser,
# con el PERFIL REAL: --user-data-dir apunta a la RAIZ "User Data", NUNCA a
# "User Data\Default" (crea perfil vacio y todos los logins "fallan"):
# brave.exe --remote-debugging-port=9222 --user-data-dir="C:\Users\<user>\AppData\Local\BraveSoftware\Brave-Browser\User Data"

# ANE (browser)
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape ane --site ane-cr --pages 15 --port 9222

# CINDE (API, sin browser)
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape cinde --site cinde-cr --pages 10

# LinkedIn (browser)
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape linkedin --site linkedin-cr --pages 2 --port 9222

# Indeed (browser)
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape indeed --site indeed-cr --pages 2 --port 9222

# Procomer (API)
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape procomer --site procomer-cr --pages 5

# Grupo completo
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape ane --group boards --pages 15 --port 9222

# === BÚSQUEDA ===
.\.venv\Scripts\python.exe -m jobpulse_v15 search --text "soporte técnico" --country CR --work-mode hybrid --format csv --limit 50

# === VIABILIDAD (ajuste técnico, NO probabilidad de contratar) ===
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list --limit 0
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad top --limit 20
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list --banda aplicar --format csv --output viab.csv

# === POSTULACIONES (estado del proceso, NO de aptitud) ===
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones correo --dias 90 --apply
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones workday --apply
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones list

# === CAPA B: código canónico del perfil ===
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich profile-canonico --apply

# === ALINEACIÓN: los campos estructurados del aviso también son requisitos ===
# Backfill del código canónico de los requisitos ya guardados (taxonomía 020/021).
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich requirements-canonico --apply
# Re-análisis que integra `jobs.skills` + `jobs.languages` (simula por omisión).
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich requirements-source
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich requirements-source --apply

# === UI ===
.\.venv\Scripts\python.exe -m jobpulse_v15.ui

# === TESTS ===
python -m pytest tests/ -q    # pytest vive en el python del sistema (el venv no lo trae)
```

---

## 5. PRÓXIMA ACCIÓN INMEDIATA

Pendientes vivos (handoff vigente `docs/HANDOFF_SESION_2026-11-06.md`; plan
completo en `docs/PLAN_MEJORAS.md`):

0. **Ola 4.1 — calidad del dato: APLICADA A LA BD REAL (2026-11-06, con OK
   del usuario)**: el parser de la ficha de ANE **descartaba campos** ("Nivel
   académico", "Experiencia laboral", "Estudio técnico") → el motor no podía
   evaluar esas dimensiones. Aplicado **solo a los 120 avisos ANE ya
   guardados** (respaldo `data/backups/pre_ola4_20261106_151857.db`): texto
   total de ANE 115.601 → **141.967 chars** (+23 %), **9 de 705** cambian de
   estado (7 → `descartada/titulo_universitario_requerido` con evidencia
   literal "Nivel académico: Licenciatura (Requerido)", 2 →
   `revisar_a_mano/educacion_no_cumple` porque el texto NO dice "Requerido"),
   **`educacion_no_confirmada` NO cambia** (31 → 31). Corrida vigente
   **`20261106_152304`** · evidencia OK (137 verificaciones) · `db check` ok.
   Lo que sigue: **4.2 (curación de la taxonomía) → APLICADA A LA BD REAL
   (2026-11-06)**: esquema 23, cola 1988 → **1225**, requisitos vigentes
   **2857 (0 sin código)**, corrida `20261106_182554`, evidencia OK,
   `educacion_no_confirmada` 31 → 31 (intacto) · **4.3 (métricas por etapa) →
   HECHO (2026-11-06)**: tabla `pipeline_etapa` (migración **024**, esquema 24),
   instrumentación en `pipeline.ejecutar` (punto único) + módulo
   `pipeline_metricas.py`, comando `… pipeline etapas [--limite N] [--corrida
   ID] [--json]` y línea de métricas en la UI v2 (medido sobre una copia de la
   BD real: paso5 705 avisos / 2866 requisitos evaluados) · los 24 avisos ANE
   nuevos (122031+) quedan para el barrido normal con IA.
1. **O12 — paridad CLI/UI** (meta #1): **Olas 1 y 2 YA ESTÁN** (2026-11-05:
   re-análisis incremental, badge, guarda, evidencia como módulo, login ANE
   con cierre ordenado y orquestador `pipeline.py` con los botones "Procesar"
   y "Enriquecer IA" en la UI v2; medición 231 → 11).
   El bloque de ALINEACIÓN **ya está aplicado en la BD real** (esquema 22,
   705 avisos, corrida `20261104_231932`): lo pendiente es que las UIs lo
   repitan, no volver a aplicarlo.
2. **O13 — cobertura de fuentes**: **OLA 3 COMPLETA (2026-11-06)**: LinkedIn
   reescrito (listado por HTTP + `div.base-card` + JSON-LD) → **60 avisos**;
   Elempleo (falso muro de login, empresa, filtro de país) → **3 avisos**;
   estado `requires_login` en la salud de sitios (migración **022**, 🔑 en la
   UI v2); y la **sesión de ANE entre arranques del navegador**
   (`jobpulse_v15.sesion_navegador` → `data/usuario/sesiones/ane.json`),
   verificada con **dos barridos seguidos** (24 avisos cada uno) y también
   con Brave cerrado y reabierto.
3. **El usuario marca sus áreas en la UI** (perfil → pestaña **"Áreas de
   empleo"**): hasta entonces el filtro está INACTIVO (sin áreas marcadas se
   evalúa todo, que es lo que hoy ocurre). Después, la próxima corrida del
   Paso 5 deja las ofertas de otras áreas con estado `fuera_de_area` (o
   `run_paso5.py --evaluar-todo` para evaluating todas).
4. **Capa B — extractor educativo** (aprobada por el usuario): migración
   **`017`** (filas `concepto`: master/MBA/associate/técnico superior) —
   **ESCRITA y APLICADA** el 2026-11-04 (esquema 19 en la BD real);
   `Repository.save_analysis` rellena `codigo_canonico` al guardar y
   `Repository.save_candidate_profile_facts` lo rellena para el perfil
   (**CAPA B resuelta y EFECTIVA**: resolver al guardar + backfill idempotente
   `enrich profile-canonico --apply` + fallback slug↔texto). El backfill en
   la BD real es un **no-op** (los hechos sin código son títulos de
   puesto) → no hace falta correrlo. **Pendiente**: re-analizar las vacantes
   para que los requisitos nuevos nazcan con código (→ punto 0).
5. **Paso 5 — las 31 `revisar_a_mano / educacion_no_confirmada` siguen ABIERTAS**:
   las firma una **segunda persona** en `docs/PASO5_REVISION_PENDIENTES.md`
   (el autoveredicto del autor de la regla se descarta por sesgo) → después,
   tabla `job_match_decision` + decisiones finales + UI + export (Paso 7).
   **No tocar los umbrales** (cobertura 0.60 / puntaje 0.80) sin acuerdo
   explícito.
6. **O8.2 ciclo de vida de la vacante**: recurrentes y aplicadas ocultas por
   defecto (opt-in para verlas); aplicado = manual; herencia por compañía +
   huella de descripción (exacta o ratio ≥ ~0.92; margen incierto → quality
   duplicates), con **ventana temporal configurable en Configuración**
   (1/2/3/6 meses…; fuera de la ventana la copia entra nueva).
6. **O5.3**: re-barrido de los jobs con descripción basura (login-wall) —
   hoy ~43 (35 de ANE); vía UI.
7. **O2-redefinido (afinar búsqueda)**: **O2.1** normalizar locations
   crudos de Indeed ("Heredia, Provincia de Heredia") — ✅ hecho;
   **O2.2** filtro "solo con requisitos obligatorios" + columna "Req." —
   **✅ cerrado el 2026-11-04** (UI clásica + UI v2 + CLI, definición única en
   `Repository.search_jobs`); motor semántico DORMIDO (vive como ranking ATS,
   que NO es un filtro).
8. Luego: **O6.4** (dedupe semántico del perfil: slugs ES/EN — decidir import
   vs diálogo) · **O9** (optimización de UI — alcances por definir) · **O4**
   (calibración — **redefinir o cerrar como *superseded***: sin gate semántico
   no tiene contra-qué comparar; el motor real es `matching.py`).
   ~~O3 (validar 7 fetchers ATS + resolver los sitios `needs_review`)~~ —
   **✅ cerrado el 2026-11-04**.

---

## 5. ARCHIVOS CLAVE PARA MODIFICAR

| Archivo | Qué tocar |
|---------|-----------|
| `ane.py` | `fetch(site, pages, search_text, skip_source_job_ids, port, dias)` → `AneOffers` |
| `cinde.py` | `fetch(site, pages, search_text, skip_source_job_ids)` → `CindeOffers` |
| `procomer.py` | `fetch(site, pages, search_text, skip_source_job_ids)` → `ProcomerOffers` |
| `linkedin.py` | `fetch(site, pages, search_text, skip_source_job_ids, port)` → `LinkedInOffers` |
| `indeed.py` | `fetch(site, pages, search_text, skip_source_job_ids, port)` → `IndeedOffers` |
| `cli.py` | Agregar subcomandos `scrape ane|cinde|procomer|linkedin|indeed` |
| `pyproject.toml` | Ya actualizado con deps: `httpx`, `playwright`, `beautifulsoup4`, `sentence-transformers`, `torch`, `python-dotenv`, `aiosqlite` |

---

## 6. NOTAS TÉCNICAS IMPORTANTES

1. **NO crear navegador en el fetcher**: el caller (CLI) pasa `port` CDP. El fetcher hace `p.chromium.connect_over_cdp(f"http://localhost:{port}")`.
2. **`site` dict viene del Repository**: incluye `site_config` (JSON), `db_path`, `base_url`, `company_name`, `country`, `run_groups`.
3. **`skip_source_job_ids`**: IDs que el usuario marcó para omitir manualmente (`skip_automatic=1`). El fetcher NO debe procesarlos.
4. **`jobs_skipped`**: Contador de ofertas omitidas por `skip_source_job_ids` (se pasa a `IngestionService` para health tracking).
5. **Campos `job` obligatorios** (ver `Repository.save_job`): `job_id`, `title`, `company`, `location_raw`, `country`, `city`, `region`, `work_mode`, `employment_type`, `date_published`, `expires_at`, `posting_language`, `posting_language_origin`, `description_raw`, `requirements_raw`, `salary_raw`, `sector` (opcional).
6. **Tests**: Cada fetcher nuevo debe tener test en `tests/test_<nombre>.py` (mock HTTP/Playwright, BD temporal).
7. **Modelo IA local: Gemma 4 E2B QAT (canónico desde 2026-10-25)**. A/B y pase real demostraron que es
   ~6.5x más rápido que Qwen 3.5 2B y llena mucho más (detalle completo en `docs/IA_ENRIQUECIMIENTO.md`):
   pase completo 175 jobs en 10.3 min (Qwen: ~67 min); skills 100%, languages 97.7%. Config viva en
   `.env` (`IA_MODEL=gemma4-e2b-qat`), `start_ia_server.py` (con `--metrics`) y `ia-server.bat`.
   ⚠️ Al probar/benchmarkar: la caché en disco (`data/usuario/ia_cache/`) responde instantáneo si el
   (job+modelo+prompt) ya se pidió — aislarla con `JOBPULSE_IA_CACHE` (así lo hace `tools/comparar_ia.py`).

---

## 7. DECISIONES DE DISEÑO TOMADAS

- **Ajuste técnico ≠ resultado del proceso** (decisión del usuario,
  2026-11-04): **ser rechazado NO significa que el perfil no califique** para
  el puesto (el reclutador decide por presupuesto, timing, competencia,
  sesgos y azar). Por eso el score de `viabilidad.py` (índice de ajuste
  técnico, determinista y auditable) **nunca** se entrena con los rechazos:
  los estados de postulación son señal operativa y contexto (no reprocesar lo
  postulado, medir el funnel propio, revisar posibles falsos positivos del
  ranking). El score NO es probabilidad de contratación y **no toca** los
  umbrales congelados del Paso 5.
- **Tope duro de banda**: si falta ≥1 requisito `required`, la banda máxima
  es `revisar` (nunca `aplicar`), aunque el score sea 100 — es el
  *knockout* explícito de los ATS modernos (HireVue/Paradox).
- **Puntaje comparable = dos pasadas con imputación del corpus**: pesos fijos
  + promedio del corpus para los componentes sin dato (misma regla que el
  ranking ATS). Sin esto, una vacante con un solo requisito cubierto sacaba
  100 y subía sola.
- **Postulaciones: del correo/portal solo se guardan derivados MÍNIMOS**
  (estado, fecha, remitente, asunto, referencia del aviso); **el cuerpo del
  mensaje nunca se guarda**.
- **La cola de conceptos del perfil solo recibe conceptos**: los hechos de
  `experience` del CV son títulos de puesto → quedan sin código y **no**
  ensucian `concepto_no_normalizado`.
- **No migrar datos legacy**: v1_5 empieza limpio; `data/jobpulse_v15.db` independiente.
- **No automerge dedupe**: v1_5 marca `dup_of` y deja review manual (evita pérdida de datos).
- **Config declarativa only**: No credenciales en `site_config`; credenciales en almacén local aparte (`credenciales.py`).
- **Scrapers browser reciben `port`**: Separación de responsabilidades (browser manager ≠ fetcher).
- **Health tracking por defecto**: 3 ceros = `review_required` (no desactiva solo).
- **Matching: el bloqueante educativo se CONFIRMA en el texto, no se infiere**
  (decisión del usuario, 2026-10-29): `descartada` exige evidencia literal de un
  título universitario obligatorio **sin negación y sin alternativa**; si el texto
  no lo confirma → `revisar_a_mano` (`educacion_no_confirmada`). Ante la duda,
  `revisar_a_mano` (no se descarta por heurística).
- **Matching: cada cambio de regla = una corrida nueva** en `job_match`
  (`corrida_id` + `valida`), nunca `UPDATE` in-place de una corrida emitida.
- **Matching: el alcance de negación/suavizador/obligatoriedad es el GRUPO de
  enumeración** (decisión del usuario, 2026-10-29 noche), no la cláusula completa:
  "Bachelor's/University degree, Master's degree preferred" EXIGE el bachelor's;
  "Bachelor's or Master's degree preferred" NO exige ninguno.
- **Matching: "bachillerato universitario" SÍ es título universitario** en CR
  ("bachiller/bachillerato" a secas = secundaria, no bloquea).
- **Matching: la ausencia de `education_status='pursuing'` significa "no cumple"**
  si el perfil tiene hechos educativos; si el perfil NO tiene NINGÚN hecho
  educativo, la dimensión NO es verificable → `revisar_a_mano` con
  `educacion_no_verificable` (nunca descartar por falta de información).
- **Paso 7: las decisiones manuales NUNCA se aplican in-place sobre `job_match`**
  (decisión del usuario, 2026-10-29): revisar cada vacante con su frase literal
  en el **texto completo** y **sin conclusiones previas**, decidir (queda en
  `revisar_a_mano` o es bloqueo real) y **registrar** la decisión en una tabla
  nueva (p. ej. `job_match_decision`, con migración numerada) que el
  Paso 7 lea; si el registro cambia los estados, se escribe con **corrida nueva**
  (`valida=1`), nunca `UPDATE` sobre una corrida emitida.
  **La revisión la firma una SEGUNDA persona** (no el autor de la regla): la
  revisión previa de las 19 la hizo el autor y su veredicto ("ninguna bloquea")
  quedó descartado por sesgo. Hoja de revisión (texto completo, sin veredictos):
  `docs/PASO5_REVISION_PENDIENTES.md` (por `generar_revision_pendientes.py`).
  **3 decisiones de negocio pendientes con fuente**: "advanced university
  studies" / "two year college degree (técnico superior universitario)" / "80 %
  de la carrera" — se decidieron como universitario o no ANTES de firmar los
  veredictos.
- **Áreas de empleo: la taxonomía la define el SISTEMA y vive en la BD**
  (decisión del usuario, 2026-10-30): `area` + `area_regla` sembradas desde
  `seeds/areas.json` (versionado); el perfil solo **marca o desmarca** (hechos
  `candidate_profile_facts.category='area'`). Nada del perfil hardcodeado.
- **Áreas de empleo: la clasificación es por TÍTULO y la MISMA para cualquier
  fuente** (decisión del usuario): Workday, ANE, Indeed, LinkedIn, Elempleo,
  Harvie, CINDE y Procomer usan las mismas reglas. Gana la regla de mayor
  **prioridad**; si dos áreas empatan en la prioridad máxima el aviso es
  **ambiguo** → `otros`. La descripción NO clasifica (en miles de caracteres
  cualquier palabra aparece por casualidad): su pasada queda como informativa
  futura (confianza `descripcion`, nunca excluye).
- **Áreas de empleo: el filtro va en el MOTOR del Paso 5** (decisión del
  usuario): estado `fuera_de_area` (motivo `fuera_de_area_del_perfil`), **sin
  evaluar requisitos**, pero la corrida conserva **una fila por vacante**
  (la exclusión es auditable). "Evaluar todo" = `run_paso5.py --evaluar-todo`.
- **Áreas de empleo: filtro CONSERVADOR por diseño**: sin áreas marcadas en el
  perfil NO hay filtro (se evalúa todo); `otros` (ambiguo o sin encaje) y las
  ofertas sin clasificar **SIEMPRE se evalúan** — una clasificación dudosa
  nunca oculta una oferta.

---

*Última actualización: 2026-11-04 tarde (bloque de ALINEACIÓN: los campos estructurados del aviso — `jobs.skills` / `jobs.languages` — son requisitos comparables; migraciones 020/021 + `skills_fuente.py` + CLI `enrich requirements-source`; suite 922 tests + 241 subtests)*
*Próxima revisión: tras aplicar 020/021 + re-análisis en la BD real (pide confirmación) y el cierre de la Capa B (extractor educativo)*

---

## 8. HISTORIAL DE CAMBIOS RECIENTES

### 2026-11-06 — OLA 4.3: MÉTRICAS POR ETAPA DEL PIPELINE (`pipeline_etapa`)

**Qué**: las siete etapas del pipeline devuelven contadores **propios y en
formatos distintos** (`analizados`, `jobs_found`, `ciclos`, `candidatos`,
`actualizados`, `por_estado`, `verificaciones`…). Acabada la corrida solo
quedaba el estado final, así que no se podía responder a la pregunta que
importa: **de todos los avisos que entraron, ¿cuántos llegaron al Paso 5,
cuántos tenían requisitos y en qué etapa se perdieron?** (Caso real de la Ola
4.2: 705 avisos entraron al análisis, 9 acabaron en `sin_requisitos` y 58
cambiaron de estado por requisitos sin `codigo_canonico`.)

1. **Tabla `pipeline_etapa`** (migración **024**, esquema 23 → **24**): una
   fila por **etapa y por ejecución** del pipeline. Columnas: `corrida_id`
   (`pipe_<timestamp>`, **distinto** del `corrida_id` de `job_match`),
   `etapa`, `ok`, `duracion_ms`, `avisos`, `requisitos`, `errores`,
   `detalle_json`, `iniciado_en`, `terminado_en`. Índices por
   `(corrida_id, id)` y `(etapa, id)`. **Sin claves foráneas** (el
   `corrida_id` del pipeline es un id **lógico**).
2. **Módulo `jobpulse_v15.pipeline_metricas`**: traduce el resultado de cada
   etapa a tres números **comparables** (`avisos` / `requisitos` / `errores`) y
   guarda los contadores **específicos** de la etapa en `detalle_json` (por
   estado y motivo del Paso 5, por campo rellenado por la IA, por sitio del
   barrido…).
3. **Instrumentación en el orquestador** (`pipeline.ejecutar`): es el **único**
   punto donde se cronometran las etapas → CLI, UI v2 y `run_full_flow.py`
   dejan la misma métrica. Es **puramente aditiva**: si falla, la corrida
   **sigue** (una métrica nunca rompe un pipeline).
4. **Contadores que faltaban**: `analisis.requisitos_guardados`,
   `paso5.requisitos_evaluados` (suma de `Resultado.total_req`),
   `reanalisis.texto_errores` y `evidencia.documentados` (los avisos de la
   corrida, comparables con los del Paso 5).
5. **Consulta**: `… -m jobpulse_v15 pipeline etapas [--limite N] [--corrida ID]
   [--json]` + una línea "MÉTRICAS" en la UI v2 (la UI clásica queda intacta).

**Medición (copia de la BD real, `%TEMP%\opencode\ola43_copia.db`)**: paso5
**705 avisos / 2866 requisitos evaluados**, evidencia 705 avisos con **137
verificaciones literales** (`no_confirmada=31`, intacto), 0 errores; tiempo
total de la corrida ≈ 3,4 s. La migración 024 se aplicó sola al abrir la
copia (convención del proyecto: el esquema se migra al abrir la BD).

**Pendiente**: ~~aplicar la 024 a la **BD real**~~ → **APLICADA (2026-11-06,
con OK del usuario)**: **solo la migración** (respaldo
`data/backups/pre_ola43_20261106_210124.db`, esquema 23 → **24**, `db check`
ok: `integrity ok`, 0 violaciones de FK); **nada del matching cambió** (705
avisos, 706 conceptos, cola 1225, 825 `job_analysis`, 0 requisitos sin
código, 2669 filas de `job_match`, corrida vigente **`20261106_182554`**,
`educacion_no_confirmada` **31 intacto**). `pipeline_etapa` queda vacía hasta
la próxima corrida real del pipeline.

### 2026-11-06 — OLA 4.2: CURACIÓN DE LA TAXONOMÍA (`concepto_no_normalizado`)

**Qué**: la cola `concepto_no_normalizado` es la lista de trabajo de la
taxonomía (variante de texto → código canónico). Al medirla sobre una copia
de la BD real resultó **obsoleta**: 1988 filas de las que 10 ya resolvían y
1976 no. De las **3397 skills** distintas de `jobs.skills` solo **241**
resolvían a un concepto (el 17 %): el resto eran **actividades** ("despachar",
"empacar"), **palabras vacías** ("analysis", "planning") o **sectores**
("construccion", "ventas") — el criterio que la propia migración 021 aplicó a
mano, pero que nadie automatizó.

1. **Filtro antes de encolar** (`conceptos.es_variante_encolable`): descarta
   actividad, palabra vacía, sector y frases de más de tres palabras. Vive en
   `encolar_sin_concepto`, el **único punto de entrada** de la cola → aplica a
   todos los orígenes. Es **conservador**: lo que no cae en las reglas se queda
   en la cola; nunca se descarta en silencio.
2. **Curación por tandas** (datos, no código): migración **023**
   (`023_taxonomia_curacion_tanda_1.sql`) con **alias** de conceptos que ya
   existían ("office 365 basico" → Office 365, "mantenimiento correctivo" →
   mantenimiento) y **conceptos nuevos** para lo que el corpus pide y no
   existía (Mulesoft, PowerShell, MFA, SAML, ISO 9001/19011, lectura de planos,
   metrología, cableado estructurado, fontanería, electricidad, PCAOB, ICFR,
   COSO, asientos contables…).
3. **Herramienta de curación** (`jobpulse-v15 taxonomy curate [--apply]`):
   audita el corpus (resuelto / ruido / pendiente) y, con `--apply`,
   reconstruye la cola desde `jobs.skills`/`jobs.languages`: borra lo ya
   resuelto y lo que es ruido, y reescribe `veces` con el nº de **avisos** que
   piden cada variante (antes contaba encolados).

**Medición (copia de la BD real, `%TEMP%\opencode\ola42_full.db`)**: las
etiquetas que resuelven suben de 241 a **560** (877 → 2064 menciones), la cola
baja de 1988 a **1225** filas (las pendientes reales), los requisitos
vigentes suben de 2483 (1 sin código) a **2857 (0 sin código)** y los
requisitos medios por aviso de 3,53 a **4,07** (232 avisos con más, 0 con
menos). **58 avisos cambian de estado** (47 `calificada → revisar_a_mano`):
los avisos ANE se evaluaban con **un solo requisito** (el idioma) y ahora
también con las skills que realmente piden ("inventario", "fontanería",
"electricidad", ISO 19011, PCAOB, ICFR, SEC SOX, COSO) → el perfil no las
tiene → `revisar_a_mano/skill_faltante`. Antes esos requisitos eran
**invisibles** (sin `codigo_canonico` el motor los ignora en silencio) y las
vacantes parecían más compatibles de lo que son. Bandas: `aplicar` 270 → **217**,
`no_prioritario` 323 → **376**, `veto` 96 → 96 (sin cambios),
`educacion_no_confirmada` 31 → **31 (intacto)**.

**Pendiente**: una **segunda tanda** de curación (la cola tiene 1225
pendientes; la siguiente cubre las variantes con `veces >= 2`).

**APLICADO A LA BD REAL (2026-11-06, con OK del usuario)**: respaldo
`data/backups/pre_ola42_20261106_182411.db` (`integrity ok`, esquema 22, 705
avisos) → apertura (aplica la **023**, esquema 23) → `taxonomy curate --apply`
(cola 1988 → **1225**) → re-análisis de los **705** avisos (la etapa
`reanalisis` del pipeline solo rehace los que nunca integraron `jobs.skills`)
→ requisitos vigentes 2483 (1 sin código) → **2857 (0 sin código)** → backfill
(0) → **corrida `20261106_182554`** → evidencia OK (137 verificaciones
literales, `no_confirmada=31`) → `db check` ok (`integrity ok`, 0 violaciones
de FK). El resultado real fue **idéntico al medido en la copia**: 58 avisos
cambian de estado, requisitos medios 3,53 → **4,07**, `educacion_no_confirmada`
31 → **31 (intacto)**.

### 2026-11-06 — OLA 4.1: CALIDAD DEL DATO (parser de ANE + re-barrido de detalle + re-análisis por texto nuevo)

**Qué**: el plan pedía "re-barrido de detalle" para 43 descripciones cortas.
Al medirlo, el problema real era otro: **el parser de la ficha de ANE
descartaba campos** ("Nivel académico", "Experiencia laboral", "Estudio
técnico"), o sea justo **lo que la empresa PIDE**. El corpus, en cambio,
ya coincidía con la fuente (descripción corta ≠ texto perdido: el texto
estaba en `requirements_raw`).

1. **Parser ampliado** (`ane.py`): lee los campos que se perdían; un valor
   **negado** ("No se especifica estudios técnicos") NO se copia; el **correo
   del empleador NO se guarda**; `Ocupación`/`Horario`/`Tipo contratación` van
   como contexto del aviso, no como requisitos.
2. **Re-barrido de detalle** (`scrape ane --site ane-cr --revisitar`): vuelve
   a bajar el detalle de los avisos **ya guardados** (por su URL). Hace falta
   porque el listado de ANE solo muestra lo nuevo: un aviso viejo guardado con
   un parser viejo nunca vuelve a pasar por el listado. Lo que ya no existe en
   la web se **omite** (no se borra nada). La oferta se construye con
   `AneFetcher._oferta` (**una sola implementación** para barrido y
   re-barrido).
3. **Re-análisis por texto nuevo** (`analysis_flow.avisos_con_texto_cambiado`
   / `reananalizar_texto_cambiado`): si el `text_hash` del análisis vigente no
   cuadra con el texto del aviso, el aviso está obsoleto → se re-analiza
   (enganchado en la etapa `reanalisis` de `pipeline.py`).

**Medición (copia de la BD real, `%TEMP%\opencode\ola4.db`)**: 120 avisos ANE
con **más texto** (+24 nuevos = 729), **9 de 705 cambian de estado**, y
**`educacion_no_confirmada` no cambia** (31 → 31). De los 9: 7 pasan a
`descartada` con evidencia literal **"Nivel académico: Licenciatura
(Requerido)"** y 2 pasan a `revisar_a_mano` porque el texto dice solo
"Nivel académico: Licenciatura" (sin "Requerido" → ante la duda, revisar).

**Pendiente**: los 24 avisos ANE nuevos (122031+) que aparecieron al medir
quedan para el barrido normal (con pase de IA): `scrape ane --site ane-cr` →
`analysis extract-pending` → `run_enriquecimiento.py` → re-análisis → backfill
→ `run_paso5.py`.

**APLICADO A LA BD REAL (2026-11-06, con OK del usuario)**: solo los 120
avisos ANE ya guardados. Respaldo
`data/backups/pre_ola4_20261106_151857.db` → re-barrido (120 revisados, 0
omitidos) → re-análisis (120) → backfill (0) → **corrida `20261106_152304`** →
evidencia OK (137 verificaciones, 0 fallos) → `db check` ok. Texto total de
ANE 115.601 → **141.967 chars** (+23 %) · **9 de 705** cambian de estado ·
`educacion_no_confirmada` **31 → 31** · hoja de firma regenerada (31 casos).

### 2026-11-06 — OLA 3 DE O13: COBERTURA DE FUENTES (LinkedIn, Elempleo, `requires_login`, sesión de ANE)

**Qué**: cuatro cosas, todas medidas **en vivo** (no en teoría):

1. **LinkedIn** (`linkedin.py`, reescrito): el listado público que funciona es
   `https://www.linkedin.com/jobs/search/?keywords=…&location=…` por **HTTP
   simple** (`/jobs/search-results/` responde 999 y el navegador sin sesión
   recibe authwall). Las tarjetas son `div.base-card` +
   `data-entity-urn="urn:li:jobPosting:<id>"`; el JSON-LD `ItemList` es el
   respaldo y el navegador (CDP) el refuerzo que fusiona resultados.
   **60 avisos** (antes 0). Rate-limit medido: `jobs-guest` aguanta ~10
   peticiones seguidas y luego da 429 → `request_delay` = **1,5 s** (19 OK /
   0 429 medidos) y reintento con espera ante 429.
2. **Elempleo** (`elempleo.py`): `.ee_list-item` es el **menú lateral**, no el
   listado (las ofertas siguen en `.result-item` + `.js-area-bind.area-bind`);
   el botón "Inicia sesión" del encabezado **no** es un muro de login (solo un
   formulario de acceso lo es); la empresa está en `.js-offer-company`; y el
   filtro de país mira país + cantón (la ubicación es el cantón). **3 avisos**
   (antes 0). `site_config["max_ofertas"]` acota el barrido.
3. **`requires_login`** (migración **022**): un sitio que pide iniciar sesión
   no está roto. Salud `requiere_login`, corrida `requires_login`, **no** suma
   a la racha de ceros, sí queda `review_required=1`, la UI v2 muestra 🔑 y el
   barrido lista los sitios que piden login.
4. **Sesión de ANE entre arranques** (`jobpulse_v15.sesion_navegador`): la
   cookie `ASP.NET_SessionId` es de **sesión** (`expires = -1`) y Chromium no
   la escribe en disco → al reabrir Brave se perdía (el cierre ordenado de
   O12 · 1.5 no la salva). Ahora el login guarda las cookies del sitio en
   `data/usuario/sesiones/ane.json` (fuera del repo) y el scraper las restaura
   cuando falta la sesión; si el servidor la caducó, el archivo se borra.

**Criterio de aceptación**: ANE con **dos barridos seguidos** → 24 avisos y
24 avisos (0 nuevos, 24 duplicados) y salud `healthy`; con Brave **cerrado y
reabierto** → 24 avisos restaurando la sesión (antes `requires_login`, 0).
LinkedIn 60 avisos · Elempleo 3 avisos. Tests nuevos: `test_linkedin.py` (16),
`test_elempleo.py` (10), `test_requiere_login.py` (8),
`test_sesion_navegador.py` (18) + 2 en `test_ane_login.py` + 2 de UI v2.

**Nota de esquema**: la 022 **recrea** `source_sites` y `source_run_sites`
(SQLite no deja cambiar un `CHECK` con `ALTER` y `PRAGMA foreign_keys` no se
puede cambiar dentro de una transacción) → `db.py` reconoce el marcador
`-- jobpulse:transaccion-propia` y deja que la migración gestione su propia
transacción. Probada sobre una **copia** de la BD real: 129 sitios, 705 avisos
y 134 corridas intactos, `integrity_check ok`, 0 violaciones de FK.

### 2026-11-05 — OLA 2 DE O12: ORQUESTADOR ÚNICO (`pipeline.py`) + BOTONES EN UI v2

**Qué**: `src/jobpulse_v15/pipeline.py` encadena las etapas con una sola
implementación cada una (`scrape` → `analisis` → `ia` → `reanalisis` →
`backfill` → `paso5` → `evidencia`). `run_full_flow.py` deja de tener su
propia lógica y pasa a ser un **envoltorio** del orquestador; la UI v2 suma
los botones **"Procesar"** (pipeline completo sin raspar) y **"Enriquecer IA"**
(pase IA + re-análisis), con log, progreso, cancelación y confirmación de
privacidad si la IA es externa.

**Criterio de aceptación (2.1)**: el camino UI (orquestador) y el camino CLI
(etapas sueltas) dan el **mismo estado de `job_match`** sobre dos bases
idénticas — test en `tests/test_pipeline.py` (15 tests) + 3 de UI v2.

**Nota**: la UI clásica conserva su flujo (regla del repo: no se toca sin
pedirlo), aunque usa las mismas implementaciones por etapa (incluido el
re-análisis del paso 3.5). Migrarla al orquestador queda como sugerencia 5 de
`docs/FLUJO_CLI_VS_UI.md`.

### 2026-11-05 — OLA 1 DE O12: PARIDAD CLI/UI (re-análisis, evidencia, ANE)

**Pedido del usuario**: cerrar la divergencia CLI/UI (`docs/PLAN_MEJORAS.md`,
Ola 1). Medición sobre copia de la BD real: la UI dejaba **231** avisos
`sin_requisitos` frente a **11** de la CLI.

**Causa**: el análisis se hace ANTES del pase IA, así que `jobs.skills` /
`jobs.languages` (que produce la IA) nunca se convertían en requisitos. La CLI
lo resolvía con `enrich requirements-source --apply`; las UIs no tenían ese
paso.

**Implementado** (detalle en `docs/HANDOFF_SESION_2026-11-05.md` §8):
- **1.1** `analysis_flow.reananalizar_con_campos_fuente()` (solo candidatos,
  calcula en seco y **guarda solo si cambia**; idempotente) cableado en CLI,
  UI clásica y UI v2.
- **1.2** `cuenta_analisis_obsoletos()` **exacto** (confirma en seco: la SQL
  sola sobrecontaba 67 → 0 reales) + badge en ambas UIs + `tools/estado_bd.py`.
- **1.3** guarda `askyesnocancel` antes del Paso 5 en UI v2.
- **1.4** `jobpulse_v15.evidencia` (generar/verificar/estado); los scripts
  quedan como **envoltorios** (documento generado idéntico, `exit 0`); UI v2
  con botón "Evidencia" e indicador "al día" sin subprocess.
- **1.5** `cerrar_brave_ordenado()` (`Browser.close` por CDP) + `login_ane.py
  --mantener-abierto`: la cookie de ANE ya no se pierde al cerrar.

**Medición final**: 231 → **11** `sin_requisitos` (−220) sobre la copia.
**Suite**: 1003 passed + 241 subtests. `verificar_evidencia.py` exit 0
(130 verificaciones). **Sin cambios en la BD real.**

### 2026-11-05 — IA EXTERNA (Ollama/LM Studio/cloud) + METAS REPLANTEADAS (O11–O14)

**Pedido del usuario**: "que se pueda usar la IA externa para el análisis y,
si no está, poner la opción para implementarlo… que se pueda usar para el
enriquecimiento y para otras tareas que veremos más adelante, porque ello
pueden dar acceso gratis a servidores en la nube".

**Diagnóstico**: el cliente (`ia_api.py`) y las dos UIs **ya** permitían
configurar un proveedor externo; lo que estaba roto era el **camino de
ejecución**:
1. `ia_servidor.asegurar_servidor()` arrancaba llama-server y lanzaba
   `RuntimeError("Servidor EXTERNO ... no responde")` (buscaba `/health`,
   que las APIs externas no tienen) → el pase moría antes de empezar;
2. `chat_json` forzaba `response_format: json_schema` estricto → 400 en
   Gemini / LM Studio / Ollama (no lo soportan);
3. `IA_MODEL=auto` enviaba `model: ""` (no había autodetección);
4. ningún aviso de privacidad: el texto de los avisos salía de la máquina
   sin que nadie lo dijera;
5. los presets estaban **duplicados y divergentes** entre el cliente y la UI
   ("ollama" = cloud en uno, local en el otro).

**Implementado**:
- `ia_servidor.es_endpoint_local()` (host real, no búsqueda de texto) +
  `asegurar_servidor()` devuelve `None` con endpoint externo (no arranca ni
  detiene nada local);
- `chat_json` degrada el modo de respuesta solo ante el rechazo del
  proveedor (400/422): `json_schema` → `json_object` → sin `response_format`.
  Un 429/404 **no** degrada (son errores reales, no de formato);
- `IAClient._resolver_modelo()`: `auto` → `GET /models` (con error explícito
  si el endpoint no expone modelos);
- presets **unificados** en `ia_api.PRESETS` (fuente única que ven las dos
  UIs): `ollama`=**Ollama Cloud**, `ollama-local`, `lmstudio`, `openrouter`,
  `nvidia`, `google`, `custom`;
- **aviso de privacidad + confirmación**: UI (botón "Enriquecer" y "Flujo
  completo") y CLI (`--confirmar-externo`); el pase deja el aviso en el log;
- **O14 — límites opt-in y ajustables**: `IA_MAX_LLAMADAS`, `IA_RPM` y
  `IA_MAX_VACANTES` (avisos por corrida). Vacío = **sin tope**; `0` o un
  valor no numérico = sin tope (con aviso, no con crash). El tope de avisos
  se edita en "Configuración → IA externa" (las dos UIs) o en el `.env`;
- `pase_completo` acepta `max_vacantes`/`db_path` (testabilidad y CLI).

**Metas replanteadas** (tabla O1–O14): la prioridad ya no es "más features"
sino **O12 (paridad CLI/UI)** y **O13 (cobertura de fuentes)**; O11/O14
quedan hechos; O4 se propone cerrar como *superseded*. Plan de 5 olas con
criterio de aceptación en `docs/PLAN_MEJORAS.md`.

**Suite**: **961 passed + 241 subtests** (base 922 → +39 tests nuevos en
`tests/test_ia_externa.py`, con un end-to-end contra un proveedor
OpenAI-compatible real por HTTP).

### 2026-11-04 (tarde) — ALINEACIÓN: los campos estructurados del aviso también son requisitos

**Objetivo que ordena el bloque**: encontrar, entre **TODOS** los puestos, los
que tienen los requisitos más compatibles con la persona del CV. Para
comparar un requisito del aviso con un hecho del perfil, los dos tienen que
hablar el mismo idioma: la tabla `concepto` (variante → `codigo_canonico`).
El motor **solo compara los requisitos con código**: los demás se ignoran
**en silencio**.

**Diagnóstico (corpus real, 535 avisos)**:
- 135 avisos estaban en la banda `sin_datos` del motor (sin NINGÚN requisito
  comparable) y **133 de esos 135 sí tenían `jobs.skills`** informado;
- con la taxonomía de la 020 solo resolvían **45 de 2438** menciones de skills
  de la fuente (el 98% no era comparable con el perfil);
- 511/535 avisos tienen `jobs.languages` (el idioma que **piden**, con nivel
  CEFR explícito) — dato que el sistema no leía.

**1. Módulo nuevo `skills_fuente.py`** (tests `tests/test_skills_fuente.py`, 24):
convierte los campos estructurados del aviso en requisitos comparables, con
cinco reglas duras: (1) solo lo que resuelve a concepto canónico (lo demás va
a la cola `concepto_no_normalizado`); (2) las **frases de tarea** no son
competencias (`ats.es_frase_de_tarea`); (3) el nivel es `inferred` (el campo
dice QUÉ pide, no si es obligatorio); (4) evidencia literal; (5) no se
duplica lo que el texto ya dio.

**2. `analysis_flow.py`** pasa a ser la implementación **única** del análisis
(la usan la CLI, la UI clásica, la UI v2 y `run_full_flow`): integra texto +
campos estructurados, con `VERSION_ANALISIS = "rules-2+fuente"` (las
revisiones viejas quedan como historial).

**3. Bugs corregidos (fallos silenciosos de alineación)**:
- **niveles de idioma**: la escala tenía las claves en MAYÚSCULAS ("B2") y
  los requisitos traen el nivel en minúsculas ("b2") → la comparación caía
  siempre en `no_verificable`. Ahora `idiomas.normalizar_nivel` ("B2+",
  "C1-C2", "fluent", "intermedio", "nativo") + `orden_nivel`;
- **`conceptos.resolver`**: usaba solo `value_code`; las licencias sin clase
  ("Driver's license") perdían el código → se añade el fallback a
  `value_text`.

**4. Taxonomía (migraciones `020` y `021`)**: `020` = conceptos de alineación
(java, tableau, six_sigma, c++, c#, typescript, autocad, solidworks + clases
de licencia de CR) + `Repository.backfill_requirements_canonico()` + CLI
`enrich requirements-canonico`. `021` = idiomas que faltaban + alias +
~180 conceptos nuevos curados del corpus real (retail, manufactura, calidad,
contabilidad, finanzas, IT/soporte, RRHH). **Criterio de curación**: solo
entra lo que nombra una competencia, herramienta, norma o método concreto
(ni funciones como "ventas", ni sectores como "construcción", ni palabras
vacías como "analysis").

**5. CLI**: `enrich requirements-source [--apply] [--platform X] [--limit N]`
(simulación por omisión; re-analiza y guarda con `--apply`).

**Medición (COPIAS — la BD real quedó INTACTA)**:

| Métrica | Antes | Después |
|---|---|---|
| Requisitos vigentes con `codigo_canonico` | 1071/1071 | **2172/2172** (1101 de `source_field`) |
| Viabilidad `sin_datos` | 133 | **9** |
| Viabilidad `aplicar` / `revisar` | 4 / 4 | 4 / 2 |
| Paso 5 `sin_requisitos` | 123 | **9** |
| Paso 5 `revisar_a_mano` | 111 | 275 |

Los 9 que quedan en `sin_datos` son avisos cuyas skills son **frases de
tarea o campos genéricos** ("desarrollo", "computer hardware"): no hay
competencia que comparar y `sin_datos` es la respuesta honesta.

**6. Postulaciones = REGISTRO (no señal de aptitud)**: `applied` = "postulada,
sin respuesta o en proceso"; el rechazo solo se registra si el portal/correo
lo dice explícitamente; **el silencio NO es rechazo**
(`postulaciones.sin_respuesta`, `ETIQUETA_ESTADO`, columna `estado_texto` en
`listar_postulaciones` y en el CSV del CLI).

**Suite**: 846 → **922 tests verdes + 241 subtests**.

### 2026-11-04 — MOTOR DE VIABILIDAD (ajuste técnico) + POSTULACIONES + CAPA B

**Decisión de negocio que ordena todo lo demás:**
> **Ser rechazado de un trabajo NO significa que no se es apto para él.**

El reclutador humano decide por presupuesto, timing, competencia, sesgos y
azar. Por eso se separan DOS cosas que antes se mezclaban:

| | Qué es | Módulo | Se usa para |
|---|---|---|---|
| **Ajuste técnico** | ¿el perfil cumple lo que pide el aviso? | `viabilidad.py` | priorizar a dónde postular |
| **Estado del proceso** | ¿qué decidió el reclutador? | `postulaciones.py` | no reprocesar, medir el funnel, revisar falsos positivos |

**El score NUNCA se entrena con rechazos** (serían etiquetas de aptitud
ruidosas y sesgadas). Los rechazos son señal operativa y contexto.

**1. Motor de viabilidad** (`viabilidad.py`, 12 tests):
- Índice 0-100 + bandas: `aplicar` (≥85) · `revisar` (80-85) ·
  `no_prioritario` (<80) · `sin_datos` · `veto`.
- **Tope duro**: falta ≥1 requisito `required` → banda máxima `revisar`
  (nunca `aplicar`). `preferred` no bloquea; `ambiguous`/`inferred` pesan
  como incierto (1.0) y no activan el tope.
- Pesos: skill 0.40 · education 0.25 · experience 0.15 · language 0.10 ·
  license 0.10 · semántica 0.15. Peso interno: obligatorio 2.0 · incierto
  1.0 · deseable 0.5.
- **DOS PASADAS con imputación del corpus** (igual que el ranking ATS): sin
  esto el score era degenerado (todo 100) porque casi todos los requisitos
  carecen de `codigo_canonico`.
- Vetos: `fuera_de_area` (reutiliza `areas.es_fuera_de_area`: `otros` nunca
  se veta) y `titulo_universitario_requerido` (texto confirmado).
- Reutiliza `matching.EvaluadorPaso5` (no duplica la regla del texto).
- CLI `viabilidad list|top` + UI v2 (columnas "Ajuste"/"Banda", combo de
  bandas, "Solo aplicar", tiles por banda, detalle + CSV ampliado).
- **No toca** los umbrales congelados del Paso 5 ni los estados de
  `job_match` (es un índice paralelo).

**2. Postulaciones** (núcleo puro `postulaciones.py`, 21 tests):
- Estados alineados con `applications.application_status`: `applied` ·
  `recruiter_contact` · `interview` · `offer` · `rejected` · `withdrawn`.
  **El avance nunca se degrada** (`estado_mas_avanzado`).
- Migración `018`: `postulacion_senal` (bitácora) + `postulacion` (estado
  actual por vacante). Se guarda SOLO lo mínimo (estado, fecha, remitente,
  asunto, referencia del aviso): **el cuerpo del correo nunca se guarda**.
- `correo_postulaciones.py`: lector IMAP (Gmail, `X-GM-RAW` + fallback
  `SINCE`), credencial en el keyring (`credenciales.credencial("gmail")`).
- `workday_postulaciones.py`: parsers puros (JSON + HTML) + fetch por CDP de
  "Mis postulaciones" (reutiliza la sesión; el fetcher nunca crea navegador).
- CLI `postulaciones correo|workday|list` (dry-run por omisión).

**3. CAPA B — el perfil ya tiene `codigo_canonico`** (`tests/test_perfil_canonico.py`):
- `save_candidate_profile_facts` / `import_candidate_profile_facts` resuelven
  el código al guardar; backfill idempotente (`enrich profile-canonico
  --apply`).
- **Fallback slug ↔ texto** (`conceptos._variantes_alternas`): el importador
  de CV produce slugs (`active-directory`) y la taxonomía está en texto
  natural (`active directory`).
- **La cola del perfil solo recibe CONCEPTOS** (skill/language/license/
  education): los hechos de `experience` del CV son **títulos de puesto**, no
  conceptos que falten → no se encolan (pero sí reciben código si SÍ son un
  concepto, p. ej. `years_experience`).

**4. Migraciones nuevas** (escritas y **APLICADAS en la BD real** el
2026-11-04: esquema 16 → 19, solo aditivas — auditoría en
`docs/HANDOFF_SESION_2026-11-04.md` §2.7):
- `017_educacion_granular.sql` — master/MBA → posgrado (4); associate degree /
  two year college degree → ciclo corto (2); "bachiller" a secas →
  **secundaria** (1) en CR.
- `018_postulaciones.sql` — bitácora + estado por vacante.
- `019_google_workspace.sql` — corrige un alias **erróneo**:
  `google-workspace` estaba mapeado a `microsoft-365` (son productos
  distintos). Solo se corrigen los que venían de esa variante: un
  `microsoft-365` legítimo no se toca.

**5. Documentación**: `docs/MOTOR_VIABILIDAD.md` (nuevo) + `AGENTS.md`
(secciones nuevas, gotchas 34-39) + este historial.

**Suite**: **846 tests verdes + 241 subtests** (antes 736 + 241).

### 2026-10-30 — O6.3 (mecánicas M1–M4) + O8.1/O10: FILTRO por ÁREA de empleo de punta a punta

**Parte 1 — cierre del bloque educativo (mecánicas generales):**
- **M1** el nivel lo declara el TEXTO (ancla: `job_requirements.evidence`; gana
  la frase más larga) · **M2** una vía académica está o no DISPONIBLE según el
  nivel del perfil (las vías por experiencia NO confirman descarte) ·
  **M3** "X % de un bachelor" = estudios parciales (cumplen título o estar en
  curso) · **M4** sin lógica por país.
- **3 decisiones de negocio resueltas CON FUENTE** (ISCED 2011 / OCDE):
  "advanced university studies" = posgrado (nivel 4) · "two year college
  degree"/"associate degree" = ciclo corto (nivel 2) · "% de completitud" =
  parciales (nivel 3 sin título).
- **Corrida `20261030_151648`** (447 filas, `valida=1`; las 7 previas quedan
  `valida=0`): calificada 104 · revisar_a_mano 90 · **descartada 82** ·
  datos_insuficientes 30 · sin_requisitos 141 (sumas verificadas por
  `GROUP BY estado` = 447). `educacion_no_confirmada` 19 → **30**.
- **Evidencia**: `docs/PASO5_EVIDENCIA_2026-10-30.md` (GENERADO: §1.1
  mecánicas + §7 delta) verificada por `verificar_evidencia.py` → **125
  verificaciones con frase literal, 0 fallos**. El verificador ahora usa por
  defecto el documento de evidencia **más reciente** (antes fallaba en falso
  al haber una corrida nueva).
- **`docs/PASO5_REVISION_PENDIENTES.md`** regenerado: **30 casos**, texto
  completo verbatim, **sin veredictos** (los firma una segunda persona).

**Parte 2 — filtro por ÁREA de empleo (O8.1 + O10):**
- **Migración `016_areas.sql`** (esquema v16): tablas `area`, `area_regla`,
  `job_area`; reconstrucción de `candidate_profile_facts` (CHECK `category` +
  `'area'`) y de `job_match` (CHECK `estado` + `'fuera_de_area'`), copiando
  48 facts y 3576 filas de `job_match` y recreando 5 índices.
  `check_integrity` → ok, 0 violaciones FK.
- **Taxonomía del SISTEMA**: 20 áreas (19 + `otros`) y **51 reglas** en
  `src/jobpulse_v15/seeds/areas.json`; CLI `init-areas [--classify]`,
  `areas list`, `areas classify [--dry-run]`.
- **Módulo `src/jobpulse_v15/areas.py`**: clasificación por **TÍTULO** con
  reglas por **prioridad** (empate en la prioridad máxima → `otros`),
  áreas del perfil (hechos `category='area'`) y predicado `es_fuera_de_area`
  (conservador: sin áreas marcadas no hay filtro; `otros` y las sin clasificar
  **siempre** se evalúan).
- **Al INGESTAR**: `Repository.save_job` clasifica cada vacante nueva → un
  puesto nuevo de **cualquier fuente** (Workday, ANE, Indeed, LinkedIn,
  Elempleo, Harvie, CINDE, Procomer) queda clasificado solo, con la MISMA
  regla (la fuente no aparece en ninguna regla).
- **UI del perfil**: pestaña **"Áreas de empleo"** (casillas por área con el nº
  de vacantes + botón "Guardar áreas"; `otros` anotado "siempre se evalúan").
  **UI principal**: combo "Área", casilla "Solo áreas de mi perfil" y columna
  "Área".
- **Motor del Paso 5**: estado **`fuera_de_area`** (motivo
  `fuera_de_area_del_perfil`), **sin evaluar requisitos**, conservando una
  fila por vacante (auditable); `run_paso5.py --evaluar-todo` desactiva el
  filtro.
- **Medición real** (447 vacantes, `GROUP BY` sobre la BD): 447/447
  clasificadas → informática 92 · producción 43 · ventas 42 · administración 38
  · **otros 34** (32 sin encaje + 2 ambiguos) · alimentación 32 · servicio 20 ·
  logística 18 · automotriz 17 · ingeniería 16 · marketing 16 · salud 15 ·
  almacén 14 · calidad 12 · mantenimiento 12 · RR.HH. 10 · legal 7 ·
  educación 5 · seguridad 4 · construcción 0. **Sin áreas marcadas los
  resultados son IDÉNTICOS a la corrida vigente** → no hizo falta corrida
  nueva; con "todo menos informática" se excluyen exactamente las 92 y con
  solo "administración" se excluyen 375 (se evalúan 72).
- **Tests**: `tests/test_areas.py` (nuevo: 20 tests + 21 subtests, con títulos
  LITERALES de la BD real) + test de UI de marcar/desmarcar en
  `tests/test_ui.py`; suite completa **393 tests verdes**.

### 2026-10-29 (noche) - O6.3 / Paso 5: alcance por grupo + semántica de `education_status` + medición de 43 casos

**Los 3 puntos del bloqueante educativo:**
1. **Medición ampliada** de `educacion_no_cumple` a **43 casos** (estrato A = las 13
   promovidas, todas; estrato B = 30 sistemáticas de las 93 restantes), revisados
   uno por uno contra la frase literal: 26/43 ≈ **60 %** eran bloqueos reales (la
   muestra inicial daba 5/10 = 50 %) → **la regla se sostiene, NO estaba
   sobreajustada**; contra el ground truth manual acierta **43/43**.
2. **Confirmación POR CONSULTA** de las 13 entradas promovidas por la corrida
   `183231` (y de las 80 `descartada` + 19 `educacion_no_confirmada` de la vigente):
   `verificar_evidencia.py` comprueba que cada `job_id` aparece en
   `docs/PASO5_EVIDENCIA_2026-10-29.md` **con frase literal** y que esa frase es
   substring literal de `jobs.requirements_raw` + `jobs.description_raw`.
   Resultado: **112 verificaciones, 0 fallos**.
3. **Semántica documentada de la ausencia de `education_status`**: perfil con
   hechos educativos y ninguno `pursuing` → "no cumple" (bloquea con
   `titulo_universitario_en_curso_requerido`); perfil SIN hechos educativos →
   "no verificable" → `revisar_a_mano` con el motivo nuevo
   `educacion_no_verificable` (nunca se descarta por falta de información).

**Cambios de regla (corrida nueva `20261029_205348`; las 6 previas quedan `valida=0`):**
- **Alcance por GRUPO de enumeración** (`_grupos_terminos` + `_COORDINACION`): la
  negación, el suavizador y la obligatoriedad se aplican al grupo de títulos unidos
  por "or"/"/"/"y".
- **Negación DURA vs. SUAVIZADOR** (`_NEGACION_DURA`): "is preferred but not
  required" → `negacion`; encabezado "Preferred Qualifications" → `suave`.
- **Encabezado de requisitos al final de la cláusula anterior**
  (`_ENCABEZADO_REQUISITOS_FIN`): "…under pressure ____ What you need to bring:",
  "Job Requirements: Active university student…".
- **Perfil de estudiante activo** como exigencia propia: "active university
  student", "students … pursuing", "currently pursuing".
- **"bachillerato universitario"** = título universitario (término explícito).
- **"alternatively, N years of relevant professional experience"** = vía alternativa
  (corrige el falso descarte A2).
- **"or advanced coursework / university studies"** = vía alternativa;
  "or equivalent field of study / discipline / degree" NO lo es.
- **"Who You Are"** NO se añade como encabezado de obligatoriedad (ambiguo →
  queda en revisión).

**Resultado (447 vacantes):** `descartada` 45 -> **80** (56 titulo requerido +
24 estudiante activo); `revisar_a_mano` 94 (19 `educacion_no_confirmada` +
57 `educacion_no_cumple` + 11 skill + 4 experiencia + 3 licencia);
`calificada` 102 · `sin_requisitos` 141 · `datos_insuficientes` 30.
Delta exacto vs. `183231`: **37 cambios** (36 nuevas `descartada` + 1 salida:
A2 → `revisar_a_mano / educacion_no_cumple`).

**Verificacion:**
- `tests/test_matching.py`: 65 casos (19 regresiones con frases literales de la BD +
  `TestSemanticaEducationStatus`).
- Suite completa: **358 tests verdes** (339 + 19 nuevos).
- `generar_evidencia_paso5.py` reescrito (evidencia desde la BD, con la tabla de la
  medición de 43 casos) + `verificar_evidencia.py` (nuevo).

### 2026-10-29 (tarde) - O6.3 / Paso 5: el TEXTO decide la obligatoriedad + estudiante activo

**Cambios de regla (corrida nueva `20261029_183231`; las 5 previas quedan `valida=0`):**
- **La obligatoriedad la decide el TEXTO, no solo `requirement_level`.** Si la
  clausula exige el titulo ("Required/Minimum/Basic Qualifications", "must have",
  "degree or above", "Requisitos", encabezado "Qualifications" en su propia vineta)
  bloquea aunque el extractor lo marque `ambiguous`/`inferred`; si el texto solo lo
  prefiere ("Preferred") NO bloquea.
- **"or equivalent field of study / discipline / degree" NO es via alternativa**
  (sigue exigiendo titulo universitario). **"or advanced coursework / advanced
  university studies" SI es via alternativa** -> no se descarta.
- **Estudiante activo** = criterio explicito y distinto del titulo completado:
  nuevo motivo `titulo_universitario_en_curso_requerido`; se cumple solo si el
  perfil tiene un hecho educativo con `education_status='pursuing'`.
- `Requisito` gana `education_status`; el perfil carga `education_status` de sus
  facts (`candidato_universitario_en_curso()`).

**Resultado (447 vacantes):** `descartada` 32 -> **45** (37 titulo requerido +
8 estudiante activo); `revisar_a_mano` **128** (20 `educacion_no_confirmada` +
90 `educacion_no_cumple` + 11 skill + 4 experiencia + 3 licencia);
`calificada` 102 · `sin_requisitos` 141 · `datos_insuficientes` 31.
Delta exacto: 13 entradas a `descartada` (con frase literal), 1 salida
(`workday-Accounting-Analyst---Temporary_J-020392`, via alternativa "or advanced
university studies"), 7 reetiquetadas como *estudiante activo*.

**Medicion (muestra 10 de `educacion_no_cumple`):** 5/10 eran bloqueos REALES
escondidos por el nivel del extractor -> la regla nueva los promueve con evidencia.

**Verificacion:**
- `tests/test_matching.py`: 46 casos (15 regresiones con frases literales de la BD).
- Suite completa: **339 tests verdes** (324 + 15 nuevos).
- `docs/PASO5_EVIDENCIA_2026-10-29.md` regenerado por
  `generar_evidencia_paso5.py` (704 lineas, 45 descartadas + 20 no confirmadas).
- SQL directo sobre la corrida `183231`: las 8 correcciones de la sesion anterior
  siguen `revisar_a_mano / educacion_no_confirmada`.

### 2026-10-29 - O6.3 / Paso 5: matching de requisitos vs. perfil (modulo real + evidencia literal)

**Implementado:**
- **`src/jobpulse_v15/matching.py`** - modulo real del Paso 5 (carga desde BD,
  evalua por vacante, escribe una **corrida nueva** en `job_match` e invalida las
  previas con `valida = 0`). Sin datos del candidato hardcodeados: todo sale de
  `candidate_profile_facts` + `concepto` (`MAX(nivel_orden)` para el nivel efectivo).
- **`src/jobpulse_v15/migrations/015_job_match_valida.sql`** - columna `valida` +
  indices (migracion numerada nueva; no se edito ninguna ya aplicada).
- **`tests/test_matching.py`** - 31 casos, 11 de ellos regresiones con frases
  literales copiadas de la BD real.
- **`run_paso5.py`** (runner, `--dry` opcional), **`evidencia_descartadas.py`**,
  **`resumen_bloqueo.py`**, **`verificar_corridas.py`** - verificacion reproducible.
- **`docs/PASO5_EVIDENCIA_2026-10-29.md`** - evidencia literal de las 32
  `descartada` y de las 20 `revisar_a_mano / educacion_no_confirmada`.
- **Limpieza**: 75 scripts ad-hoc de la raiz eliminados (los `paso5_*.py` viejos
  quedaron obsoletos al mover la logica a `src/`).
- **Migraciones 009-014** (`concepto` canonico + `job_match` + `corrida_id` +
  columnas de conteo) versionadas por primera vez en git.

**Correccion del bloqueante educativo (falsos descartes -> `revisar_a_mano`):**
- `linkedin-4483157697` - "No university degree required." (negacion pegada al termino).
- `workday-Credit---Collections-Specialist--2_R232432` - "Associate's or bachelor's degree" (alternativa).
- `workday-Instructional-Designer_R17971` - "Bachelor's degree or certification" (alternativa).
- `workday-Security-Governance---Compliance-Specialist_2022361-1` - "equivalent practical experience may be considered" (alternativa en la clausula siguiente).
- `workday-Cardiac-Specialist-II_R18282-1` - "or an equivalent combination of education and relevant experience" (alternativa).
- `workday-Assistant-Director-of-Engineering_REQ10393409` - alternativa detectada en el texto.
- `workday-Production-Supervisor-I_31163511` / `_31163518` - "or other technical/scientific experience" (alternativa en la clausula completa).

**Resultado:** `descartada` 40 -> **32** (corridas `160358` -> `171039`); las 8
corregidas pasan a `revisar_a_mano / educacion_no_confirmada`. Resto de estados
identico (calificada 102 - sin_requisitos 141 - datos_insuficientes 31 -
revisar_a_mano 141). Suite completa: **324 tests verdes** (se arreglo
`tests/test_database.py`, que fijaba la version de esquema en `8` - ya fallaba
desde la migracion 009). RECENTES

### 2026-10-24 — IA Externa: cliente OpenAI-compatible (`ia_api.py`) + `init-sources` completado

**Implementado:**
- **`ia_api.py`** — Cliente IA externa compatible OpenAI con 6 presets:
  - `openrouter` — openrouter.ai/api/v1 (modelo default: `~openai/gpt-latest`)
  - `nvidia` — integrate.api.nvidia.com/v1 (modelo default: `openai/gpt-oss-20b`)
  - `google` — generativelanguage.googleapis.com/v1beta/openai/ (modelo default: `gemini-2.5-flash`)
  - `ollama` — ollama.com/v1 o localhost:11434/v1 (auto-detecta modelo via `/models`)
  - `lmstudio` — localhost:1234/v1 (auto-detecta modelo via `/models`)
  - `custom` — cualquier endpoint OpenAI-compatible (**llama.cpp**, vLLM, etc.)

**Características clave:**
- Cache persistente en disco (hash determinista: proveedor + modelo + mensajes + PROMPT_VERSION)
- Rate limiting configurable (RPM) + reintentos automáticos en 429/5xx
- `chat_json()` con `response_format` json_schema/json_object para respuestas estructuradas
- `listar_modelos()` consulta GET /models en vivo (sin hardcodear modelos)
- Errores tipados: `IAModeloError` (404/410 fatal), `IACuotaError` (402/429)
- Hash de vacante/CV para cache determinista
- `PROMPT_VERSION = "v3"` invalida cache al cambiar prompts

**Configuración llama.cpp / LM Studio (local):**
```bash
# .env
IA_PROVEEDOR=custom
IA_BASE_URL=http://localhost:8080/v1
IA_MODEL=llama-3.1-8b-instruct
IA_API_KEY=sk-no-key-needed

# Levantar llama.cpp
llama-server -m modelo.gguf -c 8192 --port 8080
```

**Comando `init-sources` completado:**
- Registra 12 plataformas + 5 sitios CR automáticamente
- `--skip-existing` para idempotencia
- Grupos configurables: `--group-gov cr-gov` / `--group-jobs cr-jobs`

**Tests:** 127/127 pasan (excluyendo test_ui por entorno Tcl/Tk)

**Próximos pasos FASE 2:** `search_engine.py` (embeddings), `ats.py`, `gate.py`, `ia_calibracion.py`, `cv_analysis.py`, `cv2profile.py` — **Todos completados. Pasar a priorizar fetchers CR o FASE 3.

---

### 2026-10-24 — Credenciales + Login manual (`credenciales.py`, CLI `credenciales`/`login`)

**Implementado:**
- **`credenciales.py`** — Almacén local completo (gitignored):
  - `credenciales.json` — credenciales usuario/password/SSO
  - `login_requerido.json` — LA LISTA maestra (seeds + runtime + manual)
  - `pending_login.json` — pendientes detectados en corridas
  - `login_sites.json` — portales employer para barrido con navegador

**Seeds configurados:**
- **ANE** — obligatorio, auto_login, user/password (fallback .env: ANE_USER/ANE_PASSWORD)
- **Indeed** — obligatorio, auto_login, SSO Google (cuenta Gmail, no password propia)
- **LinkedIn** — opcional, SSO Google, prioridad login manual en Brave

**CLI `credenciales`:**
- `list` / `list --resumen` / `list --solo-faltantes`
- `set --empresa --usuario [--password|--sso google] [--auto on|off] [--url]`
- `del --empresa`
- `auto --empresa --estado on|off`
- `add-site --empresa [--url] [--grupo] [--obligatorio]`
- `rm-site --empresa`

**CLI `login`:**
- `login --list` — lista pendientes/recomendados
- `login` — abre cada sitio en TU Brave (pestaña en sesión viva), tú te logueas, confirmas, y la sesión queda para el scraper
- Reusa `BraveManager` para lanzar Brave con CDP

**Tests:** 127/127 pasan

**Completado FASE 3 (Auth/Session):**
- **`providers/login/auto_login.py`** — SSO Google Indeed/LinkedIn (iframe GIS, popup, selector cuenta), fallback a login manual si Google pide password/CAPTCHA/2FA; user/pass 1-2 pasos con selectores configurables; `hay_login_configurable()`
- **`providers/login/browser_sites.py`** — LoginSitesProvider con 2 modos:
  - `dom`: extraccion por selectores CSS (card_sel, title_sel, etc.) + paginacion + deteccion Cloudflare Turnstile (auto-click checkbox) + login-wall -> registra pendiente
  - `page_fetch`: fetch API interna del SPA (mismo origen, cookies CF) + JSONPath + dot-paths
- Ambos usan `credenciales.py` para auto-login opt-in

**Tests:** 127/127 pasan

**Próximos pasos FASE 2:** `search_engine.py` (embeddings), `ats.py`, `gate.py`, `ia_calibracion.py`, `cv_analysis.py`, `cv2profile.py` — **Todos completados. Pasar a priorizar fetchers CR o FASE 3.

---

### 2026-10-25/26 — IA local canónica, instalador, capa IA de CVs, repo al día

- **Gemma 4 E2B QAT canónico** (8k ctx + MTP draft, puerto 8081): A/B vs Qwen
  3.5 2B — ~6.5x más rápido; pase completo 175 jobs en 10.3 min (detalle en
  `docs/IA_ENRIQUECIMIENTO.md`). `ia-server.bat` + `start_ia_server.py` (`--metrics`).
- **Instalador IA equipo nuevo**: `instalar-modelo-ia.bat` / `instalacion_ia.py`
  (modelo Unsloth con SHA256 verificados + llama.cpp Vulkan; `--check` = verificar).
- **Capa IA de CVs (O6.2)**: `cv_ia.py` (PDF/DOCX/TXT → harvard-ats-v1, E2E con
  Gemma local y Gemini) e **integrada** al asistente "Importar CV…" de la UI
  (reglas primero; pase IA si sugieren <5 facts; revisión en `_DialogoRevision`).
- **Suite**: 217 tests + 46 subtests (pytest del sistema; el venv no trae
  pytest). Flaky de Tk estabilizado con `_tkroot_reintentos()` (tests/test_ui.py).
- **Seguridad**: `login_ane.py` SIN credenciales en el código — lee del almacén
  (`credencial("ANE")`: keyring de Windows + `data/empresas/credenciales.json`,
  fallback `.env` ANE_USER/ANE_PASSWORD). `keyring` instalado en el venv y
  credencial ANE migrada al almacén. **Pendiente del usuario: rotar la
  contraseña de ANE** (quedó expuesta en el historial git público) y
  actualizarla con `credenciales set`.
- **Docs al día y verificados contra el código**: `AGENTS.md`, este documento
  (estado, FASE 1, gaps, comandos) y `README.md` (tests con pytest).
- **Mudanza a repo propio**: `giovar24/jobpulse-cr-v15` en `D:\Proyectos\v1_5`
  (95 commits del fork vía subtree split; contraseña de ANE purgada del
  historial con git-filter-repo ANTES de publicar; venv, `.env` y BD movidos
  con la carpeta; editable reinstalado en venv y python del sistema).