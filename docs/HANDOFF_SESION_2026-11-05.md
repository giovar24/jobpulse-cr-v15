# Handoff — Sesión 2026-11-05

**TL;DR**: Cerrado el bloque de **IA EXTERNA** (O11/O14): Ollama **Cloud**,
Ollama local y LM Studio son alternativas reales a la IA local, con el mismo
cliente y el mismo pase — el camino de ejecución estaba roto y ya no lo está.
El **tope de avisos** (`IA_MAX_VACANTES`) es **opt‑in y ajustable** (vacío =
sin tope; nada de valores fijos). **Metas replanteadas** (O11–O14): la
prioridad real pasa a **O12 (paridad CLI/UI)** y **O13 (cobertura de
fuentes)**; el plan está en `docs/PLAN_MEJORAS.md` (5 olas, con criterio de
aceptación). **Al cierre se ejecutó la Ola 1 completa (O12)**: re-análisis
incremental, badge de obsoletos, guarda antes del Paso 5, evidencia como
módulo y login ANE con cierre ordenado. **Medición en copia de la BD real:
`sin_requisitos` 231 → 11 (−220).** Al cierre se ejecutó también la **Ola 2**:
orquestador único `jobpulse_v15.pipeline` (una implementación por etapa) y
botones **"Procesar"** y **"Enriquecer IA"** en la UI v2 (con test de paridad
UI/CLI). Suite: **1021 passed + 241 subtests** (base 922 → +99),
**Commits pusheados** a `origin/main` (`caf486d`, `49f3827`).

> ℹ️ Esta sesión continúa el trabajo de la **noche del 2026-11-04** (sin
> handoff propio): limpieza total + proceso completo sobre la BD real, que
> quedó en **esquema 21, 705 avisos, corrida `20261104_231932`**. El resumen
> está en §7.

---

## 1. La decisión que ordena todo lo demás (no cambió)

> **Ser rechazado de un trabajo NO significa que no se es apto para él.**
> (decisión del usuario, 2026-10-27)

| | Qué es | Módulo |
|---|---|---|
| **Ajuste técnico** | ¿el perfil cumple lo que pide el aviso? | `viabilidad.py` |
| **Estado del proceso** | ¿qué decidió el reclutador? | `postulaciones.py` |

Y la regla de oro que se aplicó hoy: **lo que el usuario ve en la UI tiene que
ser lo mismo que ve la CLI**. La UI mentía (231 avisos `sin_requisitos` vs
11 de la CLI) porque analysis **antes** de la IA y nunca re-analizaba.

---

## 2. Lo que se hizo

### 2.1 Diagnóstico: la IA externa estaba "configurada" pero no era ejecutable

El cliente (`ia_api.py`) y las dos UIs **ya** permitían configurar proveedor,
base_url, modelo y API key. Los límites eran de **ejecución**, no de
configuración:

| # | Bloqueo | Síntoma |
|---|---|---|
| 1 | `ia_servidor.asegurar_servidor()` arrancaba llama-server y buscaba `/health` | `RuntimeError: Servidor EXTERNO … no responde` → el pase moría **antes** de empezar (`run_enriquecimiento.py:32`, `ui.py` botón Enriquecer y flujo completo) |
| 2 | `chat_json` forzaba `response_format: json_schema` + `strict` | HTTP 400 en Gemini / LM Studio / Ollama (no lo soportan) |
| 3 | `IA_MODEL=auto` | se enviaba `model: ""` (no había autodetección) |
| 4 | Privacidad | con IA externa el **texto de los avisos salía de la máquina** sin ningún aviso |
| 5 | Presets | **duplicados y divergentes**: "ollama" era *Cloud* en el cliente y *local* en la UI |

### 2.2 Lo implementado

| Cambio | Dónde | Detalle |
|---|---|---|
| `es_endpoint_local()` | `ia_servidor.py` | decide por **host real** (`urlparse`), no por búsqueda de texto: `127.0.0.1`, `localhost`, `::1`, `0.0.0.0`, `host.docker.internal`, `127.*` → local; el resto → externo |
| `asegurar_servidor()` | `ia_servidor.py` | con endpoint externo devuelve `None` **sin arrancar ni detener nada local** (`arrancar_servidor` sigue lanzando para externo: hay test que lo garantiza) |
| `IAPeticionError` + degradación | `ia_api.py` | 400/422 → `IAPeticionError`; `chat_json` degrada **solo** ante rechazo del proveedor: `json_schema` → `json_object` → sin `response_format`. **429/404 no degradan** (son errores reales) |
| `_resolver_modelo()` | `ia_api.py` | `auto` → `GET /models` (usa el primero); si el endpoint no expone modelos, error explícito ("Define IA_MODEL") |
| Presets unificados | `ia_api.PRESETS` | **fuente única** que ven las dos UIs: `ollama`=**Ollama Cloud** (`https://ollama.com/v1`), `ollama-local` (`http://localhost:11434/v1`), `lmstudio` (`http://localhost:1234/v1`), `openrouter`, `nvidia`, `google`, `custom` |
| Aviso de privacidad | `ia_enrichment.aviso_privacidad()` | con IA no local: el texto (descripción, requisitos, perfil) sale de la máquina → **confirmación obligatoria** en UI (`ui.py:_confirmar_ia_externa`, en "Enriquecer" y en "Flujo completo") y en CLI (`run_enriquecimiento.py --confirmar-externo`); el pase deja el aviso en el log |
| Preflight con contexto | `ia_enrichment.verificar_servidor_ia()` | mensaje según local ("arranca llama-server") o externo ("revisa IA_BASE_URL / IA_MODEL / API key") |
| **O14 — límites ajustables** | `ia_api.py`, `ia_enrichment.py`, ambas UIs | `IA_MAX_LLAMADAS`, `IA_RPM` y **`IA_MAX_VACANTES`** (avisos por corrida). **Vacío = sin tope**; `0` o valor no numérico = sin tope (con aviso, no con crash). El presupuesto se consume a lo largo de la corrida (ciclos críticos + pase completo), no se reinicia |
| `pase_completo(max_vacantes=, db_path=)` | `ia_enrichment.py` | testeabilidad + CLI; el CLI imprime el tope vigente |
| UI v2 Configuración | `ui_v2/tabs/configuracion.py` | campo "Máx. avisos" (`IA_MAX_VACANTES`) + la tarjeta "IA local" detecta el proveedor externo (no habilita "Arrancar" y lo dice) |
| UI clásica Configuración | `configuration_window.py` | campo "Máx. avisos por corrida" + presets desde `ia_api.PRESETS` |

### 2.3 Tests

`tests/test_ia_externa.py` (**39 tests**): endpoint local vs externo ·
`asegurar_servidor` externo (no arranca nada) · degradación de `chat_json`
(3 modos + no-degradar 429) · preflight local/externo · aviso de privacidad ·
tope opt-in (env vacío/0/no-numérico/explícito) · auto-modelo · **end-to-end
contra un proveedor OpenAI-compatible real por HTTP** (un `http.server` que
rechaza `json_schema` y acepta `json_object`).

Suite completa: **961 passed + 241 subtests** (~3:30 min).

---

## 3. Decisiones de diseño

| Tema | Decisión |
|---|---|
| Motor de IA | **Intercambiable**, no "local vs externo": el mismo cliente OpenAI-compatible para todos. La IA local es **una** configuración, no una arquitectura aparte |
| Qué NO degrada | Un 429 (cuota) o un 404 (modelo) **no** degradan el formato de respuesta: degradar ahí gastaría cuota y escondería el error real |
| Privacidad | El aviso es **obligatorio** con IA no local y va **antes** de enviar nada (no un log posterior). La UI pregunta; el CLI exige `--confirmar-externo` o una respuesta por consola |
| Límites | **Opt-in y ajustables**, nunca con valor fijo por defecto (regla del proyecto). `IA_MAX_VACANTES=0` = sin tope, no "cero avisos" |
| Presets | **Una sola tabla** (`ia_api.PRESETS`): la UI clásica y la v2 leen la misma (antes divergían) |
| `ollama` | Ahora es **Ollama Cloud**. `IA_PROVEEDOR=ollama` + `IA_BASE_URL` explícito sigue mandando sobre el preset → los `.env` existentes con Ollama local **no se rompen** |

---

## 4. Metas replanteadas (tabla canónica O1–O14)

| Objetivo | Qué es | Estado |
|---|---|---|
| O1–O6 (pipeline scrape → matching) | — | ✅ Hecho (sesiones previas) |
| O7 (IA local/browser) | — | ✅ Hecho |
| O8/O10 (retención + diagnóstico + filtros) | — | ✅ Hecho |
| O2.2 (Req. + filtro) · O3 (salud de sitios) | — | ✅ Hecho (2026-11-04) |
| Capa B (`codigo_canonico` del perfil) | — | ✅ Hecho y efectivo en la BD real |
| Motor de viabilidad (ajuste técnico) | — | ✅ Hecho (pesos = priors; falta ground truth propio) |
| Postulaciones (correo + Workday) | — | ✅ Hecho en código; falta validación en vivo |
| Bloque de ALINEACIÓN (campos estructurados) | — | ✅ Hecho **y aplicado en la BD real** (esquema 21, corrida `20261104_231932`) |
| **O11 IA externa / motor intercambiable** | Ollama Cloud, Ollama local, LM Studio, gateways | ✅ **Hecho (2026-11-05)** |
| **O12 Paridad CLI/UI** | La UI debe dar los mismos números que la CLI | 🟡 **Ola 1 hecha (2026-11-05)**: 231 → 11 `sin_requisitos` en la medición; falta la Ola 2 (orquestador) |
| **O13 Cobertura de fuentes** | LinkedIn y Elempleo dan 0 avisos; ANE pierde la cookie de sesión | 🔴 **ABIERTO — meta #2** |
| **O14 Control del coste de la IA** | Límites opt-in y ajustables (nunca fijos) | ✅ **Hecho (2026-11-05)** |
| `educacion_no_confirmada` | 31 casos | ⏳ **ABIERTO** (firma de una 2ª persona) |
| O5.3 (re-barrido de descripciones basura) | 43 descripciones <200 chars (35 de ANE) | ⏳ Pendiente (Ola 4) |
| O6.4 (dedupe slugs ES/EN) | — | ⏳ Parcial (el resolver ya tolera slug↔texto) |
| O4 (calibración gate-vs-IA) | — | 🟡 Proponer cerrar como *superseded* (no hay gate semántico) |
| O8.2 / O8.4 / O9 / pestañas nuevas UI v2 | — | ⏳ Pendiente (Ola 4) |

**Orden de ejecución** (detalle en `docs/PLAN_MEJORAS.md`):
Ola 1 (cierra O12, cambios chicos) → Ola 2 (orquestador `pipeline.py`, O12) →
Ola 3 (O13: selectores + login ANE) → Ola 4 (calidad de datos) → Ola 5 (se
puede dejar de último).

---

## 5. Cómo retomar (comandos)

```powershell
# Suite completa (python del SISTEMA)
python -m pytest tests/ -q

# Solo lo de esta sesión
python -m pytest tests/test_ia_externa.py tests/test_ia_enrichment.py `
  tests/test_ia_servidor.py tests/test_ui_v2.py -q

# Ola 1 de O12 (re-análisis, evidencia, login ANE)
python -m pytest tests/test_reanalisis.py tests/test_evidencia.py `
  tests/test_ane_login.py -q

# Ola 2 de O12 (orquestador + botones de UI v2)
python -m pytest tests/test_pipeline.py tests/test_ui_v2.py -q

# Evidencia (exit 0 = todo cuadra) y estado de la BD
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py
.\.venv\Scripts\python.exe -X utf8 tools\estado_bd.py

# Probar la IA externa con otro proveedor (cambia SOLO el .env)
# IA_PROVEEDOR=ollama
# IA_BASE_URL=https://ollama.com/v1
# IA_MODEL=<modelo del endpoint>
# OLLAMA_API_KEY=...
.\.venv\Scripts\python.exe -X utf8 run_enriquecimiento.py --confirmar-externo
```

---

## 6. Archivos clave

| Archivo | Qué es |
|---|---|
| `src/jobpulse_v15/ia_api.py` | Cliente OpenAI-compatible: presets (fuente única), degradación de `response_format`, autodetección de modelo, límites opt-in |
| `src/jobpulse_v15/ia_servidor.py` | `es_endpoint_local()` + `asegurar_servidor()` (con externo no arranca nada local) |
| `src/jobpulse_v15/ia_enrichment.py` | `aviso_privacidad()`, `verificar_servidor_ia()` (mensaje según local/externo), `tope_vacantes()`, `pase_completo(max_vacantes=, db_path=)` |
| `run_enriquecimiento.py` | CLI del pase IA: aviso + confirmación externa, tope vigente, `--confirmar-externo` |
| `src/jobpulse_v15/ui.py` | `_confirmar_ia_externa()` (Enriquecer + Flujo completo) |
| `src/jobpulse_v15/ui_v2/tabs/configuracion.py` | Tarjeta IA externa: "Máx. avisos" + estado de proveedor externo |
| `src/jobpulse_v15/configuration_window.py` | UI clásica: "Máx. avisos por corrida" + presets desde `ia_api.PRESETS` |
| `tests/test_ia_externa.py` | **NUEVO** — 39 tests del soporte de IA externa |
| `src/jobpulse_v15/evidencia.py` | **NUEVO (Ola 1.4)** — generar/verificar/estado de la evidencia del Paso 5 (los scripts son envoltorios) |
| `src/jobpulse_v15/pipeline.py` | **NUEVO (Ola 2.1)** — orquestador único: `ejecutar(repository, etapas=..., progreso=...)`; una implementación por etapa |
| `src/jobpulse_v15/analysis_flow.py` | **Ola 1.1/1.2** — `reananalizar_con_campos_fuente`, `avisos_con_campos_sin_integrar`, `cuenta_analisis_obsoletos`, `analisis_refleja_campos` |
| `tests/test_reanalisis.py` | **NUEVO** — 14 tests de 1.1/1.2 (idempotencia, no infla `job_analysis`) |
| `tests/test_evidencia.py` | **NUEVO** — 19 tests de 1.4 |
| `docs/PLAN_MEJORAS.md` | **NUEVO** — 5 olas con criterio de aceptación |
| `docs/IA_ENRIQUECIMIENTO.md` | Sección "IA externa: Ollama, LM Studio y cloud gratis" |
| `DESARROLLO_v15.md` | Metas O11–O14 + §5 "próxima acción" + §8 historial del 2026-11-05 |

---

## 7. Contexto (estado de la BD real y de la noche del 2026-11-04)

- **BD real `data/jobpulse_v15.db`**: **esquema 21**, **705 avisos**, 2478
  requisitos (1145 `rule` + 1333 `source_field`, 2477 con `codigo_canonico`),
  perfil con 48 hechos intactos. Corrida Paso 5 vigente `20261104_231932`:
  calificada 239 · revisar 324 · descartada 89 · datos_insuf 42 ·
  sin_requisitos 11. Viabilidad: aplicar 5 · revisar 2 · no_prioritario 595 ·
  sin_datos 14 · veto 89. `verificar_evidencia.py` exit 0 (130 verificaciones),
  `db check` ok / 0 FK.
- **Respaldo**: `data/backups/pre_limpieza_20261104_211349.db`.
- **Divergencia CLI/UI medida** (simulación sobre copia `%TEMP%\opencode\ui_sim.db`):
  requisitos 1145 (UI) vs 2478 (CLI) · `sin_requisitos` 231 vs 11 ·
  `calificada` 207 vs 239 · `revisar/skill_faltante` 34 vs 238.
- **O5.3**: 43 avisos con descripción <200 chars (35 de ANE).
- **Duplicados dudosos**: 23 grupos (conservador: `quality duplicates`, nunca
  auto-fusionar).
- **`.env` actual**: `IA_PROVEEDOR=custom`, `IA_BASE_URL=http://127.0.0.1:8081/v1`,
  `IA_MODEL=gemma4-e2b-qat` (Gemma local) · `GEMINI_API_KEY` ya existe ·
  `BRAVE_CDP_PORT=9222`. **No hay `IA_MAX_VACANTES`** → sin tope.
- **Trampa ANE (RESUELTA en O12 · 1.5)**: `login_ane.py` cerraba el Brave que
  abrió con `terminate()`/`kill()` → la cookie no persistía → "ANE: sin sesión
  de detalle" y 0 avisos. Ahora el cierre es **ordenado** (`Browser.close` por
  CDP) y `--mantener-abierto` deja el navegador vivo:
  `login_ane.py --mantener-abierto` + `scrape ane --site ane-cr` seguido.
  Falta verificarlo en vivo con **dos barridos seguidos** (O13).

---

## 8. Olas 1 y 2 de O12 — hechas (2026-11-05, al cierre)

### 8.1 Ola 1 — el hueco de raíz

| Paso | Qué quedó | Dónde |
|---|---|---|
| **1.1** | `reananalizar_con_campos_fuente(repository, on_progress, dry_run)`: re-analiza **solo** los avisos con `skills`/`languages` cuyo análisis vigente no los integró; calcula en seco y **solo guarda si cambia** (firma con `codigo_canonico` resuelto) | `analysis_flow.py` |
| **1.1** | Cableado como paso explícito en CLI (`run_enriquecimiento.py` → `iae.reananalizar_tras_ia`), UI clásica (paso 3.5 y tras "Enriquecer") y UI v2 (worker de `ejecutar_paso5`) | `run_enriquecimiento.py`, `ui.py`, `ui_v2/tabs/vacantes.py` |
| **1.2** | `cuenta_analisis_obsoletos` **exacto**: la SQL sola daba 67 candidatos y el re-análisis 0 cambios → confirma en seco (`analisis_refleja_campos`). Badge en ambas UIs + `tools/estado_bd.py` | `analysis_flow.py`, `ui.py`, `ui_v2`, `tools/estado_bd.py` |
| **1.3** | Guarda antes del Paso 5 (`askyesnocancel`): re-analizar y evaluar / evaluar igual / abortar | `ui_v2/tabs/vacantes.py` |
| **1.4** | `jobpulse_v15.evidencia` (`generar_evidencia`, `verificar_evidencia`, `estado_evidencia`, `docs_dir_para`); `generar_evidencia_paso5.py` y `verificar_evidencia.py` son **envoltorios** (mismo CLI y exit codes; el documento generado es **idéntico** byte a byte al anterior). UI v2: botón **"Evidencia"** + indicador "evidencia al día / desactualizada" sin subprocess | `evidencia.py` (NUEVO), scripts, `ui_v2/tabs/vacantes.py`, `i18n.py` |
| **1.5** | `cerrar_brave_ordenado()` (`Browser.close` por CDP) + `login_ane.py --mantener-abierto`; la UI clásica usa el cierre ordenado | `ane_login.py`, `login_ane.py`, `ui.py` |
| **Tests** | `tests/test_evidencia.py` (19) + `tests/test_reanalisis.py` (14) + `tests/test_ane_login.py` (12) | `tests/` |
| **Medición** | Copia de la BD real en `%TEMP%\opencode\medicion_ola1.db`: se borran los 1333 `source_field` (estado "UI antes"), matching → **231 `sin_requisitos`**; re-análisis (638 actualizados, 67 sin cambio, 0 errores) + matching → **11** | (no toca la BD real) |

### 8.2 Ola 2 — orquestador único y botones en la UI v2

| Paso | Qué quedó | Dónde |
|---|---|---|
| **2.1** | `jobpulse_v15.pipeline.ejecutar(repository, etapas=..., progreso=..., evaluar_todo=...)`: cada etapa es **una implementación** (`scraper.ejecutar_barrido`, `analysis_flow.extract_job_analysis`, `ia_enrichment.pase_completo`, `analysis_flow.reananalizar_con_campos_fuente`, `repository.backfill_requirements_canonico`, `matching.ejecutar_paso5`, `jobpulse_v15.evidencia`). Etapa desconocida = `ValueError`; una excepción detiene las siguientes; un resultado con `ok=False` (IA "atascada") NO aborta | `src/jobpulse_v15/pipeline.py` (NUEVO) |
| **2.1** | `run_full_flow.py` deja de tener lógica propia: es un **envoltorio** del orquestador (`--only-scrape`, `--pages`, `--no-notify`, `--evaluar-todo`) | `run_full_flow.py` |
| **2.2** | Botón **"Procesar"** (pestaña "Scraping" de la UI v2): pipeline completo **sin raspar** (análisis → IA → re-análisis → backfill → Paso 5 → evidencia), con log, progreso, cancelación y refresco de las demás pestañas | `ui_v2/tabs/scraping.py`, `ui_v2/app.py` |
| **2.3** | Botón **"Enriquecer IA"**: pase IA + re-análisis; con IA **externa** pide confirmación (el texto sale de la máquina) antes de enviar nada | `ui_v2/tabs/scraping.py` |
| **2.4** | Paso 3.5 del flujo completo de la UI clásica (ya hecho en la Ola 1) | `ui.py` |
| **Tests** | `tests/test_pipeline.py` (**15**): contrato (etapa desconocida, orden, progreso), cada etapa, **paridad UI/CLI sobre dos bases idénticas** (mismo `job_match`), idempotencia del re-análisis, corrida nueva del Paso 5. + 3 tests de UI v2 (botones y confirmación de privacidad) | `tests/` |
| **Humo real** | Sobre una **copia** de la BD real (`%TEMP%\opencode\ola2.db`): `reanalisis + paso5 + evidencia` → mismos números que la CLI (calificada 239 · revisar 324 · descartada 89 · datos_insuf 42 · sin_requisitos 11) y evidencia verificada con 130 citas literales | (no toca la BD real) |

**Nota**: la UI clásica mantiene su flujo (regla del repo: no se toca sin
pedirlo) aunque usa las mismas implementaciones por etapa; migrarla al
orquestador queda como sugerencia 5 de `docs/FLUJO_CLI_VS_UI.md`.

**Seguridad de la evidencia**: `evidencia.docs_dir_para(base)` devuelve
`<repo>/docs` para la base del repo y un `docs` **junto a la base** cuando es
una copia (p. ej. `%TEMP%`): así una corrida sobre una copia nunca pisa el
documento de evidencia del repo.

## 9. Pendiente inmediato

1. **Ola 3 de O13** (`docs/PLAN_MEJORAS.md`): selectores de **LinkedIn**
   (`/jobs/search-results/` con clases ofuscadas) y **Elempleo**
   (`.ee_list-item`) con su test por fetcher · estado `requiere_login` en la
   salud de sitios · verificar ANE con **dos barridos seguidos** (el login ya
   no pierde la cookie: cierre ordenado + `--mantener-abierto`).
2. (Opcional, con permiso del usuario) migrar la **UI clásica** al
   orquestador `pipeline.py`: usa las mismas implementaciones por etapa, pero
   mantiene su propio flujo (regla del repo: la UI clásica no se toca sin
   pedirlo).
3. `educacion_no_confirmada` (31 casos): **NO** actualizar estados hasta que
   una **segunda persona** firme `docs/PASO5_REVISION_PENDIENTES.md`.

---

## 10. Commits de esta sesión

- **HEAD** — `feat(o12): Ola 2 - orquestador único (pipeline.py) y botones
  "Procesar"/"Enriquecer IA" en la UI v2` — `pipeline.py` (NUEVO),
  `run_full_flow.py` como envoltorio, 2 botones en la UI v2, 15 tests nuevos
  + 3 de UI v2.
- `21af318` — `feat(o12): Ola 1 - paridad CLI/UI (re-análisis, evidencia,
  login ANE)` — 20 archivos; +10 tests de ANE, 19 de evidencia, 14 de
  re-análisis. Suite: **1003 passed + 241 subtests**.
- `caf486d` — `feat(ia-externa): Ollama, LM Studio y cloud como alternativa a la
  IA local` (código + 39 tests + `docs/IA_ENRIQUECIMIENTO.md` + `AGENTS.md`).
- `49f3827` — `docs(metas): O11-O14, plan de 5 olas y evidencia de la corrida
  20261104_231932` (`DESARROLLO_v15.md`, `docs/PLAN_MEJORAS.md`, evidencia y
  hoja de revisión regenerada).

`caf486d` y `49f3827` están **pusheados** a `origin/main` (2026-11-05).
El commit de la Ola 1 (HEAD) queda **local**: pendiente de confirmación para
pushear.
