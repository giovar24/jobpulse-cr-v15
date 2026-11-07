# Handoff — Sesión 2026-11-07

**TL;DR**: **Ola 4.2 · segunda tanda de curación de la taxonomía HECHA Y
APLICADA A LA BD REAL** (con OK del usuario, tras medir sobre copia):
migración **025** (`025_taxonomia_curacion_tanda_2.sql`) con **8 alias + 10
códigos nuevos** que cubren **21 variantes** de las **28 que varios avisos
piden**; las 9 restantes se dejan en la cola **a propósito** (vagas, tarea,
nombre de empresa, y 3 **fantasmas** de `demanda_corpus`: `espanol c1`/
`ingles c1`/`english target language`, que el extractor ya convierte en
requisito de idioma). En la BD real: cola 1225 → **1204**, taxonomía 706 →
**727**, requisitos vigentes 2858 → **2900 (0 sin código)**, corrida nueva
**`20261107_133939`** (calificada 191 → 188, revisar 376 → 380: los +42
requisitos recién visibles muestran gaps reales que antes eran invisibles),
evidencia OK (137 verificaciones literales), `db check` ok (esquema **25**),
`educacion_no_confirmada` **31 intacto**. También se verificó y corrigió
`AGENTS.md` contra el código (commit `a5a43fb`): baseline de tests **1164
passed + 980 subtests (~17 min, 2026-11-07)**, Brave acotado a lo que lo abre
de verdad, `--confirmar-externo` pertenece a `run_enriquecimiento.py`, etc.

## 1. Lo hecho

### 1.1 Verificación y corrección de `AGENTS.md` (commit `a5a43fb`)

La doc decía cosas que el código ya no hacía. Correcciones aplicadas (nada de
código):

- **Baseline de tests**: 1164 passed + 980 subtests, ~17 min (2026-11-07),
  python del **sistema** (`python -m pytest tests/ -q`); pytest no está en el
  venv.
- **Brave**: acotado — los subcomandos `scrape <plataforma>` NO abren Brave
  (reciben el puerto CDP); el que lo abre bajo demanda es
  `scraper.ejecutar_barrido` (etapa `scrape` del pipeline, `run_full_flow.py`,
  UI v2, `pipeline.ejecutar`).
- **No existe `scrape elempleo` ni `scrape harvie`**: esos fetchers solo corren
  vía `ejecutar_barrido`.
- `--confirmar-externo` es flag de `run_enriquecimiento.py`, **no** del CLI
  `jobpulse_v15`.
- `viabilidad top --limit` por defecto: **50**.
- Añadidos: `site mark-reviewed --all-needs-review` y
  `tools\corrida_medicion.py [--sin-ia] [--db RUTA]`.

### 1.2 Ola 4.2 · segunda tanda de curación (migración 025)

**Alcance medido, no supuesto**: la cola `concepto_no_normalizado` tiene 1225
variantes, pero el contador `veces` está **duplicado ×2** tras el re-análisis →
la demanda real se midió con `taxonomia.demanda_corpus`: **28 variantes las
piden ≥2 avisos** (el resto, 1197, las pide UN aviso).

**Migración** `src/jobpulse_v15/migrations/025_taxonomia_curacion_tanda_2.sql`
(mismo patrón que la 023; la cabecera documenta TODAS las decisiones):

- **8 alias** → conceptos existentes: `power brakes` →
  `tooling-especializado` (maquina-herramienta de la **misma lista** que ya
  curó la 023), `html css` → html, `nc capas` → acciones-correctivas,
  `service operations` → operational-support, `supply chain engineering` →
  abastecimiento, `informe de ventas` → reporting, `almacenamiento al vacio` +
  `preliminado de alimentos` → manipulacion-alimentos.
- **10 códigos nuevos** (13 variantes): `tuv`, `b2b`, `macos`,
  `sistemas-operativos`, `r`, `servidores` (servers/servidores),
  `organizacion`, `comunicacion` (comunicacion/listening skills),
  `validacion` (validacion/validation), `variance-analysis`.
- **9 en la cola a propósito**: `data driven settings`, `external services`,
  `upgrades`, `website`, `four seasons` (empresa), `providing product
  information` (tarea) + los 3 fantasmas `espanol c1` / `ingles c1` /
  `english target language` (ver decisión 2 abajo).

**Tests**: `tests/test_migraciones.py` (+`TestMigracion025`: alias, códigos
nuevos, las 9 dejadas en NULL, idempotencia, no toca la cola; versiones
24 → 25), `tests/test_pipeline_metricas.py` (versiones 24 → 25). Suite
objetivo: **105 passed + 1499 subtests, 42,9 s**. **Suite completa: 1171
passed + 1740 subtests, 8 min 30 s** (baseline 1164+980 + los 7 tests nuevos
de la 025).

**Herramienta**: `tools/estado_extraccion.py` ahora acepta `--db RUTA`
(antes solo medía la BD real; ahora mide copias — consistente con
`corrida_medicion.py --db`).

### 1.3 Medición (copia) y aplicación (BD real) — resultado IDÉNTICO

Copia por la API de respaldo (`backup` valida integridad):
`%TEMP%\opencode\tanda2_copia.db`. Secuencia en la copia: abrir (esquema 25)
→ `taxonomy curate --apply` → `enrich requirements-source --apply` →
`enrich requirements-canonico --apply` → `corrida_medicion.py --sin-ia --db …`
→ snapshot + `comparar_extraccion.py` → `db check` ok.

| Métrica | Antes (esq. 24) | Después (esq. 25) |
|---|---|---|
| Cola `concepto_no_normalizado` | 1225 | **1204** (−21) |
| Taxonomía (filas `concepto`) | 706 | **727** (+21) |
| Requisitos vigentes | 2858 (0 sin código) | **2900 (0 sin código)** (+42: 39 skill, 3 language) |
| Variantes con código / códigos usados | 546 / 281 | 566 (+20) / 291 (+10) |
| Matching | calif. 191 · revisar 376 · datos_insuf 34 · descartada 96 · sin_req 8 | calif. **188** · revisar **380** · datos_insuf **33** · descartada 96 · sin_req 8 |
| `educacion_no_confirmada` | 31 | **31 (intacto)** |

**Aplicación a la BD real (2026-11-07, con OK del usuario)**: respaldo
`data/backups/pre_tanda2_20261107_133858.db` → apertura (aplica la 025,
esquema **25**) → `taxonomy curate --apply` (cola 1225 → **1204**) →
`enrich requirements-source --apply` (705 avisos, 1750 requisitos fuente, 0
errores) → `enrich requirements-canonico --apply` (0) → corrida
**`20261107_133939`** (705 evaluadas, 2906 requisitos evaluados) → evidencia
`docs/PASO5_EVIDENCIA_2026-11-07.md` OK (**137 verificaciones literales**,
`no_confirmada=31`) → hoja de firma regenerada (31 casos, corrida nueva) →
`db check` ok (esquema 25, integridad ok, 0 FK).

## 2. Decisiones

1. **Tanda 2 = demanda real ≥2 avisos** (vía `demanda_corpus`), NO el
   contador `veces` de la cola (está duplicado ×2 tras el re-análisis).
2. **Los 3 "idioma-en-skills" son FANTASMAS y NO se curan** (documentado en la
   cabecera de la 025): `espanol c1`/`ingles c1`/`english target language`
   aparecen en `jobs.skills` crudos, pero el extractor **ya** los crea como
   requisito de **idioma** con nivel (verificado: 0 filas tipo `%c1%` como
   skill en `job_requirements`; ej. `ane-121813` → language `es`/`c1`/
   `espanol`). Curarlos como skills sería un **bug**: `cumple_skill` solo
   mira hechos del perfil categoría `skill` y el perfil registra `espanol`
   como **idioma** → falso "faltante". El arreglo correcto es de **código**
   (`demanda_corpus` lee `jobs.skills` crudos), queda anotado para otra
   sesión.
3. **El −3 de `calificada` es honestidad, no regresión**: los +42 requisitos
   recién visibles hacen que 3 avisos que parecían cubiertos del todo
   muestren un `required` real que faltaba (tope `revisar`) y 1 pase de
   `datos_insuficientes` a `revisar`. `descartada` (96) y `sin_requisitos`
   (8) no se movieron. Mismo criterio que la tanda 1 (§4.2 del plan).
4. **Medir antes de tocar la BD real** (regla del repo): todo se midió primero
   sobre copia; el resultado real fue **idéntico**.

## 3. Metas (tabla canónica O1–O14)

| Objetivo | Qué es | Estado |
|---|---|---|
| O1–O6 (pipeline scrape → matching) | — | ✅ Hecho (sesiones previas) |
| O7 (IA local/browser) | — | ✅ Hecho |
| O8/O10 (retención + diagnóstico + filtros) | — | ✅ Hecho |
| O2.2 (Req. + filtro) · O3 (salud de sitios) | — | ✅ Hecho (2026-11-04) |
| Capa B (`codigo_canonico` del perfil) | — | ✅ Hecho y efectivo en la BD real |
| Motor de viabilidad (ajuste técnico) | — | ✅ Hecho (pesos = priors; falta ground truth propio) |
| Postulaciones (correo + Workday) | — | ✅ Hecho en código; falta validación en vivo |
| Bloque de ALINEACIÓN (campos estructurados) | — | ✅ Hecho **y aplicado en la BD real** |
| **O11 IA externa / motor intercambiable** | — | ✅ Hecho (2026-11-05) |
| **O12 Paridad CLI/UI** | La UI debe dar los mismos números que la CLI | ✅ **Olas 1 y 2** (2026-11-05): 231 → 11 `sin_requisitos` |
| **O13 Cobertura de fuentes** | Que el barrido traiga los avisos que existen | 🟢 **Ola 3 COMPLETA (2026-11-06)**: LinkedIn 0 → 60 · Elempleo 0 → 3 · `requires_login` · sesión de ANE entre arranques · ANE con dos barridos seguidos |
| **O14 Control del coste de la IA** | Límites opt-in y ajustables | ✅ Hecho (2026-11-05) |
| `educacion_no_confirmada` | 31 casos | ⏳ **ABIERTO** (firma de una 2ª persona) |
| O5.3 (re-barrido de descripciones basuras) | 43 descripciones <200 chars (35 de ANE) | 🟢 **HECHO Y APLICADO (2026-11-06)**: el hueco era el **parser**; corrida `20261106_152304` |
| Ola 4.2 (curación de la taxonomía) | Cola: 1988 → tanda 1 → tanda 2 | 🟢 **HECHO Y APLICADO (2026-11-07, tanda 2)**: filtro + 023 + **025** + `taxonomy curate`. Cola 1988 → **1204**, requisitos 2483 (1 sin código) → **2900 (0 sin código)**, corrida vigente **`20261107_133939`**, `educacion_no_confirmada` 31 intacto |
| Ola 4.3 (métricas por etapa) | Auditar por qué una corrida dio menos | 🟢 **HECHO Y APLICADO (2026-11-06)**: tabla `pipeline_etapa` (migración 024) + `pipeline_metricas.py` + `… pipeline etapas`; corrida real `pipe_20261106_215235` |
| O6.4 (dedupe slugs ES/EN) | — | ⏳ Parcial |
| O4 (calibración gate-vs-IA) | — | 🟡 Proponer cerrar como *superseded* |
| O8.2 / O8.4 / O9 / pestañas nuevas UI v2 | — | ⏳ Pendiente (Ola 4) |

**Siguiente ola** (plan en `docs/PLAN_MEJORAS.md`): Ola 4 — 4.1 ✅ · 4.2
✅ (tanda 1 + tanda 2 aplicadas; **resto de la cola = 1197 variantes de un
solo aviso → siguiente tanda cuando entre corpus nuevo** + arreglo de código
de los 3 fantasmas) · 4.3 ✅ · **corrida en limpio con scrape → otro día**
(decisión del usuario: la medida sobre datos crudos no aportó corpus) ·
**Ola 5** (O4, upsert, embeddings) se puede dejar de último.

## 4. Cómo retomar (comandos)

```powershell
# Suite completa (python del SISTEMA; ~17 min; baseline 1164+980 subtests)
python -m pytest tests/ -q

# Solo la tanda 2 de la Ola 4.2
python -m pytest tests/test_migraciones.py tests/test_pipeline_metricas.py `
  tests/test_taxonomia.py tests/test_conceptos.py -q

# Taxonomia: auditar la cola / reconstruirla (NO toca la BD real sin --apply)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 taxonomy curate --limit 30
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 taxonomy curate --apply

# MEDIR una mejora sobre una COPIA (estado ANTES -> corrida -> DESPUES -> comparar)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 backup --output data\backups\X.db
.\.venv\Scripts\python.exe -X utf8 tools\estado_extraccion.py --db C:\...\copia.db antes antes.json
.\.venv\Scripts\python.exe -X utf8 tools\corrida_medicion.py --sin-ia --db C:\...\copia.db
.\.venv\Scripts\python.exe -X utf8 tools\estado_extraccion.py --db C:\...\copia.db despues despues.json
.\.venv\Scripts\python.exe -X utf8 tools\comparar_extraccion.py antes.json despues.json

# Estado de la BD real y evidencia (exit 0 = todo cuadra)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 db check
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py
.\.venv\Scripts\python.exe -X utf8 generar_revision_pendientes.py   # hoja de firma

# Corrida real del pipeline (el MISMO orquestador que la CLI y la UI v2)
.\.venv\Scripts\python.exe -X utf8 tools\corrida_medicion.py [--sin-ia] [--db RUTA]

# Metricas por etapa (Ola 4.3)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 pipeline etapas --limite 5
```

## 5. Archivos clave

| Archivo | Qué es |
|---|---|
| `src/jobpulse_v15/migrations/025_taxonomia_curacion_tanda_2.sql` | **NUEVO** — tanda 2: 8 alias + 10 códigos nuevos (21 variantes); cabecera con TODAS las decisiones y las 9 dejadas |
| `tests/test_migraciones.py` | **+`TestMigracion025`** (alias, códigos nuevos, 9 en NULL, idempotencia, no toca la cola); versiones 24 → 25 |
| `tests/test_pipeline_metricas.py` | versiones 24 → 25 |
| `tools/estado_extraccion.py` | **+flag `--db RUTA`** (mide copias; antes solo la BD real) |
| `docs/PLAN_MEJORAS.md` | §4.2 actualizado con la tanda 2 (medición + aplicación) |
| `docs/PASO5_EVIDENCIA_2026-11-07.md` | **GENERADO** — evidencia de la corrida `20261107_133939` (137 verificaciones literales) |
| `docs/PASO5_REVISION_PENDIENTES.md` | hoja de firma regenerada (corrida `20261107_133939`, 31 casos) |
| `AGENTS.md` | verificado/corregido contra el código (commit `a5a43fb`) |
| `src/jobpulse_v15/taxonomia.py` | `demanda_corpus` (la fuente de verdad del alcance) y `curar` (reconstruye la cola) |
| `data/backups/pre_tanda2_20261107_133858.db` | respaldo previo a la aplicación en la BD real |

## 6. Contexto (estado de la BD real)

- **BD real `data/jobpulse_v15.db`**: **esquema 25** (025 aplicada hoy), 705
  avisos, taxonomía **727** conceptos, cola **1204**, requisitos vigentes
  **2900 (0 sin `codigo_canonico`)**, `integrity_check ok`, 0 FK.
  **Corrida Paso 5 vigente `20261107_133939`**: calificada 188 · revisar 380
  · descartada 96 · datos_insuf 33 · sin_requisitos 8 ·
  `educacion_no_confirmada` **31 (intacto)**. Corridas anteriores
  (`valida=0`): `20261106_220243` (191/376/96/34/8), `20261106_182554`,
  `20261106_152304`, `20261104_231932`.
- **Respaldo de esta sesión**: `data/backups/pre_tanda2_20261107_133858.db`
  (antes de la 025). Anteriores: `pre_ia_20261106_215042.db`,
  `pre_ola43_20261106_210124.db`, `pre_ola42_20261106_182411.db`,
  `pre_ola4_20261106_151857.db`, `pre_mig022_20261106_130349.db`.
- **Medición de la tanda 2** (copias en `%TEMP%\opencode\`):
  `tanda2_copia.db` + snapshots `tanda2_antes.json` / `tanda2_despues.json` /
  `tanda2_despues_real.json`; resultado copia == real (§1.3).
- **Salud de sitios**: `ane-cr` healthy; `linkedin-cr` y `elempleo-cr` en
  `zero_results` con 2 ceros (corridas del scraper roto de antes del arreglo:
  el próximo barrido exitoso los deja healthy).
- **`.env`**: `IA_PROVEEDOR=custom`, `IA_BASE_URL=http://127.0.0.1:8081/v1`,
  `IA_MODEL=gemma4-e2b-qat` (sin tope) · `BRAVE_CDP_PORT=9222`.
- **Sesión de ANE**: `data/usuario/sesiones/ane.json` (gitignoreado).
- **Cola de taxonomía**: 1204 pendientes: **9** las piden 2 avisos (las que
  se dejaron a propósito en la tanda 2) y **1195** las pide un solo aviso →
  siguiente tanda cuando entre corpus nuevo.
- **`concepto_no_normalizado.veces` sigue duplicado ×2** tras el re-análisis:
  `taxonomy curate --apply` lo reescribe bien; usar `demanda_corpus` como
  medida (decisión 2 del handoff 2026-11-06 también aplica).

## 7. Pendiente inmediato

1. **Corrida en limpio con scrape → OTRO DÍA** (decisión del usuario): falta
   corpus (los 24 avisos ANE 122031+ detectados, LinkedIn/Elempleo). Orden:
   scrape → `analysis extract-pending` → `run_enriquecimiento.py` →
   `enrich requirements-source --apply` → `enrich requirements-canonico
   --apply` → `run_paso5.py` → evidencia. **Con el aviso**: la etapa IA local
   tarda ~10 min por 700 avisos.
2. **Arreglo de código (no de datos) de los 3 fantasmas** en
   `taxonomia.demanda_corpus`: leer los idiomas de `jobs.languages` (o
   filtrar los `* c1` de `jobs.skills`) para que la cola no pida curar como
   skill lo que ya es requisito de idioma.
3. **Ola 5** (`docs/PLAN_MEJORAS.md`): O4 (calibración gate-vs-IA, proponer
   cerrar como *superseded*), upsert, embeddings. Se puede dejar de último.
4. `educacion_no_confirmada` (31 casos): **NO** actualizar estados hasta que
   una **segunda persona** firme `docs/PASO5_REVISION_PENDIENTES.md` (ya
   regenerada para la corrida `20261107_133939`).
5. (Opcional, con permiso) migrar la **UI clásica** al orquestador
   `pipeline.py` (la UI clásica no se toca sin pedirlo).
6. **No pushear sin confirmación del usuario** (regla del repo): los commits
   de esta sesión están locales.

## 8. Commits de esta sesión

- `a5a43fb` — `docs: verifica y corrige AGENTS.md contra el codigo (baseline
  tests, Brave, flags)` — sin push.
- `317f908` — `feat(o5.3): Ola 4.2 tanda 2 - migracion 025 (21 variantes
  curadas)` — migración 025 + tests (versiones 25, `TestMigracion025`) +
  `--db` en `estado_extraccion.py`; medido en copia y **aplicado a la BD
  real** (cola 1225 → 1204, requisitos 2900, corrida `20261107_133939`,
  evidencia 137 OK, `db check` ok). Suite completa **1171 passed + 1740
  subtests (8 min 30 s)**. Sin push.
- **HEAD (docs)** — `docs(o5.3): Ola 4.2 tanda 2 aplicada a la BD real` —
  plan + evidencia + hoja de firma + este handoff.
