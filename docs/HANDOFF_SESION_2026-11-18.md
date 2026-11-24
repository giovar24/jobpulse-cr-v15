# Handoff — Sesión 2026-11-18

**TL;DR**: sesión dedicada **solo a documentación** (cero cambios de código
funcional). Se escribieron **10 contratos EGM «Hay»** por directorio, se
generó un **informe de deriva** con ~70 discrepancias entre esos contratos y el
código real, se corrigieron, y luego se corrió un **loop de revisión Goldfish
sobre el `README.md` raíz** con **2 rondas** y 3 revisores. El README pasó de
**822 a 1040 líneas** con **32 reparaciones aplicadas** (24 en la ronda 1, 8 en
la ronda 2). **La convergencia del loop NO quedó acreditada**: los revisores
`codebase_details` y `style` fallaron en la ronda 2 por límites del proveedor
(HTTP 429 y «content safety screening is temporarily unavailable») y quedaron
como `not run`. Nada está commiteado hasta este cierre.

---

## 1. Lo hecho

### 1.1 Contratos EGM por directorio (10 archivos nuevos)

Cada directorio gana un `README.md` con interfaz, invariantes y efectos:

| Archivo | Contenido |
|---|---|
| `README.md` | Contrato raíz (blueprint) — ver §1.3 |
| `src/README.md` | Hay del código fuente; documenta el defecto de `package-data` |
| `src/jobpulse_v15/README.md` | El más corregido: ~60 módulos |
| `src/jobpulse_v15/migrations/README.md` | Las 28 migraciones, por tipo (DDL/DML) y por tabla |
| `src/jobpulse_v15/providers/README.md` | Adaptadores de fuente |
| `src/jobpulse_v15/providers/login/README.md` | El que más hallazgos tuvo: **sin llamadores en producción** |
| `src/jobpulse_v15/ui_v2/README.md` | UI v2 (única interfaz) |
| `src/jobpulse_v15/ui_v2/data/README.md` | Stores sin Tk |
| `src/jobpulse_v15/ui_v2/tabs/README.md` | 6 pestañas |
| `tools/README.md` | Qué scripts **escriben** la BD o **migran** el esquema |

### 1.2 Informe de deriva — `2026-11-13_DRIFT_REPORT.md` (raíz)

~70 discrepancias de 10 documentos, con 4 revisores `egm-codebase-details` en
contexto fresco. Correcciones verificadas contra el código y aplicadas en los
contratos: bandas `BANDA_REVISAR`/`BANDA_VETO`/etc.; `login_ane(port: int = 9222)`;
`IngestionError(run_id, message)`; fila nueva de `ubicaciones_cr.py`;
`harvie.py` como ATS; `workday.py` **sin CDP**; `ProfileStore.save` **sí** escribe
`codigo_canonico`; `pyproject.toml` solo declara `seeds/*.json` (faltan
`migrations/*.sql` y los CSV); `022` mezcla `requiere_login`/`requires_login`;
5 scripts de `tools/` llaman `Database.initialize()`. Enlaces relativos
verificados: **todos resuelven**.

### 1.3 Loop de revisión Goldfish sobre `README.md` (raíz)

Configuración: objetivo `README.md` raíz, alcance **archivo completo**,
revisores `codebase_details` + `style` + `comprehension`, estándares
`feature-spec-standard` ×2 + `zoom-out-standard`, contexto de oro = código
completo + seeds + `pyproject.toml`.

| Ronda | Hallazgos | Aprobados | Estado |
|---|---|---|---|
| 1 | 31 (2 Blocker · 18 Major · 11 Nit) | 24 PROPOSE FIX, 6 DECLINE | ✅ aplicada |
| 2 | 9 (7 Major · 2 Nit) de `comprehension` | 8 PROPOSE FIX | ✅ aplicada |

**Bloqueadores corregidos (ronda 1, ambos verificados contra el código):**

1. `## Interfaz de escritorio` (161-263) describía la **UI clásica ya retirada**
   (2026-11-11) como vigente → aviso `> **Histórico.**` + redirección a la UI v2
   (6 pestañas). Verificado en `ui_v2/app.py:39-45`.
2. **Workable**: se documentaba `country_query (multi-loc)` y modalidad solo
   «telecommuting» → reescrito: `jobs.md`/`jobs/view/<id>.md` por `urllib`,
   `country_query` sobre título+ubicación, `location_raw` **sin** `multi-loc`,
   `work_mode` desde `**Workplace:**`. Verificado en `workable.py:55-57,86,210-219`.

**Reparaciones mayores de la ronda 1:** `rules-1` → `rules-2` (dos apariciones);
`location normalize-workday --apply` documentado como **mutante** (corrige
ciudades basura, `corrected_cities`, `cli.py:3195-3205`); los 4 scripts de
`tools/` que migran el esquema; tabla de 10 subsistemas con comandos, tablas y
enlaces; `### Prerrequisitos`; `### Problemas conocidos de los lanzadores`;
glosario de siglas; nota de jerarquía blueprint↔manual.

**Reparaciones de la ronda 2 (las importantes):**

- **Numeración de las etapas**: el flujo ahora está numerado
  `1 scrape → 2 análisis → 3 IA → 4 re-análisis → 5 backfill → 6 Paso 5 → 7 evidencia`,
  con la nota de que **el Paso 5 es la etapa 6** (la numeración «Paso 5» es
  histórica). *Este defecto lo introdujo yo en la ronda 1* al escribir «el paso 3»
  y «el paso 4» sin definir el esquema.
- `run_enriquecimiento.py` aclarado como **atajo** (etapa 3 + etapa 4 encadenada),
  no un segundo re-análisis.
- Glosario: **9 términos load-bearing** añadidos (fetcher/adaptador, orquestador,
  `codigo_canonico`, evidencia/`evidence`, huella, salud de sitios, idempotente,
  Paso 7, `educacion_no_confirmada`).
- Tabla de subsistemas: cada comando `enrich` con su **etapa y función**
  (`requirements-source` = etapa 4, `requirements-canonico` = etapa 5,
  `profile-canonico` = fuera del flujo).
- «Paso 7» explicado (hito del proyecto, no etapa del pipeline) + efecto de cada
  veredicto de firma.
- **Salud de sitios** definida: estados `ok`/`zero_results`/`error`/`requires_login`,
  bandera `review_required`, regla de 3 corridas con 0 avisos.
- **Prerrequisitos separados**: Brave con CDP (con el comando del CLI
  `asegurar_brave(9222)`) y chromium de Playwright.
- ~8 referencias a «la UI» normalizadas a UI v2 / UI clásica retirada.

### 1.4 Defectos detectados por verificación propia (no por los revisores)

| # | Defecto | Origen |
|---|---|---|
| A | Tabla de subsistemas con filas de 6 columnas frente a 5 de la cabecera | Ronda 1 (mío) |
| B | `credenciales list\|set\|…` rompía la tabla en 11 columnas (`\|` no escapa dentro de *code spans*) | Ronda 1 (mío) |
| C | Glosario decía «consultado con `urllib`» cuando la dependencia real es `httpx[http2]` | Ronda 2 (mío) |
| D | `RSS`, `Playwright`, `urllib` usados sin expandir | Ronda 2 (mío) |
| E | Errata `la_ui clásica` | Ronda 2 (mío) |

Ninguno de A-E fue detectado por los revisores Goldfish.

---

## 2. Decisiones

1. **Solo documentación**: cero cambios de código funcional en toda la sesión.
2. **Corrección in-place** de los contratos (no sobrescritura total), para
   preservar lo ya verificado.
3. **DECLINE sobre reestructuración editorial** del manual heredado (6 hallazgos
   en la ronda 1): el capitulo de UI, el boilerplate ATS y los párrafos largos
   de búsqueda se dejan como están, protegidos por el aviso de histórico. El
   coste editorial supera el beneficio y arriesga perder detalle.
4. **Una ronda con revisores `not run` NO cuenta como limpia**: la convergencia
   del loop (2 rondas limpias consecutivas) no se acredita.
5. **Suspensión de Windows ampliada a 4 h** (antes 2 h) por el usuario, porque
   cada suspensión tumba los subagentes en vuelo y es la raíz de los fallos
   repetidos del proveedor (429 / screening). El usuario la ampliará más si hace
   falta.

---

## 3. Tabla de objetivos (estado al cierre del 2026-11-18)

Sin cambios respecto al cierre del 2026-11-10: **ninguna sesión de objetivos se
tocó**. Ver `docs/HANDOFF_SESION_2026-11-10.md` §0 para la tabla completa
(O1-O14 + Ola 6). Resumen: O1/O3/O7/O11/O12/O13/O14 completos; O2/O5/O6/O8/O10
parciales; O4 cerrado como *superseded*; O9 placeholder; Ola 6 R1 y 6.2.1
aplicadas; Ola 6 6.1/6.3 diferidas.

---

## 4. Cómo retomar

1. **Abrir el contrato raíz** `README.md` (1040 líneas): las líneas 1-256 son
   el blueprint vigente (manda en conflicto), 258-1040 el manual heredado.
2. **Para el loop**: reanudar en la **ronda 3** (quedan 3 del tope de 5).
   Repaso mínimo antes de lanzarla: los 2 revisores caídos conviene despacharlos
   **uno por vez y con el prompt corto** (el prompt largo es lo que más
   dispara el screening); si vuelven a fallar, la ronda 3 será `not run` otra vez
   y la convergencia seguirá sin acreditarse. Si el proveedor sigue limitando,
   la alternativa documentada es cerrar el loop con la verificación mecánica
   propia (ya hecha: 27 subcomandos + flags, 43 rutas, 7 estados de `job_match`,
   5 bandas, 2 firmas de API, 4 límites numéricos, 3 tablas homogéneas).
3. **Decisión pendiente**: mover `2026-11-13_DRIFT_REPORT.md` de la raíz a
   `docs/` (ofrecido, sin decidir).
   → **Resuelto el 2026-11-22**: el informe se movió a
   `docs/2026-11-13_DRIFT_REPORT.md` y quedó enlazado desde el README
   (sección «Subdirectories & System Boundaries»).
4. **Recomendación**: al tocar de nuevo un contrato EGM, re-verificar las
   afirmaciones numéricas y de flags con un barrido de `--help` como el de esta
   sesión; es lo que detectó los defectos A y B que los revisores no vieron.

---

## 5. Archivos clave

| Archivo | Estado |
|---|---|
| `README.md` (raíz) | **modificado** — 822 → 1040 líneas |
| `AGENTS.md` | **modificado** — correcciones de deriva (corrida vigente `20261111_074200`, `init-db` sí migra, `Database.initialize()` en 5 scripts, UI v2 como módulos planos) |
| `goldfish_review_report.md` (raíz) | **nuevo** — informe anotado de las 2 rondas con categorización y estado de aplicación |
| `2026-11-13_DRIFT_REPORT.md` (raíz) | **nuevo** — ~70 discrepancias |
| 8 `README.md` por directorio | **nuevos** — ver §1.1 |
| `docs/HANDOFF_SESION_2026-11-18.md` | **nuevo** — este archivo |

---

## 6. Contexto

- **Modelo de la sesión**: `nvidia/minimaxai/minimax-m3.1-flash`.
- **Problema del proveedor**: los subagentes fallan con `HTTP 429` y
  «content safety screening is temporarily unavailable». La sesión principal
  responde sin problema. Los fallos se concentran en los subagentes y empeoran
  con prompts largos.
- **Ruta del bundle EGM**: los globs del harness **no alcanzan** rutas fuera del
  workspace; leer el bundle con `read`/`shell`, nunca `glob`. Los subagentes
  **no** pueden leer esos archivos (denegado `external_directory`): hay que
  pasarles el contenido o pedirles la ruta absoluta.
- **`AGENTS.md` está cargado como instrucciones del repo**: sus cambios
  reaparecen como `system-update` en cada turno.
- **Dos Pythons**: app/CLI/scripts → `.venv\Scripts\python.exe -X utf8`;
  tests → python del sistema (`python -m pytest tests/ -q`).

---

## 7. Pendiente inmediato

1. **Commitear y pushear** el trabajo de documentación de esta sesión (pedido
   y confirmado por el usuario). Esto es lo que cierra el punto 3 de §4.
2. **Ronda 3 del loop** (o cierre del loop con la verificación mecánica).
3. **Decidir** la ubicación de `2026-11-13_DRIFT_REPORT.md` (raíz vs `docs/`).
   → **Hecho el 2026-11-22**: vive en `docs/`.
