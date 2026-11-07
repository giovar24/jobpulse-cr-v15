# Flujo CLI vs. UI — comparación paso a paso

Comparación del flujo ejecutado en la corrida limpia del **2026-10-31**
(scripts `run_full_flow.py` + `run_paso5.py` + evidencia) contra el flujo que
ofrecen las **dos UIs**: la clásica (`src/jobpulse_v15/ui.py`) y la v2
(`src/jobpulse_v15/ui_v2/`, plana y modular).

Regla que se mantiene: **la UI y el CLI deben compartir el mismo motor**. Lo
que hoy comparten está marcado como *compartido*; lo que no, se señala como
diferencia con su consecuencia.

> **Actualizado 2026-11-04.** Desde entonces: el Paso 5 **SÍ se ejecuta desde
> la UI v2** (pestaña "Vacantes" → botón "Ejecutar Paso 5", que deja la
> corrida PERSISTIDA en `job_match` con `corrida_id` + `valida`, igual que el
> CLI). La UI clásica sigue sin ejecutarlo.

> **Actualizado 2026-11-05 (Ola 1 + Ola 2 de O12).** Desde entonces:
> - la UI v2 tiene **orquestador propio pero el mismo motor**: `jobpulse_v15.pipeline`
>   (etapas `scrape → analisis → ia → reanalisis → backfill → paso5 → evidencia`)
>   es la implementación ÚNICA y la usan la CLI (`run_full_flow.py`) y la UI v2
>   (botones **"Procesar"** y **"Enriquecer IA"** de la pestaña "Scraping");
> - el **re-análisis con los campos de la IA** (`analysis_flow.reananalizar_con_campos_fuente`)
>   es el paso que faltaba: sin él la UI dejaba 231 avisos `sin_requisitos`
>   frente a 11 de la CLI (medido 2026-11-05: **231 → 11**);
> - la **evidencia** ya no es solo CLI: vive en `jobpulse_v15.evidencia` y la UI v2
>   la genera y verifica desde la pestaña "Vacantes" (botón "Evidencia"), sin
>   subprocess; los scripts de la raíz quedaron como envoltorios;
> - la UI clásica mantiene su flujo (está **intacta por regla del repo**) pero
>   ya incluye el re-análisis (paso 3.5) y el cierre ordenado de Brave en el
>   login de ANE.

## 1. Tabla resumen

| Etapa | CLI (lo ejecutado) | UI (lo que hay) | ¿Mismo código? |
|---|---|---|---|
| 1. Barrido | `run_full_flow.py --only-scrape <sitios>` (125 API + 4 browser) | Fuentes → **Ejecutar barrido** (árbol por plataforma; puerto CDP, días ANE, casilla "Flujo completo") | ✅ `scrape_dispatch.construir_llamada` + `IngestionService.fetch_and_import` |
| 2. Análisis por reglas | `run_full_flow.run_analysis()` | **Analizar** / **Analizar sin analizar** / (casilla del barrido) | ✅ `analysis_flow.extract_job_analysis` |
| 3. Enriquecimiento IA | `run_enriquecimiento.py` (servidor local bajo demanda) | **Enriquecer** (diálogo propio) | ✅ `ia_enrichment.pase_completo` + `ia_servidor` |
| 4. Comparar con el perfil | **no lo hace** (imprime "abre la UI") | **Buscar** con filtro de compatibilidad + área | ⚠️ UI usa `repository.compare_jobs_to_candidate_profile` |
| 5. Matching (Paso 5) | `run_paso5.py` → tabla `job_match` (corrida nueva) | UI v2: **Ejecutar Paso 5** → `job_match` (corrida nueva). UI clásica: no | ✅ (v2) `matching.ejecutar_paso5` vía `ui_v2/data/paso5.py` |
| 5.b Re-análisis con los campos de la IA | `enrich requirements-source --apply` (todo) o el paso `reanalisis` del orquestador | UI clásica: paso 3.5 del flujo completo. UI v2: etapa `reanalisis` del pipeline | ✅ `analysis_flow.reananalizar_con_campos_fuente` (incremental: solo lo que no está integrado) |
| 6. Evidencia / firma | `generar_evidencia_paso5.py`, `verificar_evidencia.py`, `generar_revision_pendientes.py` | UI v2: **Evidencia** (genera + verifica, sin subprocess). La hoja de firma sigue siendo CLI | ✅ `jobpulse_v15.evidencia` (los scripts son envoltorios) |
| 7. Brave/CDP | `run_scrape` lo abre y lo cierra **solo si lo abrió** (O7.2) | igual (barrido, re-login ANE, enriquecimiento) | ✅ `browser_manager.asegurar_brave` |
| 8. Filtro "solo con requisitos obligatorios" (O2.2) | `search --solo-requisitos-obligatorios` | UI clásica + UI v2: columna **"Req."** + casilla | ✅ `Repository.search_jobs` (SQL; definición única) |
| 9. Salud de los sitios (O3) | `site list --needs-review`, `site mark-reviewed [--all-needs-review]` | UI clásica: pestaña Fuentes (revisión manual) | ✅ `Repository.list_sites` / `mark_site_reviewed` |

## 2. Etapa por etapa

### 2.1 Barrido (etapa 1) — compartido tras los fixes del 2026-10-31

Ambos llaman al mismo dispatcher:

```python
llamada = construir_llamada(platform_id, fetcher, site, pages=…, port=…, dias=…)
service.fetch_and_import(site_id, llamada, run_kind=platform_id)
```

- `scrape_dispatch.construir_llamada` es la **única** fuente de la firma de
  cada fetcher (async/sync, `pages`, `port`, `dias`). Antes cada llamador
  armaba su propio `lambda` y eso produjo dos bugs reales: el CLI hacía
  `await` a los fetchers sync y no a los async (cinde/procomer reventaban) y
  la UI pasaba `pages=` a tableros que no lo aceptan (TypeError).
- Diferencia menor: el **default de páginas** es 1 en `run_full_flow.py`
  (`--pages`) y 2 en la UI (`pages_default`, más `site_config["pages"]` por
  sitio). En la corrida limpia se usó 1 (el CLI) y `site_config` cuando el
  sitio lo declara.

### 2.2 Análisis por reglas (etapa 2) — compartido

`analysis_flow.extract_job_analysis(repo, job_id)` es la implementación
única: extrae con `RuleBasedExtractor`, resuelve `codigo_canonico` al guardar
y persiste análisis + requisitos + `job_field_status`.

- La UI lo aplica a **la selección** ("Analizar") o a **lo visible sin
  análisis** ("Analizar sin analizar"); el CLI (`run_analysis`) a **todos los
  pendientes** (`review_reason="analysis_missing"`, hasta 10 000).
- Antes esta lógica estaba **triplicada** y la del CLI llamaba a un método
  inexistente (`IngestionService.analyze_job`), así que el análisis del CLI
  fallaba en el 100 % de las vacantes sin que se notara ("Analizadas: 0").

### 2.3 Enriquecimiento IA (etapa 3) — compartido

Mismo `ia_enrichment.pase_completo` (idempotente) y mismo servidor local bajo
demanda: si el servidor ya estaba arriba **no se toca**; si lo levantó el
proceso, se apaga al terminar.

- El CLI lo hace en `run_enriquecimiento.py` (usado por el pipeline y por
  `run_full_flow.py`).
- La UI lo hace en **Enriquecer** y también dentro de la casilla "Flujo
  completo" (que encadena análisis → IA → comparación).
- La regla determinista de `work_mode` (patrones `#LI-*`, "hybrid work
  arrangement", etc.) corre en ambos porque vive dentro del pase.

### 2.4 Comparar con el perfil (etapa 4) — DIFERENTE motor

| | UI | Paso 5 (CLI) |
|---|---|---|
| Función | `repository.compare_jobs_to_candidate_profile` | `matching.py` (`evaluar` / `run_paso5.py`) |
| Persistencia | **ninguna** (se calcula al pintar la grilla) | tabla `job_match`, con `corrida_id` + `valida` |
| Insume | perfil (`candidate_profile_facts`) vs requisitos del análisis | perfil vs requisitos **con `codigo_canonico`** |
| Estados | `matched` / `not_registered` / `below_requirement` / `needs_review` | `calificada` / `revisar_a_mano` / `descartada` / `sin_requisitos` / `datos_insuficientes` / `fuera_de_area` |
| Regla educativa dura | no | sí (título obligatorio ⇒ `descartada`; duda ⇒ `revisar_a_mano`) |
| Filtro por área | filtro de la grilla (cliente) | estado `fuera_de_area` en la BD |
| Auditoría | ninguna | evidencia + hoja de firma por corrida |

Consecuencia práctica: **la UI no descarta ni clasifica con la regla
educativa**; su "Perfil" es una comparación optimista que exige análisis
`complete` (por eso tantas filas caen en `needs_review`). El veredicto
auditable del sistema (con `descartada`/`fuera_de_area` y evidencia) **solo
existe por CLI** hoy.

### 2.5 Paso 5 y evidencia (5-6) — el motor es compartido, la evidencia no

- `run_paso5.py` crea una **corrida nueva** (nunca `UPDATE` in-place) y la
  marca `valida=1`, dejando las anteriores en `valida=0`.
- **Desde 2026-11-03 la UI v2 hace lo mismo**: el botón "Ejecutar Paso 5"
  (pestaña "Vacantes") llama a `matching.ejecutar_paso5` vía
  `ui_v2/data/paso5.py` y deja la corrida **persistida** en `job_match`; la
  casilla "Evaluar todo" = `--evaluar-todo`. La columna "Paso 5" de la tabla
  muestra el estado de esa corrida. La UI clásica sigue sin ejecutarlo.
- `generar_evidencia_paso5.py` escribe `docs/PASO5_EVIDENCIA_<corrida>.md`
  (el nombre lo decide la corrida vigente, no una fecha fija) con la cita
  literal de cada descarte.
- `verificar_evidencia.py` comprueba que cada frase citada es literal del
  texto de la BD (exit 0 = todo cuadra).
- `generar_revision_pendientes.py` produce la hoja
  `docs/PASO5_REVISION_PENDIENTES.md` (las `educacion_no_confirmada`), que
  **solo firma una segunda persona**.
- Ni la UI clásica ni la v2 generaban evidencia: había que correr el CLI
  después de usar la UI. **Desde 2026-11-05 la UI v2 sí** (botón "Evidencia"
  en "Vacantes"): la lógica vive en `jobpulse_v15.evidencia` y los scripts de
  la raíz son envoltorios finos (mismo CLI, mismo exit code).

### 2.6 Filtro de requisitos obligatorios (O2.2) — compartido

La definición es **una sola y vive en SQL**
(`Repository.search_jobs`): `req_obligatorios` = nº de requisitos
`requirement_level='required'` del análisis vigente (`is_current = 1`); los
`preferred` no cuentan y los análisis viejos tampoco.

- CLI: `search --solo-requisitos-obligatorios`; el CSV añade
  `requisitos_obligatorios` al final.
- UI clásica: columna "Req." + casilla "Solo vacantes con requisitos
  obligatorios".
- UI v2: columna "req" + casilla "Solo con requisitos obligatorios"
  (filtro en `ui_v2/data/vacantes.py::filtrar`).
- **Alcance**: la columna cuenta lo que el EXTRACTOR marcó `required`; el
  motor del Paso 5 decide la obligatoriedad por el TEXTO del aviso, así que
  hay avisos `calificada` con "Req." = 0 (122 de 173 en la BD real). "Req." = 0
  = "el extractor no confirmó ningún obligatorio", no "no tiene requisitos".
  Es un triage conservador; el veredicto es la columna "Paso 5".

### 2.7 Salud de los sitios (O3) — compartido

`site list --needs-review` y `site mark-reviewed` (con `--id` o
`--all-needs-review`) operates sobre `source_sites`. La revisión manual
**reinicia el rache de ceros** (`consecutive_zero_runs = 0`): es el acuse de
recibo del sitio; sin ese reset el sitio volvía a marcarse en la siguiente
corrida con 0. `clean_run.py` reinicia la salud de todos los sitios (la
salud se deriva de las corridas, y `clean_run` borra las corridas).

## 3. Lo que la corrida limpia hizo distinto de la UI

1. **Barrido por lotes de sitios** (129 sitios) en vez de selección
   interactiva en el árbol de fuentes.
2. **Cerró Brave solo si lo abrió** al raspar Elempleo (quedó abierto con CDP
   para el uso normal, como pide O7.2).
3. **Análisis de todos los pendientes** en un paso (552), no de lo visible.
4. **Corrió el Paso 5 y la evidencia**, que la UI no ejecuta.
5. El "PASO 4" del CLI solo imprime un aviso: la comparación con el perfil se
   ve en la UI.

## 4. Recomendaciones

1. ~~**La UI debería poder correr el Paso 5**~~ → **hecho en la UI v2**
   (2026-11-03): botón "Ejecutar Paso 5" en la pestaña "Vacantes", corrida
   persistida en `job_match`. Falta el equivalente en la UI clásica.
2. Unificar `compare_jobs_to_candidate_profile` con `matching.evaluar` o
   documentar explícitamente que la compatibilidad de la UI es informativa.
   (La UI v2 ya muestra **ambos**: el score ATS, que es un *ranking*, y el
   estado del Paso 5, que es el veredicto auditable.)
3. Que el CLI imprima al final el resumen `GROUP BY estado` de la corrida
   (hoy hay que leerlo en la BD).
4. ~~La evidencia y la hoja de firma siguen siendo solo CLI~~ → **la evidencia
   ya está en la UI v2** (2026-11-05, botón "Evidencia"): se genera y verifica
   desde `jobpulse_v15.evidencia`, sin subprocess. La **hoja de firma**
   (`generar_revision_pendientes.py`) sigue siendo CLI a propósito: la firma
   es de una segunda persona.
5. **Migrar la UI clásica al orquestador** `jobpulse_v15.pipeline`: hoy mantiene
   su propio flujo (por regla del repo, la UI clásica no se toca sin pedirlo),
   aunque usa las mismas implementaciones por etapa (análisis, IA, re-análisis,
   backfill). Con eso, CLI y UI clásica darían el mismo `job_match` por
   construcción, no por convención.

---

## 5. El flujo de la corrida real (anotado)

> **Anotado 2026-11-06** en la corrida real sobre la BD real (705 avisos), con
> el objetivo de medir si el pase de IA sobre los **datos crudos que ya
> existen** mejora la extracción de código canónico.

### 5.1 El comando

```powershell
$py = ".\.venv\Scripts\python.exe"

# 0) Respaldo ANTES de tocar la BD real (no migra el esquema)
& $py -X utf8 -m jobpulse_v15 backup --output data\backups\pre_ia_<stamp>.db

# 1) La corrida: el ORQUESTADOR (implementación única de cada etapa)
& $py -X utf8 -c "from jobpulse_v15 import pipeline; ..."
#   pipeline.ejecutar(repo, etapas=('analisis','ia','reanalisis','backfill',
#                                    'paso5','evidencia'), db_path=..., progreso=print)
```

El mismo orquestador es el que usa la CLI de producto (`run_full_flow.py`) y
la UI v2 (botones **"Procesar"** / **"Enriquecer IA"**). La **única**
diferencia de esta corrida es que **no** empieza por `scrape`: el corpus se
queda en 705 avisos, porque lo que se mide es la mejora de la **extracción**
sobre el texto crudo existente (la corrida en limpio, con barrido, queda
para otro día).

### 5.2 Etapa por etapa (qué corre y qué escribe)

| # | Etapa | Implementación que corre | Qué escribe | Idempotente |
|---|---|---|---|---|
| 1 | `analisis` | `analysis_flow.extract_job_analysis` (uno por aviso pendiente) | `job_analysis` (vigente) · `job_requirements` · `job_field_status` · cola `concepto_no_normalizado` | Sí (solo lo que falta) |
| 2 | `ia` | `ia_enrichment.pase_completo` (servidor local **bajo demanda**) | `jobs.city/region/work_mode/employment_type/salary_*/skills/languages` | Sí (solo campos vacíos) |
| 3 | `reanalisis` | `analysis_flow.reananalizar_con_campos_fuente` + `reananalizar_texto_cambiado` | `job_analysis` nuevo con requisitos `origin='source_field'` | Sí (solo si el análisis cambia) |
| 4 | `backfill` | `repository.backfill_requirements_canonico` | `job_requirements.codigo_canonico` (**solo NULL**) | Sí |
| 5 | `paso5` | `matching.ejecutar_paso5` | `job_match` (**corrida nueva**; la anterior queda `valida=0`) | No (por diseño: cada regla ⇒ corrida nueva) |
| 6 | `evidencia` | `jobpulse_v15.evidencia` (genera + verifica) | `docs/PASO5_EVIDENCIA_<fecha>.md` | Sí |

Propiedades del flujo que no son negociables:

- **El orden importa**: sin (3) los campos de la IA no son requisitos
  comparables (el aviso queda `sin_requisitos`); sin (4) los requisitos
  **nuevos** no tienen código (el motor los **ignora en silencio**).
- **Cada etapa deja su métrica** en `pipeline_etapa` (Ola 4.3): duración,
  avisos, requisitos y errores → `… pipeline etapas`.
- **El re-análisis es incremental**: solo rehace los avisos cuyo análisis
  vigente **no** integró `jobs.skills`/`languages`, o cuyo texto cambió
  (`text_hash` descuadrado). Tras cambiar la **taxonomía** hay que re-analizar
  **todos** (el incremental no los alcanza).
- **La evidencia es la puerta**: `verificar_evidencia` comprueba que cada
  frase citada es **literal** del texto de la BD (exit 0 = todo cuadra).

### 5.3 La corrida del 2026-11-06 (medida)

| Etapa | Duración | Avisos | Requisitos | Errores |
|---|---|---|---|---|
| `analisis` | 100 ms | 0 | 0 | 0 |
| `ia` | **606 s** | 25 (enriquecidos) | 0 | **0** (1051 "no mencionados") |
| `reanalisis` | 746 ms | 1 | 1 | 0 |
| `backfill` | 2 ms | 0 | 0 | 0 |
| `paso5` | 526 ms | 705 | 2867 | 0 |
| `evidencia` | 755 ms | 705 | 0 | 0 |

**Ojo con la etapa `ia`**: el pase reports `failed=1051`, pero eso **NO** son
errores: es "el modelo no encontró el campo" (**el aviso no lo dice**). Los
errores reales se loguean como `IA extract {campo} fallo tras 3 intentos` y en
esta corrida hubo **cero**. La instrumentación de la Ola 4.3 se corrigió para
no contarlos como errores (el `detalle_json` los lleva como `no_encontrado`).

---

## 6. Comparación con el flujo de la UI (sin cambiar la UI)

Comparado **después** de la corrida, contra el código de las dos UIs.

### 6.1 Etapas: mi corrida vs. cada interfaz

| Etapa | Mi corrida (orquestador) | CLI `run_full_flow.py` | UI v2 "Procesar" | UI v2 "Enriquecer IA" | UI clásica |
|---|---|---|---|---|---|
| `scrape` | — (a propósito) | ✅ primero | — (botón aparte) | — | ✅ propio |
| `analisis` | ✅ | ✅ | ✅ | — | ✅ (selección o "sin analizar") |
| `ia` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `reanalisis` | ✅ | ✅ | ✅ | ✅ | ✅ (paso 3.5) |
| `backfill` | ✅ | ✅ | ✅ | — | ❌ **no** |
| `paso5` | ✅ | ✅ | ✅ | — | ❌ **no** |
| `evidencia` | ✅ | ✅ | ✅ | — | ❌ **no** |

### 6.2 Qué es literalmente el MISMO código

| Pieza | Compartida por |
|---|---|
| `analysis_flow.extract_job_analysis` | mi corrida · CLI · UI v2 · UI clásica |
| `ia_enrichment.pase_completo` + `ia_servidor` | mi corrida · CLI · UI v2 · UI clásica |
| `analysis_flow.reananalizar_con_campos_fuente` | mi corrida · CLI · UI v2 · UI clásica |
| `repository.backfill_requirements_canonico` | mi corrida · CLI · UI v2 (**no** UI clásica) |
| `matching.ejecutar_paso5` | mi corrida · CLI · UI v2 (**no** UI clásica) |
| `jobpulse_v15.evidencia` | mi corrida · CLI · UI v2 (**no** UI clásica) |

**Consecuencia**: mi corrida y el botón **"Procesar"** de la UI v2 ejecutan
**exactamente las mismas 6 etapas, en el mismo orden, con el mismo
orquestador** → la paridad es **por construcción**, no por convención. La
única diferencia es el `scrape` (mi corrida no barre; "Procesar" tampoco: en
la UI v2 el barrido es otro botón, y en la CLI es la primera etapa).

### 6.3 Las diferencias que SÍ importan

| # | Diferencia | Consecuencia |
|---|---|---|
| 1 | La UI clásica **no** hace `backfill` | Los requisitos nuevos (nacidos de una taxonomía curada) quedan **sin `codigo_canonico`** → el motor los **ignora en silencio** → el aviso se ve más compatible de lo que es |
| 2 | La UI clásica **no** corre el Paso 5 | No hay veredicto auditable (`calificada`/`revisar_a_mano`/`descartada`/`fuera_de_area`): su "Perfil" es una comparación informativa |
| 3 | La UI clásica **no** genera evidencia | Las frases literales y la hoja de firma quedan solo por CLI/UI v2 |
| 4 | La UI clásica analiza **lo visible** (o lo pendiente con `limit=10000`, pero en su propio hilo) | Mismo resultado, distinto alcance; el orquestador usa `review_reason="analysis_missing"` |
| 5 | La UI v2 "Enriquecer IA" solo hace `ia` + `reanalisis` | No deja el matching al día: hay que luego correr "Procesar" (o el Paso 5) |

### 6.4 Lo que NO se cambió (a propósito)

- **La UI clásica no se tocó** (regla del repo: intacta sin pedido explícito).
- El **filtro de la UI** (`fuera_de_area` en el motor) y los umbrales
  (0,60 / 0,80) tampoco.
- La **hoja de firma** sigue siendo CLI (`generar_revision_pendientes.py`):
  la firma es de una **segunda persona**.
