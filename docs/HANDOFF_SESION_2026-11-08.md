# Handoff — Sesión 2026-11-08

**TL;DR (turno 4)**: se cerró el **punto 5** del backlog (Ola 5). La **UI
clásica** ya no tiene flujo propio: delega al **orquestador**
`pipeline.ejecutar` (`analisis → ia → reanalisis → backfill → paso5 →
evidencia` en el flujo completo; `ia + reanalisis` en la ventana
"Enriquecer IA") y se borró su implementación duplicada del re-análisis
(`_reananalizar_con_campos_fuente`). Con eso **CLI, UI v2 y UI clásica dan el
mismo `job_match` por construcción**. El **alcance real de 5.1 y 5.2** se
midió: **5.1 ya estaba hecho** (735 analyses para 735 avisos: cero
inflación del historial) y **5.2 ya estaba en el motor** (el componente
semántico con peso 0,15): lo que faltaba era el **valor por defecto**, y la
medición sobre 736 avisos mostró **0 cambios de banda** (solo cambia el
ORDEN), así que ahora la CLI lo usa por defecto **sin custo extra**
(solo si el modelo y la cache ya están en disco; `--semantica` lo fuerza,
`--sin-semantica` lo quita). Los **5 puntos del backlog están cerrados**.

**TL;DR (turno 3)**: se ejecutó el **punto 3** del backlog (la **firma** de los
29 `educacion_no_confirmada`). La firma de la **segunda persona** (el usuario,
2026-11-08) queda **registrada en la base** (migración **`027`**, esquema
**27**): tabla `job_match_decision`, anclada al **sha256 del texto exacto** que
se leyó (si el aviso se re-raspa, la firma deja de aplicar y el caso vuelve a
la hoja). **25 "no bloqueo"** → `revisar_a_mano / educacion_no_cumple`; **2
"bloqueo real"** → `descartada / titulo_universitario_requerido`; **2 "dudoso"**
siguen **ABIERTOS** (dependen de 2 decisiones de negocio sin tomar).
Corrida nueva **`20261108_175932`**: `educacion_no_confirmada` **29 → 2**,
`descartada` 97 → **99**, `revisar` 389 → **391**. Evidencia OK (**140
verificaciones literales**, incluidas las 29 firmas con su cita literal y su
efecto). CLI nuevo: `jobpulse-v15 decision list|sign`. Puntos **1, 2 y 4** ya
estaban hechos (turno 2); el **5** sigue pendiente.

**TL;DR (turno 2)**: se ejecutaron los **puntos 1, 2 y 4** del backlog de la
sesión. **Punto 1** (ciclos de IA inútiles): los avisos que el modelo no
puede enriquecer ya **no se reintentan** (el ciclo 3 local reintentaba 433
avisos y llenaba 0). **Punto 4** (persistir tokens): el consumo real
(llamadas + tokens) queda **guardado** en `pipeline_etapa.detalle_json`
(medido: 123 llamadas, 52 827 in / 3 901 out). **Punto 2** (curaduría de la
taxonomía, **tanda 3**): migración **`026`** (esquema **26**) que cura las
**57 variantes de la cola que ≥2 avisos piden** → **+48 conceptos**,
**+19 códigos**, **+77 requisitos comparables** (2879 → **2956**, 0 sin
código), cola **1198 → 1150**, y una **corrida nueva de Paso 5**
(`20261108_131343`): `calificada` 220 → **202**, `revisar` 365 → **389** (el
motor ve más requisitos), `sin_requisitos` 11 (igual), y los **29
`educacion_no_confirmada` intactos**. Puntos **3** (firma de los 29) y **5**
(Ola 5: upsert + embeddings, y UI clásica → `pipeline.py`) siguen pendientes.

**TL;DR (turno 1)**: Sesión de **comparación IA nube vs IA local sobre el mismo corpus
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

### 1.7 Turno 2 · PUNTO 1: los ciclos de IA que no rinden se cortan

`src/jobpulse_v15/ia_enrichment.py`:

- `run_ia_enrichment(..., exclude_ids: Set[str] | None)` salta los ids
  excluidos **antes de elegir lote** (ni una llamada de IA).
- `run_ia_enrichment` devuelve **`ids_estancados`**: los avisos que no
  rindieron (`failed` = el modelo no halló el campo; `skipped` = devolvió lo
  que ya estaba). Antes el ciclo 3 de la corrida local reintentó **433 avisos
  y llenó 0** (el modelo es determinista a temp 0.1).
- `pase_completo` acumula los estancados y los excluye del **siguiente ciclo
  y del pase completo**.
- Sin cambio de esquema. Tests: `tests/test_ia_enrichment.py` (34 + 36
  subtests) y `tests/test_ia_externa.py`.

### 1.8 Turno 2 · PUNTO 4: el consumo real de tokens queda guardado

- `pase_completo` usa **un único cliente IA para todo el pase** (así los
  tokens se acumulan), lo **cierra al terminar** (pase lo que pase) y
  devuelve `resumen["uso"] = {llamadas, tokens_in, tokens_out}`.
- `pipeline_metricas.detalle_etapa("ia")` lo guarda en
  `pipeline_etapa.detalle_json` (clave `uso`) → consultable con
  `jobpulse-v15 pipeline etapas --json`.
- **Medido en COPIA** (corpus crudo + caché IA nueva + `IA_MAX_VACANTES=25`,
  IA local): **123 llamadas · 52 827 tokens in · 3 901 tokens out**; 25/25
  avisos enriquecidos, 0 errores. Sin pérdida de datos: solo 2 de 25 avisos
  cambian de skills y es por el modelo no determinista (no por el cambio).

### 1.9 Turno 2 · PUNTO 2: curaduría de la taxonomía, TANDA 3 (migración 026)

Auditoría del corpus real (`taxonomia.demanda_corpus`, no el contador `veces`
de la cola): de las **1198** variantes pendientes, **57** las piden **≥2
avisos** → esa es la tanda.

- **25 alias** a conceptos que ya existían (`interpretacion de planos` /
  `interpretacion de diagramas` / `planos` / `drawings` → `lectura-planos`;
  `diagnostico` / `investigate technical problems` / `network diagnostics` →
  `troubleshooting`; `business analysis` → `analisis-negocio`; `invoicing` →
  `facturacion`; `collections` → `cuentas-por-cobrar`; `supply chain` →
  `abastecimiento`; `timelines` → `project-planning`; `seleccion` →
  `reclutamiento`; `sap basico` → `sap`; `iis` / `web server technologies` →
  `servidores`; `digitacion` → `data-entry`; `destrezas electricas` →
  `electricidad`; `destrezas mecanicas` → `mecanica-industrial`;
  `almacenamiento de alimentos` / `conservacion de alimentos` →
  `manipulacion-alimentos`; `protocolos de higiene` →
  `seguridad-alimentaria`; `phone` / `phone calls` /
  `llamadas salientes outbound` → `atencion-al-cliente`).
- **23 variantes con 19 códigos nuevos**: `negociacion`, `cierre-ventas`,
  `marketing-automation`, `evaluacion-riesgos`, `order-to-cash`,
  `containerization`, `ich`, `onq`, `reservaciones`, `cocteleria`,
  `preparacion-alimentos`, `tecnicas-coccion`, `tecnicas-montaje`, `moto`,
  `vehiculo-propio`, `ventaneria`, `alarma`, `paneles-control`,
  `tarjetas-acceso`.
- **9 se dejan en la cola a propósito** (con el motivo en la cabecera de la
  migración): `website`, `data driven settings`, `upgrades`, `four seasons`,
  `explore products`, `providing product information`, `buenas practicas`,
  `asesor`, `liviano`.

**Medición (copia → real, IDÉNTICA)**:

| Métrica | Antes | Después |
|---|---|---|
| Esquema | 25 | **26** |
| Cola de taxonomía | 1198 | **1150** (−48) |
| Conceptos / códigos | 727 / 317 | **775 / 336** (+48 / +19) |
| Requisitos (0 sin código) | 2879 | **2956** (+77) |
| `calificada` / `revisar` | 220 / 365 | **202 / 389** |
| `datos_insuf` / `descartada` / `sin_requisitos` | 42 / 97 / 11 | 36 / 97 / 11 |
| `educacion_no_confirmada` | 29 | **29 (intacto)** |

**Aplicación a la BD real**: respaldo
`data/backups/pre_tanda3_20261108_131212.db` → apertura (aplica la **026**) →
`enrich requirements-source --apply` (736 avisos, 1756 requisitos fuente; 1
aviso sin descripción: `linkedin-4476184789`) → `enrich requirements-canonico
--apply` (0) → `taxonomy curate --apply` (1202 → **1150**) → corrida
**`20261108_131343`** → evidencia `docs/PASO5_EVIDENCIA_2026-11-08.md` OK
(**136 verificaciones literales**, `no_confirmada=29`) → hoja de firma
regenerada (29 casos) → `db check` ok (esquema 26, 0 FK).

El −18 de `calificada` es el efecto esperado: los +77 requisitos recién
visibles hacen que avisos que parecían cubiertos del todo muestren un
`required` real que faltaba (tope `revisar`). El motor ve más requisitos, no
peor matching.

### 1.10 Turno 3 · PUNTO 3: la firma de los 29 `educacion_no_confirmada`

La firma la hizo una **segunda persona** (el usuario, 2026-11-08) leyendo la
hoja `docs/PASO5_REVISION_PENDIENTES.md` (corrida `20261108_131343`).

**Qué se construyó** (nuevo):

- `src/jobpulse_v15/decisiones.py` — módulo canónico: dimensiones/veredictos
  válidos, el **ancla** (`hash_aviso` = sha256 de `requirements_raw` +
  `description_raw`, el MISMO texto que leen el motor y la hoja), persistencia
  (`guardar_decision`, `listar_decisiones`, `decision_vigente`) y la hoja de
  firma (`cargar_firma`, `aplicar_firma`).
- `src/jobpulse_v15/migrations/027_job_match_decision.sql` — tabla
  `job_match_decision` (`job_id`, `dimension`, `veredicto`, `criterio`,
  `revisor`, `fecha`, `text_hash`, `corrida_id`), `UNIQUE (job_id, dimension,
  text_hash)` y FK a `jobs` con `ON DELETE CASCADE`. **No toca `job_match`**:
  los estados los produce una **corrida nueva**.
- `src/jobpulse_v15/matching.py` — el evaluador carga las firmas y las aplica
  **SOLO cuando el motor no pudo decidir** (`no_confirmado`): `bloqueo_real` →
  `bloqueante` (`descartada`), `no_bloqueo` → `faltante` (`revisar_a_mano`),
  `dudoso` → sin cambio. **Una firma NUNCA pisa un veredicto del motor.**
- `src/jobpulse_v15/viabilidad.py` — el veto educativo respeta la firma (los
  2 "bloqueo real" pasan a banda `veto`).
- `src/jobpulse_v15/cli.py` — `jobpulse-v15 decision list` y
  `jobpulse-v15 decision sign --file <firma.json> [--dry-run]`.
- `docs/PASO5_FIRMA_EDUCACION.json` — la hoja de firma (29 decisiones con su
  `text_hash`); es la entrada auditable del CLI.
- `src/jobpulse_v15/evidencia.py` — sección 6 nueva (las 29 firmas con su
  veredicto, su efecto en la corrida y el criterio firmado) y verificación
  **D** (cada cita `«...»` del criterio tiene que ser literal del texto de la
  BD **y** el estado de la corrida tiene que concordar con el veredicto).
- `generar_revision_pendientes.py` — la hoja muestra ahora el veredicto, el
  criterio, el revisor y la fecha de los casos ya firmados, y lista aparte
  las **decisiones de negocio pendientes**.

**La firma (29 casos)**:

| grupo | veredicto | n | efecto |
|---|---|---|---|
| A (vía alternativa explícita: "or equivalent experience" y compañía) | `no_bloqueo` | 25 | `revisar_a_mano / educacion_no_cumple` |
| B `workday-Principal-Engineer--Quality_Req-51750` | `bloqueo_real` | 1 | `descartada / titulo_universitario_requerido` |
| E `workday-SharePoint-Application-Developer_R55630-1` | `bloqueo_real` | 1 | `descartada / titulo_universitario_requerido` |
| C `workday-Credit---Collections-Specialist--2_R232432` | `dudoso` | 1 | sigue `educacion_no_confirmada` |
| D `workday-Production-Supervisor-I_31163511` | `dudoso` | 1 | sigue `educacion_no_confirmada` |

**Medición (copia → real, IDÉNTICA)**: en la copia, el motor **sin** firma
reproduce la corrida vigente **exactamente** (0 diferencias) → la firma es lo
único que cambia. 27 avisos cambian de estado, **0 cambian de cobertura o
puntaje** (solo `nc_count` 1 → 0), así que **ninguno cae a
`datos_insuficientes`**. En **viabilidad**: 12 avisos `no_prioritario` →
`revisar` (tope duro: requisito `required` faltante) y 2 → `veto`.

**Aplicación a la BD real**: respaldo
`data/backups/pre_firma_educacion_20261108_175903.db` → apertura (aplica la
**027**) → `decision sign --file docs/PASO5_FIRMA_EDUCACION.json` (29
aplicadas, 0 con texto cambiado) → corrida **`20261108_175932`** → evidencia
`docs/PASO5_EVIDENCIA_2026-11-08.md` OK (**140 verificaciones literales**) →
hoja regenerada (**2 casos abiertos**) → `db check` ok (esquema 27, 0 FK).

**Reglas que se respetan**: la firma es de una segunda persona; los estados
solo cambian con una **corrida nueva** (nunca `UPDATE` de la anterior); los
umbrales (cobertura 0.60 / puntaje 0.80) **no se tocaron**; una firma anclada
a un texto viejo **no** se aplica a un texto nuevo.

### 1.11 Turno 4 · PUNTO 5: la UI clásica al orquestador + el alcance real de 5.1/5.2

Con **permiso explícito del usuario** (la UI clásica era "intacta por
regla"), se cerró el último punto del backlog.

**a) La UI clásica delega en `pipeline.ejecutar`** — era la **tercera**
implementación del flujo (su propio bucle de análisis, su propio
`asyncio.run(pase_completo)` y su propio re-análisis
`_reananalizar_con_campos_fuente`):

| ventana de la UI clásica | antes | ahora |
|---|---|---|
| flujo completo (casilla del barrido) | análisis → IA → re-análisis → backfill → **sin** Paso 5, **sin** evidencia | `pipeline.ejecutar("analisis","ia","reanalisis","backfill","paso5","evidencia")` |
| "Enriquecimiento IA" | `asyncio.run(pase_completo)` + arranque/parada manual del servidor IA | `pipeline.ejecutar("ia","reanalisis")` |

Se **borró** el método muerto `_reananalizar_con_campos_fuente`. La
**comparación con el perfil** (paso 4, el filtro de la grilla) **NO** cambia:
sigue siendo `repository.compare_jobs_to_candidate_profile`, que es
**informativa**; el veredicto auditable es el del Paso 5 (que ahora también
corre desde la UI clásica, siempre como **corrida nueva**).

**b) 5.1 (upsert de `save_analysis`) — ya estaba hecho**, medido en la BD
real: `job_analysis` = **735 filas** para **735 avisos** (1 análisis por
aviso, **0** duplicados `(job_id, text_hash, versión)`). El motivo está en el
código: `Repository.save_analysis` **reutiliza el `analysis_id`** cuando el
aviso, el `text_hash` y la versión coinciden, y
`analysis_flow.reananalizar_con_campos_fuente` **solo guarda si el resultado
cambia**. → **cero cambios de código**.

**c) 5.2 (semántica en viabilidad) — el motor ya la usaba; faltaba el valor
por defecto.** Medido sobre los **736 avisos** (solo lectura):

| | SIN semántica | CON semántica |
|---|---|---|
| bandas | aplicar 4 · revisar 16 · no_prioritario 602 · sin_datos 15 · veto 99 | **idénticas** |
| cambios de BANDA | — | **0 de 736** |
| delta del `ajuste` (622 con puntaje) | — | media **3,82** · máx **10,0** · 187 >5 puntos |
| cambios en el ORDEN (top 50) | — | **45 de 50** |

La semántica **ordena, no veredicta** (peso `PESO_SEMANTICA = 0,15`, sin
tocar). Cambios:

- `search_engine.modelo_embeddings_disponible()` — ¿el modelo ya está en la
  cache local de Hugging Face?
- `search_engine.embeddings_cache_cubren(job_ids)` — ¿la cache de embeddings
  cubre el corpus?
- `jobpulse-v15 viabilidad list|top`: el componente semántico es el
  **PREDETERMINADO**, pero **solo si no cuesta trabajo extra** (modelo local
  **y** cache completa); si falta uno, avisa por **stderr** (la salida es
  JSON) y sigue sin él. `--semantica` lo **fuerza**, `--sin-semantica` lo
  quita; los dos a la vez → error de uso (exit 2).

**d) La BD real NO se tocó en el turno 4**: `db check` ok (esquema **27**,
`integrity_check` ok, 0 violaciones FK); la corrida vigente sigue siendo
**`20261108_175932`**.

**Tests**: `tests/test_ui.py::TestUiClasicaDelegaAlOrquestador` (5),
`tests/test_cli_viabilidad.py::TestCliViabilidadSemantica` (6),
`tests/test_caches.py::TestDisponibilidadDeEmbeddings` (5).

## 2. Decisiones

1. **La corrida local queda como vigente**: más datos y coste $0. La nube se
   conserva solo en el respaldo (comparar de nuevo = restaurar ese `.db`).
2. **No se toca el `.env` con secretos** — el repo no gestiona keys; el
   usuario la creó en ollama.com y queda en su `.env` gitignoreado.
3. **Las 29 `educacion_no_confirmada`**: la firma es de una **segunda
   persona**; los estados NO se tocan. Hoja: `docs/PASO5_REVISION_PENDIENTES.md`.
   (Turno 2: la tanda 3 **no las movió**: siguen siendo 29.)
4. **Esquema 26** (turno 2): la curaduría de la tanda 3 es una **migración
   de datos** (`026_taxonomia_curacion_tanda_3.sql`), no un `UPDATE` a mano.
5. **Tests aislados del `.env` real** (ver §1.7 del turno 1).
6. **Tanda 3 medida por `demanda_corpus`** (nº de avisos que piden la
   variante), no por `veces` de la cola: `veces` se reescribe en cada
   curación y ya no distingue "un aviso" de "varios".
7. **Un aviso estancado no se reintenta** (punto 1): el modelo es
   determinista a temp 0.1; reintentar es trabajo tirado. Los ids se
   acumulan solo durante el pase (no se guardan en la BD).
8. **Turno 3 · la firma se APLICA, pero solo donde el motor no pudo decidir**
   (punto 3): `bloqueo_real` → `descartada`, `no_bloqueo` → `faltante`
   (nunca `descartada`), `dudoso` → el caso sigue abierto. Una firma
   **nunca** pisa un veredicto que el motor ya dio (texto confirmado,
   perfil que cumple, etc.).
9. **Turno 3 · la firma está anclada al texto**: `text_hash` = sha256 de
   `requirements_raw` + `description_raw`. Si el aviso se re-raspa y su texto
   cambia, la firma **deja de aplicar** y el caso vuelve a la hoja. Es lo que
   impide que una firma vieja se aplique a un texto que nadie leyó.
10. **Turno 3 · "no bloqueo" NO es "cumple"**: el título no bloquea, pero el
    perfil no lo tiene → el requisito queda `faltante` y la vacante a
    `revisar_a_mano` (y en viabilidad, banda máxima `revisar`).
11. **Turno 4 · la UI clásica delega en el orquestador** (punto 5, con
    permiso explícito del usuario): su flujo completo corre las **mismas 6
    etapas** que el botón "Procesar" de la UI v2, y su ventana de
    enriquecimiento las mismas 2 (`ia`, `reanalisis`). Su **comparación con
    el perfil** (paso 4) **no** cambia: es informativa; el veredicto
    auditable es el del Paso 5, que ahora también corre desde la UI clásica.
12. **Turno 4 · la semántica en viabilidad NO cambia ninguna banda**
    (medido sobre 736 avisos): 0 avisos cambian de banda; lo que cambia es
    el **orden** (45 de los 50 primeros se reordenan). Por eso se puede
    activar por defecto **sin tocar umbrales** (los del Paso 5 siguen
    congelados y el peso `PESO_SEMANTICA = 0,15` se deja como está).
13. **Turno 4 · la semántica solo se activa si no cuesta trabajo extra**: el
    modelo tiene que estar en la cache local de Hugging Face **y** la cache
    de embeddings tiene que cubrir el corpus. Un comando de solo lectura no
    descarga ~500 MB ni re-vectoriza el corpus sin avisar (avisa por
    **stderr**, porque la salida es JSON).

## 3. Estado de la BD real

- Esquema **27** · **736 avisos** (735 con análisis) · **2956 requisitos**
  (0 sin código) · **job_match vigente `20261108_175932`**
  (calificada 202 · revisar 391 · descartada 99 · datos_insuf 36 ·
  sin_requisitos 11) · cola de taxonomía **1150** (1160 menciones) ·
  conceptos **775** (336 códigos) · `educacion_no_confirmada` **2**
  (las dos firmadas "dudoso") · **29 decisiones firmadas** en
  `job_match_decision` (25 `no_bloqueo` · 2 `bloqueo_real` · 2 `dudoso`).
- `.env` **en config local**: `IA_PROVEEDOR=custom`,
  `IA_BASE_URL=http://127.0.0.1:8081/v1`, `IA_MODEL=gemma4-e2b-qat`.
  Para volver a la nube: 2 líneas (`ollama` + `https://ollama.com/v1` +
  `gemma4:31b`).
- Backups: `pre_clean_20261107_181242` · `pre_ia_externa_20261107_203459` ·
  `post_ia_externa_20261107_205655` (nube) · `post_ia_local_20261107_230622` ·
  `pre_tanda3_20261108_131212` · **`pre_firma_educacion_20261108_175903`**
  (antes de la migración 027).

## 4. Pendiente inmediato (priorizado)

1. ~~**PUNTO 5 · Ola 5**~~ → **CERRADO (turno 4)**: la UI clásica delega en
   el orquestador (`pipeline.ejecutar`), 5.1 **ya estaba hecho** (upsert real
   en `save_analysis`, 0 inflación del historial) y 5.2 **ya estaba en el
   motor** (lo que faltaba era el valor por defecto, ya activado sin costo
   extra). Ver §1.11 y `docs/PLAN_MEJORAS.md` §5.8-§5.9.
2. **2 decisiones de negocio bloquean 2 avisos** (firmados "dudoso"):
   (#2) si 2 años de educación superior en CR cuentan como universitario
   (fuente CONESUP) — `workday-Credit---Collections-Specialist--2_R232432`;
   (#3) si un bachillerato parcial del 80 % cuenta como requisito universitario
   cumplido — `workday-Production-Supervisor-I_31163511`. Hay que decidirlas
   **con una fuente**, no por impulso; hasta entonces siguen en la hoja.
3. **`espanol: nativo` es inferencia**, no texto literal (365 avisos): el
   modelo infiere el idioma del aviso. Inofensivo para el matching (el perfil
   lo cubre), pero a tener en cuenta al auditar.
4. **`linkedin-4476184789`** sin descripción: re-scrape del aviso o dejarlo
   fuera (no es un bug del extractor).
5. Cola de taxonomía **1150** → siguiente tanda de curación (migración `028`),
   priorizando variantes con ≥2 avisos reales (`demanda_corpus`, no `veces`).
6. **Medir el efecto de los puntos 1 y 4 en una corrida real** (no solo en
   copia): el siguiente pipeline completo debe mostrar menos llamadas por
   aviso y el `uso` guardado en `pipeline_etapa.detalle_json`.

## 5. Archivos clave

- `src/jobpulse_v15/ia_enrichment.py` — `pase_completo` (ciclos crítico y
  completo, cliente único, `ids_estancados`, `uso`), `run_ia_enrichment`
  (`exclude_ids`), `enrich_job` (qué cuenta como `failed`).
- `src/jobpulse_v15/pipeline_metricas.py` — `detalle_etapa("ia")` guarda el
  `uso` (llamadas + tokens).
- `src/jobpulse_v15/migrations/026_taxonomia_curacion_tanda_3.sql` — curaduría
  tanda 3 (48 variantes, 19 códigos nuevos) + los motivos de las 9 que se
  dejan en la cola.
- `src/jobpulse_v15/ui_v2/tabs/configuracion.py` — desplegable de modelos.
- `src/jobpulse_v15/migrations/027_job_match_decision.sql` — tabla de
  decisiones firmadas (`job_match_decision`).
- `src/jobpulse_v15/decisiones.py` — módulo canónico de las decisiones
  (ancla `text_hash`, persistencia, hoja de firma).
- `docs/PASO5_FIRMA_EDUCACION.json` — la hoja de firma (29 decisiones).
- `docs/PASO5_EVIDENCIA_2026-11-08.md` / `docs/PASO5_REVISION_PENDIENTES.md`
  — generados para la corrida `20261108_175932` (2 casos abiertos).
- `src/jobpulse_v15/ui.py` — `_post_flujo_completo` (~2119) y
  `open_enriquecimiento` (~2304): las dos ventanas delegan en el orquestador
  (turno 4).
- `src/jobpulse_v15/search_engine.py` — `modelo_embeddings_disponible()` y
  `embeddings_cache_cubren()` (turno 4).
- `src/jobpulse_v15/cli.py` — `viabilidad list|top` con `--semantica` /
  `--sin-semantica` (turno 4) y el comando `decision` (turno 3).
- `docs/PLAN_MEJORAS.md` §5.8 (UI clásica) y §5.9 (alcance real de 5.1/5.2).
- `docs/FLUJO_CLI_VS_UI.md` — paridad CLI / UI v2 / UI clásica.

## 6. Contexto

- Rama `main`, repo `giovar24/jobpulse-cr-v15`. **Commits locales, sin
  push** (falta confirmación del usuario): `a5a43fb`, `317f908`, `a36ca79`,
  `3b11a69`, `177de1c` + los de esta sesión (`c6fc8ce` puntos 1+4,
  `08b111d` punto 2, `6bf1b92` punto 3, y el commit del punto 5 — "feat(pipeline):
  la UI clasica delega en el orquestador y la semantica es el valor por
  defecto (punto 5)").
- **No pushear sin confirmación.**
- La UI clásica (`ui.py`) **no se toca** sin permiso explícito (el permiso
  del turno 4 se usó solo para delegar en el orquestador).
