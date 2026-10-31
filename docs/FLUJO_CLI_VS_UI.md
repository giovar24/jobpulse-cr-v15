# Flujo CLI vs. UI — comparación paso a paso

Comparación del flujo ejecutado en la corrida limpia del **2026-10-31**
(scripts `run_full_flow.py` + `run_paso5.py` + evidencia) contra el flujo que
ofrece la **UI** (`src/jobpulse_v15/ui.py`).

Regla que se mantiene: **la UI y el CLI deben compartir el mismo motor**. Lo
que hoy comparten está marcado como *compartido*; lo que no, se señala como
diferencia con su consecuencia.

## 1. Tabla resumen

| Etapa | CLI (lo ejecutado) | UI (lo que hay) | ¿Mismo código? |
|---|---|---|---|
| 1. Barrido | `run_full_flow.py --only-scrape <sitios>` (125 API + 4 browser) | Fuentes → **Ejecutar barrido** (árbol por plataforma; puerto CDP, días ANE, casilla "Flujo completo") | ✅ `scrape_dispatch.construir_llamada` + `IngestionService.fetch_and_import` |
| 2. Análisis por reglas | `run_full_flow.run_analysis()` | **Analizar** / **Analizar sin analizar** / (casilla del barrido) | ✅ `analysis_flow.extract_job_analysis` |
| 3. Enriquecimiento IA | `run_enriquecimiento.py` (servidor local bajo demanda) | **Enriquecer** (diálogo propio) | ✅ `ia_enrichment.pase_completo` + `ia_servidor` |
| 4. Comparar con el perfil | **no lo hace** (imprime "abre la UI") | **Buscar** con filtro de compatibilidad + área | ⚠️ UI usa `repository.compare_jobs_to_candidate_profile` |
| 5. Matching (Paso 5) | `run_paso5.py` → tabla `job_match` (corrida nueva) | **no lo hace** | ❌ solo CLI |
| 6. Evidencia / firma | `generar_evidencia_paso5.py`, `verificar_evidencia.py`, `generar_revision_pendientes.py` | **no lo hace** | ❌ solo CLI |
| 7. Brave/CDP | `run_scrape` lo abre y lo cierra **solo si lo abrió** (O7.2) | igual (barrido, re-login ANE, enriquecimiento) | ✅ `browser_manager.asegurar_brave` |

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

### 2.5 Paso 5 y evidencia (5-6) — solo CLI

- `run_paso5.py` crea una **corrida nueva** (nunca `UPDATE` in-place) y la
  marca `valida=1`, dejando las anteriores en `valida=0`.
- `generar_evidencia_paso5.py` escribe `docs/PASO5_EVIDENCIA_<corrida>.md`
  (el nombre lo decide la corrida vigente, no una fecha fija) con la cita
  literal de cada descarte.
- `verificar_evidencia.py` comprueba que cada frase citada es literal del
  texto de la BD (exit 0 = todo cuadra).
- `generar_revision_pendientes.py` produce la hoja
  `docs/PASO5_REVISION_PENDIENTES.md` (las `educacion_no_confirmada`), que
  **solo firma una segunda persona**.
- La UI no tiene ninguno de los tres: si se quiere el veredicto auditable,
  hay que correr el CLI después de usar la UI.

## 3. Lo que la corrida limpia hizo distinto de la UI

1. **Barrido por lotes de sitios** (129 sitios) en vez de selección
   interactiva en el árbol de fuentes.
2. **Cerró Brave solo si lo abrió** al raspar Elempleo (quedó abierto con CDP
   para el uso normal, como pide O7.2).
3. **Análisis de todos los pendientes** en un paso (552), no de lo visible.
4. **Corrió el Paso 5 y la evidencia**, que la UI no ejecuta.
5. El "PASO 4" del CLI solo imprime un aviso: la comparación con el perfil se
   ve en la UI.

## 4. Recomendaciones (no ejecutadas)

1. **La UI debería poder correr el Paso 5** (botón "Evaluar con el motor") y
   mostrar `estado`/`motivo` en la columna de compatibilidad, para que el
   veredicto de la UI y el del CLI sean el mismo dato (`job_match`).
2. Unificar `compare_jobs_to_candidate_profile` con `matching.evaluar` o
   documentar explícitamente que la compatibilidad de la UI es informativa.
3. Que el CLI imprima al final el resumen `GROUP BY estado` de la corrida
   (hoy hay que leerlo en la BD).
