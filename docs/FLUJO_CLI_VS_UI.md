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
