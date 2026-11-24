# Handoff — Sesión 2026-11-23

**TL;DR**: sesión de **solo documentación** (cero cambios de código funcional).
Se cerró el **loop de revisión Goldfish sobre el `README.md` raíz** con las
**rondas 3, 4 y 5** (la 5 como *final*, agotando el tope de 5): **114 hallazgos
nuevos**, todos verificados contra el archivo/código y **0 DECLINE**. Sumado a
las rondas 1-2 de la sesión anterior, el loop total aplica **153 hallazgos**
(tendencia 31 → 8 → 53 → 15 → 46) y el README pasa de 822 a **1187 líneas**.
**La convergencia estricta del loop NO quedó acreditada** (ninguna ronda salió
sin hallazgos y el tope de 5 la hace ya inalcanzable); se cerró **por tope** con
**verificación mecánica independiente** de los subagentes. El trabajo de las
rondas 3-5 está **commiteado y pusheado** en `0ee82a5`; este handoff es el
último commit de la sesión.

---

## 1. Lo hecho

### 1.1 Ronda 3 — 53 hallazgos (11 + 26 + 16)

Revisores despachados **secuencialmente y con prompt corto** (decisión del
usuario: el prompt largo dispara el *screening* del proveedor).

| Revisor | Hallazgos | Sev. | Aplicados |
|---|---|---|---|
| `codebase_details` (3a) | 11 | 2 Blocker · 7 Major · 2 Nit | 11 |
| `style` (3b) | 26 | 13 Major · 13 Nit | 26 |
| `comprehension` (3c) | 16 | 6 Major · 10 Nit | 16 |

**Lo importante de la 3a (los 2 Blocker eran reales):**

- El README afirmaba que la **UI v2 da de alta tableros ATS** («Agregar» +
  confirmación). Falso: el único «Agregar» de `ui_v2` es de sitios con login
  (`cuentas.py:381`); la ventana `Administrar fuentes` es de la **UI clásica**
  (`ui.py:441,2561`). Los 6 pasajes se reescribieron: **alta por CLI**
  (`site add`), la UI v2 solo ejecuta y consulta.
- `Respaldar DB` y `Marcar revisada` **no existen** en `ui_v2` (eran de la UI
  clásica). Ambos marcados como retirados, con su equivalente CLI (`backup`,
  `site mark-reviewed`).
- «Procesar» ejecuta **6 etapas sin `scrape`**
  (`scraping.py:411` → `analisis, ia, reanalisis, backfill, paso5, evidencia`).
- `viabilidad` **no lee `job_match`**: recalcula sobre `job_analysis` al vuelo
  (`viabilidad.py:536-559`).
- Versión vigente del extractor: **`rules-2+fuente`**
  (`analysis_flow.py:29`), no `rules-2`.

**Lo importante de la 3b:** unificación de las **3 redacciones contradictorias**
de quién abre Brave; normalización mecánica de tildes en el manual heredado
(227+17+25 reemplazos, preservando etiquetas *verbatim* de la UI clásica);
«muro de texto» de «Interfaz de escritorio» partido en 8 subsecciones; `pip
install -e .` → `python -m pip`; solape de bandas corregido (`revisar` ≥80 y
<85, `viabilidad.py:49-50,469-474`).

**Lo importante de la 3c:** filas nuevas en el glosario (**perfil**, **aviso**,
**harvie**, **cinde**, **procomer**, **elempleo**, **keyring**, **llama-server**);
«retención/purga» definidas (oculta, **nunca borra**); criterio de `veto` y
`sin_datos`; `country_query` ubicado en `site_config_json`.

**Defectos propios de la ronda 3** (no los vieron los revisores): F (referencia
colgante a «Esquema inicial»), G (`--solo-requisitos-obligatorios` descrito
mal), H (**corrupción de codificación**: 16 «ubicación» degradadas a
`ubicaci?n` por un pase de tildes por stdin — reparada), I (3 palabras sin tilde
que resultaron ser etiquetas *verbatim* correctas), J (6 tildes escapadas).

### 1.2 Ronda 4 — 15 hallazgos (3 + 10 + 2)

| Revisor | Hallazgos | Aplicados |
|---|---|---|
| `codebase_details` (4a) | 3 Major | 3 |
| `style` (4b) | 5 Major · 5 Nit | 10 |
| `comprehension` (4c) | 2 Major | 2 |

**Ronda 4 = primera sin problemas de fondo nuevos**: los 4 defectos que
encontró eran **del autor** (introducidos en 3b/3c/4a): `health_status`
(acumulado) confundido con `source_run_sites.status` (por corrida); «Procesar»
atribuido al scraping; la UI v2 atribuida alta/consulta de tableros; y un
**encabezado con caracteres CJK** (dos ideogramas colados) al dividir la fila de
Viabilidad.

En la 4b se creó la tabla **«Contrato común de los tableros ATS»** (consulta,
alta, filtrado, persistencia, corridas, modalidad) y cada proveedor se quedó
solo con sus **variantes**. En la 4c se aclaró que `candidate_profile_facts`
**no tiene estado «aprobado»** (solo `origin` `manual`/`imported`).

**Defectos propios de la ronda 4:** K (pipe sin escapar en `api\|rss` rota la
tabla), L/O (tildes), M (dos bloques «Contrato común» homónimos), N (typo
`platforma`), P (caracteres CJK).

### 1.3 Ronda 5 (final, tope) — 46 hallazgos (3 + 30 + 13)

| Revisor | Hallazgos | Aplicados | Notas |
|---|---|---|---|
| `codebase_details` (5a) | 1 Blocker · 2 Major | 3 | **3 intentos**: 2 fallos del proveedor + 1 informe |
| `style` (5b) | 18 Major · 12 Nit | 30 | 1 intento |
| `comprehension` (5c) | 10 Major · 3 Nit | 13 | 1 intento |

**El Blocker de la 5a (real y gordo):** el README decía que `search --format
csv` produce «el mismo CSV que la UI v2». **No hay equivalencia**: la UI v2
tiene **dos** CSV propios (`ui_v2/data/jobs.py:271`, datos crudos;
`ui_v2/data/vacantes.py:342`, ranking ATS) y **ninguno** lleva
`compatibilidad_perfil` ni `motivos_revision`; esas columnas solo existen en
`exports.write_job_search_csv` (`exports.py:45-47`), que la UI v2 nunca invoca.

**Los otros dos Major de la 5a:** el marcador `multi-loc` existe solo en
**Ashby, Lever y Recruitee** (`ashby.py:130`, `lever.py:131`,
`recruitee.py:136`), no en los 7; y `review_required` tiene **tres**
disparadores (`error`, `requires_login`, racha de 3 ceros —
`repository.py:518,532,538-562`), no solo la racha.

**Lo importante de la 5b (30/30):** `--revisitar` usa `--limite` (no `--dias`);
«7 adaptadores» ignoraba **harvie**; «activar/pausar sitios» **sí** sigue en la
UI v2 (`configuracion.py:1410-1443`); `multi-loc` y «export controlado»
definidos; etiqueta «Variantes:» ×7 → «Comportamiento:»; «un API» → «una API»
(×4); manual heredado pasado a pretérito. **Defecto propio cazado:** `Respaldá`
(voseo rioplatense) → `Respalda`.

**Lo importante de la 5c (13/13):** contradicción UI/CLI del scrape ATS
resuelta (**el alta** es solo CLI; **el scrape** de sitios ya registrados se
lanza desde la UI v2 o por CLI); justificación 4→5 corregida (la 4 **añade**
requisitos que la 5 normaliza; invertirlo deja requisitos **ignorados en
silencio**); párrafo **«Quién abre Brave»** por punto de entrada; escala de
estados **por requisito** (`bloqueante`/`faltante`/`educacion_no_cumple`) y
`inferred` como **nivel** (no estado de campo); `normalize-workday` vs.
`normalize` separados; umbrales **0.60 / 0.80** añadidos; ciclo de vida de
postulaciones y qué purga `clean_run.py`; `jobs_found = 0`; `ia-server.bat` →
`start_ia_server.py`; «Procesar» también levanta el servidor IA
(`pipeline.py:350`).

### 1.4 Verificación mecánica final (independiente de los subagentes)

Barrido de `--help` + esquema contra el README (el método que en la sesión
anterior cazó defectos que los revisores no vieron):

| Afirmación | Comprobación | Veredicto |
|---|---|---|
| 24 grupos de comando citados | `jobpulse-v15 --help` | ✅ los 24 existen |
| BD por defecto `data/jobpulse_v15.db` (raíz) | `db.py:32` + `schema-version` en vivo | ✅ el README acierta |
| Esquema vigente = 28 | `schema-version` en la BD real | ✅ |
| `source_run_sites.status` 7 valores | `001:116-119` + `022:76` | ✅ |
| `source_sites.health_status` 7 valores | `001:22-26` + `022:41-45` | ✅ |
| README íntegro | recuento | ✅ 1187 líneas, 6 tablas homogéneas, 54 fences, 19 h2, 0 corrupción, 0 CJK |

**Defecto de CÓDIGO detectado y no tocado** (la tarea era solo documentación):
`cli.py:659` dice que la BD por defecto es `v1_5/data/jobpulse_v15.db`; la real
es `data/jobpulse_v15.db`. El README documenta la ruta **correcta**; el texto de
ayuda del CLI quedó obsoleto.

---

## 2. Decisiones

1. **Solo documentación**: cero cambios de código funcional. Los defectos de
   código hallados se anotan en el README/informe, no se corrigen.
2. **Criterios del loop**: ronda limpia = sin Blocker/Major pendiente y sin
   revisores `not run`; convergencia = **2 rondas limpias consecutivas**; tope =
   **5 rondas**.
3. **Ronda 5 ejecutada como final** («Ronda 5 final»): con el tope en 5, la
   convergencia estricta ya no era alcanzable, así que la ronda se usó como
   barrido de cierre.
4. **Aplicar todo lo verificado** en cada puerta: 3/3 en 5a, 30/30 en 5b, 13/13
   en 5c (y lo mismo en 3a/3b/3c/4a/4b/4c). **0 DECLINE** en toda la sesión.
5. **Cierre del loop por tope**, con la convergencia **no acreditada** pero la
   **estabilización verificada mecánicamente**: la ronda 4 no aportó problemas
   de fondo nuevos de los revisores y la 5 los aportó solo en zonas reescritas
   por las rondas previas (10 de los 13 de `comprehension` fueron consecuencia
   directa de la 5a/5b).
6. **Informe de deriva**: se movió con `git mv` a `docs/2026-11-13_DRIFT_REPORT.md`
   y quedó enlazado desde el README («Subdirectories & System Boundaries»).
7. **Commit y push** del trabajo de las rondas 3-5 autorizados y ejecutados
   (`0ee82a5`).

---

## 3. Tabla de objetivos (estado al cierre del 2026-11-23)

**Sin cambios**: ninguna sesión de objetivos se tocó (igual que el 2026-11-18).
Tabla completa en `docs/HANDOFF_SESION_2026-11-10.md` §0. Resumen:

- ✅ Completos: **O1, O3, O7, O11, O12, O13, O14**; **Ola 6 · R1** y **6.2.1**.
- 🟢/🟡 Parciales: **O2** (O2.2 cerrado; semántica solo como ranking), **O5**
  (solo O5.3), **O6** (O6.4 slugs pendiente de decisión; O6.5 con posibilidad
  real), **O8** (solo O8.2), **O10** (falta refinar `solo_vigentes`).
- ❌ **O4** cerrado como *superseded*; ⏳ **O9** placeholder.
- ⏸ **Ola 6 · 6.1 / 6.3** (RAG consultivo + carta; embeddings *gated*)
  diferidas a decisión del usuario.

---

## 4. Cómo retomar

1. **El loop está cerrado**: no relanzarlo salvo que se reescriba una zona
   grande del README. Si se hace, el criterio práctico que funcionó es el de
   esta sesión: revisores **uno por vez, prompt corto**, un reintento, y
   **verificación mecánica propia** al final (barrido de `--help` + esquema).
2. **Leer** `goldfish_review_report.md` (678 líneas): tiene las 5 rondas con
   tabla de verificación por hallazgo y la sección «Estado del loop tras la
   ronda 5». Es la bitácora canónica del loop.
3. **Si se toca el README otra vez**, re-verificar las afirmaciones numéricas y
   de flags con `jobpulse-v15 --help` + `schema-version`: es lo que detectó los
   defectos A/B/P y el Blocker del CSV.
4. **Defecto de código pendiente** (decisión futura, fuera de esta sesión):
   `cli.py:659` — help del CLI con la ruta vieja de la BD. Corrección trivial
   (una cadena), pero exige tocar código + test.

---

## 5. Archivos clave

| Archivo | Estado |
|---|---|
| `README.md` (raíz) | **modificado** — 822 → **1187 líneas**; contrato raíz revisado (5 rondas) |
| `goldfish_review_report.md` (raíz) | **modificado** — rondas 1-5, tendencia 31 → 8 → 53 → 15 → 46 y estado del loop |
| `docs/2026-11-13_DRIFT_REPORT.md` | **movido** (`git mv` desde la raíz) y enlazado desde el README |
| `docs/HANDOFF_SESION_2026-11-23.md` | **nuevo** — este archivo |
| `docs/HANDOFF_SESION_2026-11-18.md` | contexto previo (rondas 1-2, contratos EGM) |
| `goldfish_review_report.md` §«Ronda 5» | detalle verificable de la ronda final |

---

## 6. Contexto

- **Modelo de la sesión**: `opencode/deepseek-v4.1-flash-free`.
- **Problemas del proveedor**: los subagentes siguen fallando por cuota
  (`codebase_details` necesitó **3 intentos** en la 5a; `style` y
  `comprehension` respondieron al primero). Los prompts largos disparan el
  *screening* también en este proveedor.
- **Los revisores NO ven lo que ve la verificación mecánica**: detectaron
  contenido, pero los defectos de forma/codificación (tildes, pipes en tablas,
  CJK, codificación por stdin) fueron todos **del autor**.
- **Patrón de defecto recurrente del autor**: **pequeñas corrupciones al
  reescribir en masa** (tildes, CJK, pipes). Si se vuelve a hacer una
  normalización masiva, verificar después con barridos (0 CJK, 0 `?`, tablas
  homogéneas).
- **Dos Pythons**: app/CLI → `.venv\Scripts\python.exe -X utf8`; tests → python
  del sistema. **No** se corrió la suite (no hubo cambios de código).
- **Git**: `origin/main` quedó en `0ee82a5` tras el trabajo de rondas 3-5;
  este handoff es un commit adicional, también pusheado.

---

## 7. Pendiente inmediato

1. **Nada del loop**: cerrado por tope. El README queda íntegro y verificado.
2. **Opcional / decisión del usuario**: corregir el help de `cli.py:659`
   (ruta de la BD) — es el único defecto **de código** que dejó esta sesión, y
   se dejó a propósito.
3. **Siguiente sesión de objetivos**: retomar Ola 6 · 6.1/6.3 (RAG + carta,
   embeddings *gated*) o los parciales O6.4/O8.2/O10, según decida el usuario.
