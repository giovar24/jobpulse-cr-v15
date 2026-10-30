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
| **O2 / O3 / O4** (ATS + ranking en búsqueda UI; validar 7 fetchers ATS huérfanos; calibración gate-vs-IA) | 🟡 | Ver handoff vigente |
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

### OBJETIVOS O1–O10 (lista canónica, estado al 2026-10-29)

> Cada handoff de sesión lleva su copia de esta tabla con el estado al cierre.

| Objetivo | Qué es | Estado |
|---|---|---|
| **O1** Enriquecimiento IA | Pase IA (Gemma local) llenando huecos: city/region/work_mode/employment_type/salary/skills/languages | ✅ **COMPLETO (27-10, 44 min; O7.3 E2E: servidor subió → pasó → se apagó solo)**. Resultado: skills 100%, date_published 100%, region 95.6%, employment_type 95.3%, languages 95.3%, city 91.9% (residuo = remotos / lat_raw de Indeed sin normalizar), work_mode 53.6% (137 'unknown': 46 basura O5.3 + 91 honestos sin mención), salary_raw 117 = fuente SIN texto salarial (irrecuperable). Los ciclos 2+ son replays de caché (ver gotcha: failed ≠ error) |
| **O2** Afinar la búsqueda | ~~ATS + gate + ranking semántico~~ **Redefinido por el usuario (2026-10-27): la precisión viene de la data extraída** → completar O1 (huecos). Alcance operativo: **O2.1** normalizar locations crudas de Indeed ("Heredia, Provincia de Heredia" → city/region); **O2.2** filtro UI "solo con requisitos obligatorios" + columna "Req." (aprobado por el usuario, estaba pospuesto); motor semántico **DORMIDO por decisión** (nicho: texto libre ES↔EN) | 🟡 enfoque data-first · verificado 2026-10-27: `search_engine.py` funcional (EmbeddingGemma gated → fallback `paraphrase-multilingual-mpnet` 768d; similitud ES↔EN correcta) pero **sin cablear**, caché de embeddings vacía; `ats.py`/`gate.py`/`ia_calibracion.py` sin callers ni tests |
| **O3** Fetchers ATS huérfanos | Validar los 7 fetchers ATS (workday, greenhouse, ashby, lever, recruitee, workable, successfactors) con tableros reales | ⏳ no iniciado |
| **O4** Calibración gate-vs-IA | Pearson/Spearman/MAE + umbral sugerido (`ia_calibracion.py`) | ⏳ depende de O1+O2 |
| **O5** Higiene de datos | O5.1 ✅ auditoría/huecos · O5.3 re-barrido de los ~14-19 jobs con descripción basura (login-wall) · **O5.4 ✅ CERRADO (2026-10-27)**: análisis por **huella de descripción** (en ANE el título+empresa NO es identidad — "Confidencial"); solo 4/120 del lote 26-10 eran republicaciones → **las 4 viejas marcadas `dismissed` con nota** (parejas 121034/121185, 121026/121184, 121025/121183, 120958/121094), las nuevas quedan activas; grupos misma-empresa+misma-ciudad (INAMU ×3, SALESLAND ×2) = **plazas múltiples, decisión del usuario, intactos**; multi-sede (INAMU 8 ciudades, HIPERMASCOTAS 2 tiendas) = vacantes reales | 🟢 solo queda O5.3 |
| **O6** Perfil del candidato | O6.1 editor ✅ · O6.2 capa IA de CVs + integración UI ✅ · **O6.3 matching afinado (niveles/CEFR) ✅ CERRADO (2026-10-29)** — ver bloque "O6.3 — Matching (Paso 5)" más abajo · O6.4 dedupe semántico del perfil (slugs ES/EN del mismo hecho: normalizar al importar vs. decidir en diálogo — pendiente decisión del usuario) | 🟢 O6.1/O6.2/O6.3 cerrados · O6.4 pendiente decisión |
| **O7** Operación UI-first (servidores bajo demanda) | La app arranca/detiene lo que necesita; el usuario no toca CLI ni launchers | ✅ **completo (2026-10-27)** |
| **O8** Ciclo de vida de la vacante | Plan previo del usuario (recordado 2026-10-27; formalizado tras investigar el estado real del código). **O8.1 categorías de puestos** ❌ no existe ningún campo (hoy solo hay categorías de REQUISITOS: education/experience/language/license/skill) → taxonomía nueva (migración 00N) editable en UI, sugerencia IA opcional (decisión 27-10: el AGENTE genera el borrador desde los 295 jobs con `tools/categorias_borrador.py`; el usuario corrige después) · **O8.2 recurrentes y aplicadas ocultas por defecto (decisión del usuario 27-10, refinada con ejemplo Concentrix)**: ⚠️ **ESTABA RESUELTO en v1.x (tombstones + `dup_of`, ver sub-diseño) y NO se portó**; hoy la republicación nace con ID nuevo y el estado manual del ID viejo NO se arrastra. Diseño aprobado: **matching por compañía + huella de descripción** (el título NO como criterio primario — O5.4 demostró falsos: 13 coincidencias solo-título NO eran republicaciones y grupos mismo-título eran plazas distintas). Al INGERIR una copia nueva que coincida (huella exacta o ratio ≥ ~0.92) con una ya marcada reviewed/applied → **la copia hereda el estado manual automáticamente** (nace oculta + nota de herencia con el ID origen; datos intactos — regla de repo actualizada 27-10: duplicado EXACTO = auto, patrón de v1.x; dudoso = manual). Margen incierto (ratio medio) → `quality duplicates` (dedupe conservador intacto). Opt-in en UI para mostrar repetidas/ya aplicadas; marcar aplicado = SIEMPRE manual. Y la ocultación NO es perpetua: **ventana temporal definida por el usuario en la pestaña de Configuración** (selector 1/2/3/6 meses, etc. — decisión del usuario 27-10; ancla = `updated_at` del estado del original): la copia solo hereda el estado (y queda oculta) si el estado del original tiene MENOS de la ventana; si el original ya la supera, la copia entra como vacante NUEVA (nuevo ciclo, re-aplicable). Default DECIDIDO por el usuario (27-10): **3 meses** (persistencia en `ui_config.json`, pestaña nueva "Vacantes" de Configuración; selector 1/2/3/6/12) · **O8.3 registro de aplicados** ✅ YA EXISTE: estado "Aplicada" en el diálogo de estado (excluye de búsqueda por defecto vía skip_automatic) + tabla `applications` (planned → applied → recruiter_contact → interview → offer, con applied_at + next_action_at + notas) + diálogo Seguimiento por vacante · **O8.4 de-baja automática por tiempo** ⚠️ **EXISTÍA en v1.x (`purge_expired`, ver sub-diseño) y NO se portó**: en v1.5 la búsqueda no filtra por edad ni vigencia (`expires_at` SOLO ANE lo llena; `gate.es_vigente` dormido sin callers) → portar como **OCULTAR, no borrar** (v1.x borraba filas): vencidas por `expires_at`, sin vencimiento → fuera de la ventana de publicación, sin fecha legible → TTL por `created_at`; ventana configurable en la MISMA pestaña "Vacantes" (decisión 27-10; default propuesto: 6 meses) | 🔵 diseñado 27-10 — implementación = portación de v1.x |
| **O9** Optimización de UI | Ajustes de interfaz pedidos por el usuario y siempre pospuestos — alcances por definir (después de O2-redefinido) | ⏳ placeholder |
| **O10** Mejorar filtros de búsqueda y compatibilidad | El paso 4 del flujo filtraba `matched` a ciegas → grilla vacía (0 jobs cuando 370/447 análisis son `partial`). `ui.elegir_filtro_compatibilidad()` usa `matched` si existe y si no muestra todos los vigentes, explicando por qué. Pendiente: refinar `solo_vigentes` (uso `date_published` vs `last_seen_at`), visibilidad opt-in de recurrentes/aplicadas (O8.2), y columna "Req." (O2.2). | 🟡 diseñado (elegir_filtro_compatibilidad implementado 28-10) |

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

**Pendiente del Paso 5**: solo la **aplicación manual** de las 19
`revisar_a_mano / educacion_no_confirmada` (el análisis de por qué no se descartan ya
está hecho) y después las decisiones/UI/export (Paso 7).

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

# === UI ===
.\.venv\Scripts\python.exe -m jobpulse_v15.ui

# === TESTS ===
python -m pytest tests/ -q    # pytest vive en el python del sistema (el venv no lo trae)
```

---

## 5. PRÓXIMA ACCIÓN INMEDIATA

Pendientes vivos (handoff vigente `docs/HANDOFF_SESION_2026-10-27.md`):

1. **Prueba de humo del usuario (cierra O7)**: abrir la UI → "Ejecutar barrido"
   (Brave abre/cierra solo; de paso refresca las ~46 descripciones basura si
   la sesión ANE vive — si no, "Re-login ANE" primero) → "Enriquecer" (con
   la BD ya llena responde casi instantáneo por caché).
2. **O5.3**: re-barrido de los jobs con descripción basura (login-wall) —
   hoy ~46 (creció con el lote nuevo); vía UI.
3. **O8 Ciclo de vida de la vacante** (nuevo, 27-10): comportamientos
   decididos — recurrentes y aplicadas ocultas por defecto (opt-in para
   verlas); aplicado = manual; herencia por compañía + huella de
   descripción (exacta o ratio ≥ ~0.92; margen incierto → quality
   duplicates), con **ventana temporal configurable en Configuración**
   (1/2/3/6 meses…; fuera de la ventana la copia entra nueva). Falta
   decidir: default de la ventana (prop. 3 meses), de-baja de jobs viejos
   (O8.4) y taxonomía de categorías (O8.1); luego migración + lógica en
   repository/ingest + UI.
4. **O2-redefinido (afinar búsqueda)**: **O2.1** normalizar locations
   crudos de Indeed ("Heredia, Provincia de Heredia"); **O2.2** filtro
   "solo con requisitos obligatorios" + columna "Req."; motor semántico
   DORMIDO.
5. **O6.3** (matching afinado) · **O6.4** (dedupe semántico del perfil:
   slugs ES/EN — decidir import vs diálogo). **O6.3 ✅ cerrado 29-10**
   (ver bloque "O6.3 — Matching (Paso 5)").
6. **Paso 6/7 del matching**: la revisión manual del grupo
   `revisar_a_mano / educacion_no_confirmada` ya está HECHA (20 revisadas con
   evidencia literal; 19 no bloqueantes, 1 bloqueo real corregido) y la **medición
   ampliada a 43 casos** del grupo `educacion_no_cumple` también (26/43 bloqueos
   reales ≈ 60 % → la regla se sostiene; 43/43 contra el ground truth manual).
   Falta la **aplicación manual** de las 19 que quedan y luego las decisiones
   finales + UI + export (Paso 7). **No tocar los umbrales** (cobertura 0.60 /
   puntaje 0.80) sin acuerdo explícito.
7. Luego: **O9** (optimización de UI — alcances por definir), O3 (validar
   7 fetchers ATS), O4 (calibración — redefinir: sin gate semántico no
   tiene contra-qué comparar).

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
  (decisión del usuario, 2026-10-29): revisar cada vacante con su frase literal,
  decidir (queda en `revisar_a_mano` o es bloqueo real) y **registrar** la decisión
  en una tabla nueva (p. ej. `job_match_decision`, con migración numerada) que el
  Paso 7 lea; si el registro cambia los estados, se escribe con **corrida nueva**
  (`valida=1`), nunca `UPDATE` sobre una corrida emitida.

---

*Última actualización: 2026-10-29 (O6.3 matching / Paso 5: alcance por grupo de enumeración + semántica de `education_status` + medición ampliada a 43 casos; corrida vigente `20261029_205348`)*
*Próxima revisión: tras aplicar las decisiones manuales del Paso 7 (UI + export)*

---

## 8. HISTORIAL DE CAMBIOS RECIENTES

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