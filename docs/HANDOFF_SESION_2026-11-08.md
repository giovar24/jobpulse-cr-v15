# Handoff — Sesión 2026-11-08

**TL;DR**:Sesión de **comparación IA nube vs IA local sobre el mismo corpus
fresco**. Se limpió la BD (solo datos de scraping), se hizo un **scrape
nuevo de 736 avisos**, se configuró **Ollama Cloud** (`gemma4:31b`) y se
corró el pipeline completo; luego se restauró el corpus crudo y se corrió lo
mismo con la **IA local** (`gemma4-e2b-qat`). **Ganó la IA local en datos**
(2288 campos llenados vs 1335; 2879 requisitos vs 1948; `sin_requisitos`
121 → **11**; `calificada` 132 → **220**) y **la nube ganó en velocidad**
(8,2 min vs 81,3 min) y consumió **6,7% del free usage** ($0 la local). La
**corrida local quedó vigente** (`20261107_225916`) y la nube se conserva en
`data/backups/post_ia_externa_20261107_205655.db`. De paso: **desplegable de
modelos** en la UI v2 (Configuración → "Listar modelos" llena el combo) y un
**arreglo de aislamiento de tests** (el `.env` real se colaba por
`jobpulse_v15.cli`). Esquema **25** (sin migraciones nuevas).

## 1. Lo hecho

### 1.1 Limpieza + scrape fresco (736 avisos)

- `clean_run.py SI` (destructivo, con OK explícito del usuario): borró
  `jobs`, `job_analysis`, `job_requirements`, `job_field_status`,
  `job_source_records`, `source_runs`, `source_run_sites`, `source_job_memory`,
  `job_match`, `job_area`, `candidate_profile_import_snapshots` (**705/825/
  3103/4125/705/136/136/705/4784/705/0 filas**). **Conservados**: perfil
  (`candidate_profile_facts` 48 + imports 2), `user_job_state` 7,
  `source_platforms` 14, `source_sites` 129, taxonomía (727 conceptos +
  cola 1199), áreas/niveles. Salud de sitios reiniciada.
  Respaldo: `data/backups/pre_clean_20261107_181242.db`.
- Barrido: `run_full_flow.py --only-scrape` → **736 avisos en 129 sitios**
  (68 con avisos, 61 en cero). **elempleo-cr 50** (primer barrido con datos),
  harvie 182, ane 120, indeed 30, workday-* ~400. Los ceros son empresas sin
  vacantes en CR (esperado). **Único aviso sin descripción**:
  `linkedin-4476184789` (429 de LinkedIn en la página 2) → queda sin analizar
  en ambas corridas (no hay texto que analizar).
- `db check` ok, esquema 25.

### 1.2 Ollama Cloud: configuración, precios y prueba de humo

- `.env`: `IA_PROVEEDOR=ollama`, `IA_BASE_URL=https://ollama.com/v1`,
  `IA_MODEL=gemma4:31b`, `IA_API_KEY=<key del usuario>` (el `.env` nunca se
  sube al repo). El preset `ollama` ya apunta a `https://ollama.com/v1`; el
  repo **no** instala el CLI de Ollama ni gestiona keys.
- Prueba de humo: `GET /models` → **26 modelos**; 1 llamada real OK en 0,7 s.
  Ojo: `IA_MODEL=auto` cogía el **primer** modelo de la lista
  (`gpt-oss:120b`) — por eso existe ahora el desplegable (§1.3).
- Precios (ollama.com/pricing, 2026-11-07): **pay as you go = $0 de cuota
  pero NO tokens gratis** (se pagan con créditos); Pro $20/mes = $60 de
  créditos; Max $100 = $300. Por millón de tokens: `nemotron-3-super`
  $0,015 in / $0,60 out (más barato en entrada), `nemotron-3-nano` $0,06 /
  $0,24 (más barato en salida), `gpt-oss:20b` $0,07 / $0,30, **`gemma4`
  $0,14 / $0,40**, `gpt-oss:120b` $0,15 / $0,60. Off-peak (−50 %) fuera de
  12:00–18:00 UTC entre semana y **todo el fin de semana**.

### 1.3 NUEVO: desplegable de modelos en la UI v2

`src/jobpulse_v15/ui_v2/tabs/configuracion.py`:

- El campo "Modelo:" pasó de `Entry` a **`ttk.Combobox` editable** (se puede
  escribir `auto` o elegir del desplegable).
- **"Listar modelos" ahora RELLENA el desplegable** (`configure(values=…)`) y
  además avisa con el recuento; el texto escrito por el usuario **no se
  pisa**. Aplica a **todos** los proveedores (la lista sale del endpoint
  configurado).
- La UI clásica **no se tocó**.

### 1.4 Corrida con IA externa (Ollama Cloud · `gemma4:31b`)

Lanzada desde la **UI v2** (pestaña Scraping → "Procesar" → confirmación de
privacidad), pipeline `pipe_20261107_203636`, job_match `20261107_204525`:

| Etapa | Resultado |
|---|---|
| analisis | 735/736 (1 fallo: el aviso de LinkedIn sin descripción) · 1200 reqs |
| ia | ok · **682 avisos enriquecidos · 1335 campos** (skills 600, work_mode 264, city 142, salary 128, employment_type 130, languages 54, region 17) · no_encontrado 1019 · sin_cambio 298 |
| reanalisis | 397 avisos → +748 reqs |
| paso5 | 735 evaluadas · 2340 reqs · calificada 132 · revisar 348 · **sin_requisitos 121** · descartada 97 · datos_insuf 37 |
| evidencia | OK (136 verificaciones literales) |
| **Consumo** | **6,7% del free usage** (100% → 93,3%) · ≈ 14 corridas completas del mismo tamaño |
| **Duración** | **8,2 min** de pase IA (todo el pipeline ≈ 9 min) |

Respaldo: `data/backups/post_ia_externa_20261107_205655.db`.

### 1.5 Corrida con IA local (`gemma4-e2b-qat`, llama.cpp en 8081)

Se restauró el corpus crudo (`pre_ia_externa_20261107_203459.db` → BD) y se
cambiaron 2 líneas del `.env` (`IA_PROVEEDOR=custom`,
`IA_BASE_URL=http://127.0.0.1:8081/v1`, `IA_MODEL=gemma4-e2b-qat`; la key de
ollama se conservó). Pipeline `pipe_20261107_213706`, job_match
**`20261107_225916`** (VIGENTE):

| Etapa | Resultado |
|---|---|
| analisis | 735/736 · 1200 reqs (idéntico: mismas reglas, mismo corpus) |
| ia | **parcial** · ciclo 1: 500 avisos / 1624 campos · ciclo 2: 100 / 293 · ciclo 3: **0** · COMPLETO: 136 / 371 → **2288 campos** (skills 733, **languages 709**, employment_type 357, city 169, salary 126, region 21, work_mode 173) · 582 críticos + 66 secundarios pendientes |
| reanalisis | **671 avisos → +1679 reqs** |
| paso5 | 735 evaluadas · 2885 reqs · **calificada 220** · revisar 365 · **sin_requisitos 11** · descartada 97 · datos_insuf 42 |
| evidencia | OK (136 verificaciones) · `no_confirmada` **29** → hoja de firma regenerada (566 líneas) |
| **Consumo** | **$0** |
| **Duración** | **81,3 min** de pase IA (todo el pipeline ≈ 82 min) |

Respaldo: `data/backups/post_ia_local_20261107_230622.db`.

### 1.6 Comparativa y curaduría

| Métrica | ☁️ Nube `gemma4:31b` | 💻 Local `gemma4-e2b-qat` |
|---|---|---|
| Campos llenados | 1335 | **2288** (+71%) |
| skills / languages | 600 / **54** | **733 (99,6%) / 709 (96%)** |
| Requisitos en BD | 1948 | **2879** |
| Reqs de idioma (`espanol`/`ingles`) | 41 / 223 | **471 / 345** |
| calificada / sin_requisitos | 132 / 121 | **220 / 11** |
| edu_no_confirmada | 0 | 29 (firma de 2ª persona) |
| Reqs sin `codigo_canonico` | 0 | 0 |
| Tiempo (pase IA) | **8,2 min** | 81,3 min |
| Coste | **6,7% del free** | $0 |

- La **caché de IA separa por proveedor+modelo** (`ia_api._cache_key` incluye
  ambos) → la comparación NO está contaminada.
- Muestra de calidad (local): `languages` = `{"español": "nativo"}` (365),
  `{"inglés": "B2"}` (121)…; `skills` con requisitos reales del aviso.
- `taxonomy curate --apply` sobre la corrida local: cola **1476 → 1198**
  (522 resueltas / 1705 ruido; `veces` deja de estar duplicado ×2: 2314 →
  1259 menciones). **Conceptos sin cambios (727) y requisitos sin cambios
  (2879, 0 sin código)** → **no hizo falta nueva corrida de Paso 5**: la
  vigente `20261107_225916` sigue siendo válida.
- `db check` ok (esquema 25, sin violaciones FK).

## 2. Decisiones

1. **La corrida local queda como vigente**: más datos y coste $0. La nube se
   conserva solo en el respaldo (comparar de nuevo = restaurar ese `.db`).
2. **No se toca el `.env` con secretos** — el repo no gestiona keys; el
   usuario la creó en ollama.com y queda en su `.env` gitignoreado.
3. **Las 29 `educacion_no_confirmada`**: la firma es de una **segunda
   persona**; los estados NO se tocan. Hoja: `docs/PASO5_REVISION_PENDIENTES.md`.
4. **No hay migración nueva**: el esquema sigue en **25**.
5. **Tests aislados del `.env` real** (ver §1.7).

## 3. Estado de la BD real

- Esquema **25** · **736 avisos** (735 con análisis) · **2879 requisitos**
  (0 sin código) · **job_match vigente `20261107_225916`**
  (calificada 220 · revisar 365 · descartada 97 · datos_insuf 42 ·
  sin_requisitos 11) · cola de taxonomía **1198** (1259 menciones) ·
  conceptos **727** · `educacion_no_confirmada` **29** (intocables).
- `.env` **en config local**: `IA_PROVEEDOR=custom`,
  `IA_BASE_URL=http://127.0.0.1:8081/v1`, `IA_MODEL=gemma4-e2b-qat`.
  Para volver a la nube: 2 líneas (`ollama` + `https://ollama.com/v1` +
  `gemma4:31b`).
- Backups: `pre_clean_20261107_181242` · `pre_ia_externa_20261107_203459` ·
  `post_ia_externa_20261107_205655` (nube) · `post_ia_local_20261107_230622`.

## 4. Pendiente inmediato (priorizado)

1. **Ciclos de IA que no rinden**: el ciclo 3 local reintentó 433 avisos con
   **0 llenados** (`failed=355`). Candidata a mejora: cortar el pase cuando un
   ciclo rinde 0 (también la nube dejó 521 "críticos recuperables").
2. **`espanol: nativo` es inferencia**, no texto literal (365 avisos): el
   modelo infiere el idioma del aviso. Inofensivo para el matching (el perfil
   lo cubre), pero a tener en cuenta al auditar.
3. **`linkedin-4476184789`** sin descripción: re-scrape del aviso o dejarlo
   fuera (no es un bug del extractor).
4. **29 `educacion_no_confirmada`**: segunda persona firma la hoja; después,
   corrida nueva de Paso 5.
5. Cola de taxonomía 1198 → siguiente tanda de curación (migración `026`),
   priorizando variantes con ≥2 avisos reales (`demanda_corpus`, no `veces`).
6. **Ola 5** (O4/upsert/embeddings) y **UI clásica → `pipeline.py`** (requiere
   permiso del usuario; la UI clásica está intacta por regla).
7. **Persistencia de tokens**: `IAClient.tokens_in/out` viven solo en memoria;
   `resumen_uso()` no se llama en ningún sitio. Idea: guardarlo en
   `pipeline_etapa.detalle_json` de la etapa `ia` para medir coste real.

## 5. Archivos clave

- `src/jobpulse_v15/ui_v2/tabs/configuracion.py` — desplegable de modelos.
- `tests/test_ui_v2.py` — test del desplegable + aislamiento del `.env`.
- `docs/PASO5_EVIDENCIA_2026-11-07.md` / `docs/PASO5_REVISION_PENDIENTES.md`
  — generados para la corrida `20261107_225916` (29 casos).
- `src/jobpulse_v15/ia_api.py` — `PRESETS` (incluido `ollama` nube) y
  `_cache_key` (proveedor+modelo).
- `src/jobpulse_v15/ia_enrichment.py` — `pase_completo` (ciclos crítico y
  completo) y `enrich_job` (qué cuenta como `failed`).

## 6. Contexto

- Rama `main`, repo `giovar24/jobpulse-cr-v15`. **Commits locales, sin
  push** (falta confirmación del usuario): `a5a43fb`, `317f908`, `a36ca79`,
  `3b11a69`, `177de1c` + los de esta sesión (desplegable de modelos,
  aislamiento de tests, docs).
- **No pushear sin confirmación.**
- La UI clásica (`ui.py`) **no se toca** sin permiso explícito.
