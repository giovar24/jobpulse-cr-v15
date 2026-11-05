# Handoff — Sesión 2026-11-04 (mediodía)

**TL;DR**: Implementado el **motor de VIABILIDAD** (ajuste técnico 0-100 +
bandas), el módulo de **POSTULACIONES** (estado del proceso: correo IMAP +
"Mis postulaciones" de Workday) y la **CAPA B** (el perfil ya lleva
`codigo_canonico`). Migraciones `017`–`019` aplicadas en la BD real
(esquema 16 → 19, **solo aditivas**). Suite: **846 tests verdes + 241
subtests**. Commits **pusheados** a `origin/main` (con confirmación del
usuario). El backfill de la capa B en la BD real es un **no-op**: no se
corrió.

> ⚠️ **La BD real sí cambió** (ver §2.7): al correr `postulaciones list` el
> CLI aplicó las migraciones pendientes (es su comportamiento habitual:
> `Database.initialize()` al abrir la base). Se auditó el cambio completo:
> nada se borró, `integrity_check` ok y 0 violaciones FK. Además se cambió
> el CLI para que **avise** cuando migra (ya no es silencioso).

---

## 1. La decisión que ordena todo lo demás

> **Ser rechazado de un trabajo NO significa que no se es apto para él.**
> (corrección del usuario, 2026-11-04)

El reclutador humano decide por presupuesto, timing, competencia, sesgos y
azar. Antes de esta sesión el proyecto mezclaba dos cosas distintas. Ahora
están **separadas de punta a punta**:

| | Qué es | Módulo | Para qué sirve |
|---|---|---|---|
| **Ajuste técnico** | ¿el perfil cumple lo que pide el aviso? | `viabilidad.py` | priorizar a dónde postular |
| **Estado del proceso** | ¿qué decidió el reclutador? | `postulaciones.py` | no reprocesar lo postulado · medir el funnel propio · revisar posibles falsos positivos del ranking |

**Consecuencia de diseño:** el score **NUNCA** se entrena con rechazos
(serían etiquetas de aptitud ruidosas y sesgadas). Los rechazos son señal
operativa y contexto. El score es determinista, auditable y explicable.

---

## 2. Lo que se hizo

### 2.1 Motor de VIABILIDAD (`src/jobpulse_v15/viabilidad.py`)

Índice de **ajuste técnico** 0-100 + banda. Inspirado en los ATS modernos
(Workday Skills Based Hiring, Greenhouse/Lever, HireVue/Paradox).

- **Bandas**: `aplicar` (≥85) · `revisar` (80-85) · `no_prioritario` (<80) ·
  `sin_datos` · `veto`.
- **Tope duro**: si falta ≥1 requisito `required` → banda máxima `revisar`
  (nunca `aplicar`, aunque el score sea 100). `preferred` no bloquea;
  `ambiguous`/`inferred` pesan como "incierto" (1.0) y no activan el tope.
- **Pesos por categoría**: skill 0.40 · education 0.25 · experience 0.15 ·
  language 0.10 · license 0.10 · semántica 0.15 (componente ruidoso: ordena,
  no define banda). **Peso interno**: obligatorio 2.0 · incierto 1.0 ·
  deseable 0.5.
- **DOS PASADAS con imputación del corpus** (misma regla que el ranking ATS,
  gotcha 26): la primera calcula los componentes de cada vacante y el
  promedio del corpus; la segunda puntúa con pesos **fijos** imputando el
  promedio a lo que no tiene dato. **Sin esto el score era degenerado**
  (50 de 50 vacantes con ajuste 100: casi todos los requisitos carecen de
  `codigo_canonico`).
- **Vetos**: `fuera_de_area` (reutiliza `areas.es_fuera_de_area` → `otros` y
  las sin clasificar **nunca** se vetan) y `titulo_universitario_requerido`
  (texto confirmado). Licencia sin comparación → `no_verificable` (no
  penaliza).
- **Reutiliza `matching.EvaluadorPaso5`** → no duplica la regla dura del
  texto (obligatoriedad, idioma del aviso, educación).
- **No toca** los umbrales congelados del Paso 5 (0.60/0.80) ni los estados
  de `job_match`: es un índice **paralelo**.
- Tests: `tests/test_viabilidad.py` (12).

**Calibración real** (copia de la BD, 535 avisos, sin semántica):

| Banda | Vacantes |
|---|---|
| aplicar | 5 |
| revisar | 17 |
| no prioritario | 284 |
| sin datos | 142 |
| veto | 87 |

Lectura honesta: el corpus tiene **poca señal por requisito** (49 skills y 29
licencias sin `codigo_canonico`), así que muchas vacantes quedan en
`sin_datos` o se puntúan con la imputación. Los pesos son **priors
documentados**, no pesos aprendidos (aún no hay ground truth propio).

### 2.2 POSTULACIONES (`src/jobpulse_v15/postulaciones.py` + colectores)

- **Núcleo puro** (21 tests): `Senal`, `clasificar`, `clasificar_mensajes`,
  `portal_del_remitente`, `referencia_de_url`, `estado_mas_avanzado`.
- **Estados** alineados con `applications.application_status`: `applied` ·
  `recruiter_contact` · `interview` · `offer` · `rejected` · `withdrawn`.
  **El avance nunca se degrada**: un `interview` posterior no vuelve a
  `rejected`.
- **Persistencia** (migración `018`): `postulacion_senal` (bitácora, una fila
  por notificación) + `postulacion` (estado actual por vacante). Métodos en
  `Repository`: `registrar_senales_postulacion`, `listar_senales_postulacion`,
  `listar_postulaciones`, `estado_postulacion_por_job`.
  **Privacidad**: del correo/portal solo se guardan derivados mínimos (estado,
  fecha, remitente, asunto, referencia del aviso). **El cuerpo nunca se
  guarda.**
- **Casado con el corpus**: por `source_job_id` (REQID de Workday) o por
  `source_url` normalizada (sin query ni fragmento).
- **`correo_postulaciones.py`** (12 tests, nunca red): lector IMAP de Gmail
  (`X-GM-RAW` con fallback `SINCE`), credencial por
  `credenciales.credencial("gmail")` (keyring). `fabrica_imap` inyectable
  para los tests.
- **`workday_postulaciones.py`** (13 tests): parsers **puros** (JSON + HTML)
  y fetch por **CDP** de "Mis postulaciones" (reutiliza la sesión del
  navegador; el fetcher NUNCA crea un navegador).

### 2.3 CAPA B — el perfil ya lleva `codigo_canonico`

Antes, `candidate_profile_facts.codigo_canonico` quedaba NULL → el motor
(filtra `codigo_canonico IS NOT NULL`) **ignoraba el perfil**.

- `Repository.save_candidate_profile_fact` / `import_candidate_profile_facts`
  resuelven el código **al guardar** (misma regla que los requisitos:
  `conceptos.resolver`).
- `Repository.backfill_candidate_profile_canonico()`: rellena solo los NULL
  (idempotente, no destructivo).
- CLI: `enrich profile-canonico [--apply]` (simulación por omisión).
- **Fallback slug ↔ texto** (`conceptos._variantes_alternas`): el importador
  de CV produce slugs (`active-directory`) y la taxonomía está en texto
  natural (`active directory`) → son la misma variante.
- **La cola del perfil solo recibe CONCEPTOS**
  (`conceptos.CATEGORIAS_PERFIL_CONCEPTO` = skill/language/license/education):
  los hechos de `experience` del CV son **títulos de puesto** ("Soporte
  Técnico") → quedan en NULL y **no** se encolan. Si un hecho de experience
  **sí** es un concepto (`years_experience` → `experiencia-anos`), recibe su
  código igual.

### 2.4 CLI

```
viabilidad list|top    --banda --limit --evaluar-todo --semantica
                        --format json|csv --output
postulaciones correo   --dias --host --puerto --carpeta --cred --apply
postulaciones workday  --site --port --apply
postulaciones list     --estado --format json|csv
enrich profile-canonico [--apply]
```

`postulaciones` es **dry-run por omisión** (hay que pasar `--apply`).

### 2.5 UI v2 (pestaña "Vacantes")

- `AtsStore` calcula la viabilidad junto al ranking ATS (comparten el
  percentil semántico: `ats.percentiles_semanticas` → un solo cálculo).
- Columnas **"Ajuste"** y **"Banda"**; combo de bandas; casilla **"Solo
  aplicar"**; franja de tiles por banda; detalle con "Ajuste técnico",
  "Banda" y "Faltantes obligatorios"; CSV ampliado.
- i18n es/en para los textos nuevos.

### 2.6 Migraciones (escritas, NO aplicadas en la BD real)

| Migración | Qué hace |
|---|---|
| `017_educacion_granular.sql` | master/MBA → posgrado (4) · associate degree / two year college degree → ciclo corto (2) · "bachiller" a secas → **secundaria** (1) en CR. (Era la 017 que estaba pendiente.) |
| `018_postulaciones.sql` | `postulacion_senal` + `postulacion`. |
| `019_google_workspace.sql` | Corrige un alias **erróneo**: `google-workspace` estaba mapeado a `microsoft-365` (son productos distintos). Solo se corrigen los que venían de esa variante; un `microsoft-365` legítimo no se toca. Agrega la variante `active-directory`. |

**Las tres están APLICADAS en la BD real** (esquema 19) — ver §2.7.

Tests: `tests/test_migraciones.py` (14) — la 019 se prueba **ejecutando el
SQL real** sobre un estado premigración reproducido a mano.

### 2.7 Cambio en la BD REAL (documentado y auditado)

Al correr `postulaciones list` para probar el comando, el CLI aplicó las
migraciones pendientes en `data/jobpulse_v15.db`: es su comportamiento
habitual (`cli.py` llama `Database.initialize()` al abrir la base, igual que
la UI clásica, la UI v2, los scrapers y los tools).

**Auditoría completa** (real vs. respaldo del 03-11 y vs. copia de las 11:23):

| Qué | Resultado |
|---|---|
| `jobs` / `job_requirements` / `job_analysis` / `job_match` / `source_sites` / `source_run_sites` / `candidate_profile_facts` / `concepto_no_normalizado` / `nivel_escala` | **conteos IDÉNTICOS** (535 / 1071 / 535 / 535 / 129 / 129 / 48 / 10 / 10) |
| `concepto` | 70 → **95** (+25 filas: 23 variantes educativas de la 017 + 2 de skill de la 019) |
| Tablas nuevas | `postulacion_senal` y `postulacion` (0 filas cada una) |
| Correcciones | 1: el hecho de perfil `skill/google-workspace` pasó de `microsoft-365` → `google-workspace` (la 019; 0 requisitos afectados) |
| Integridad | `PRAGMA integrity_check` = **ok** · `foreign_key_check` = **0 violaciones** |

**Nada se borró ni se fusionó**: solo filas nuevas de taxonomía, dos tablas
vacías y la corrección de un alias que estaba mal.

**Fix preventive**: el CLI ahora **avisa** cuando aplica migraciones
(`[esquema] Se aplicaron las migraciones N-M`) → una migración ya no se
aplica en silencio. Test en `tests/test_cli_viabilidad.py`.

**Pendiente**: NINGUNO. El backfill de la CAPA B (`enrich profile-canonico
--apply`) sería un **NO-OP** y **no se corrió** (decisión del usuario,
2026-11-04): la BD real ya tiene el perfil codificado donde corresponde
(skill 23/23 · language 2/2 · education 2/2 · `experience/total` = 16 años
leído por `numeric_value`) y los 9 hechos sin código son **títulos de
puesto** de `experience`, que por diseño quedan en NULL y **no** se
encolan. Verificado con el motor: ve 23 skills, 2 idiomas, 2 niveles
educativos, 16 años; `cumple excel/sql/ingles` = True.

---

## 3. Decisiones de diseño

| Tema | Decisión |
|---|---|
| Ajuste vs. proceso | **Separados**. El score nunca se entrena con rechazos. |
| Tope de banda | Falta 1 `required` → máximo `revisar`. Es el *knockout* de los ATS modernos. |
| Puntaje comparable | Dos pasadas + imputación del corpus (pesos fijos). Sin eso: score degenerado. |
| Semántica | Percentil del corpus, peso 0.15, **solo ordena** (no define banda). |
| `preferred` | No bloquea (misma regla dura del Paso 5). |
| `ambiguous`/`inferred` | "Incierto" (peso 1.0): pesa pero no activa el tope. |
| Veto de área | Reutiliza `areas.es_fuera_de_area`: `otros` nunca se veta. |
| Persistencia de señales | Solo derivados mínimos. El cuerpo del correo **nunca** se guarda. |
| Avance del proceso | Nunca se degrada (`estado_mas_avanzado`). |
| Cola del perfil | Solo conceptos; los títulos de puesto no la ensucian. |
| Peso vs. learned | Los pesos son priors documentados; se calibran con datos propios, no se entrenan con rechazos. |

---

## 4. Estado de objetivos (tabla)

| Objetivo | Estado | Nota |
|---|---|---|
| O1–O6 (pipeline scrape → matching) | Hecho (sesiones previas) | — |
| O7 (IA local/browser) | Hecho | — |
| O8/O10 (retención + diagnóstico) | Hecho | — |
| O2.2 (Req. + filtro) | **Hecho** (2026-11-04) | — |
| O3 (salud de sitios) | **Hecho** (2026-11-04) | — |
| **Capa B (`codigo_canonico` del perfil)** | **Hecho y efectivo en la BD real** | El backfill sería un no-op (decisión del usuario) |
| **Migración 017** | **Hecha y aplicada** (esquema 19) | — |
| **Motor de viabilidad (ajuste técnico)** | **Hecho** | Pesos = priors; falta ground truth propio |
| **Postulaciones (correo + Workday)** | **Hecho en código** | Falta validación en vivo (CDP + app-password) |
| `educacion_no_confirmada` | **ABIERTO** | Requiere firma de una 2ª persona |
| O5.3 (re-barrido descripciones basura) | Pendiente | — |
| O6.4 (dedupe slugs ES/EN) | Parcial | El resolver ya tolera slug↔texto |
| O4 | **Proponer cerrar como *superseded*** | El gate semántico ya no existe |
| O8.2 / O8.4 / O9 / pestañas nuevas UI v2 | Pendiente | — |

**Suite actual**: **846 passed + 241 subtests** (~3:05 min).

---

## 5. Cómo retomar (comandos)

```powershell
# Suite completa (python del SISTEMA)
python -m pytest tests/ -q

# Solo lo nuevo
python -m pytest tests/test_viabilidad.py tests/test_postulaciones.py `
  tests/test_postulaciones_persistencia.py tests/test_correo_postulaciones.py `
  tests/test_workday_postulaciones.py tests/test_perfil_canonico.py `
  tests/test_conceptos.py tests/test_migraciones.py tests/test_cli_viabilidad.py -q

# Viabilidad sobre una COPIA de la BD (NO sobre la real)
Copy-Item data\jobpulse_v15.db "$env:TEMP\opencode\viabilidad_test.db" -Force
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 `
  --db "$env:TEMP\opencode\viabilidad_test.db" viabilidad list --limit 0

# Capa B (simulación; luego --apply)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich profile-canonico

# Postulaciones (dry-run por omisión)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones correo --dias 90
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones workday

# UI v2
.\jobpulse-v15-v2.bat
```

---

## 6. Archivos clave

| Archivo | Qué es |
|---|---|
| `src/jobpulse_v15/viabilidad.py` | **(NUEVO)** Motor de ajuste técnico: bandas, pesos, imputación, vetos |
| `src/jobpulse_v15/postulaciones.py` | **(NUEVO)** Núcleo puro de señales del proceso |
| `src/jobpulse_v15/correo_postulaciones.py` | **(NUEVO)** Lector IMAP (Gmail) |
| `src/jobpulse_v15/workday_postulaciones.py` | **(NUEVO)** Parsers + fetch CDP de "Mis postulaciones" |
| `src/jobpulse_v15/repository.py` | Capa B (`_codigos_perfil`, backfill) + persistencia de postulaciones |
| `src/jobpulse_v15/conceptos.py` | Fallback slug↔texto + `CATEGORIAS_PERFIL_CONCEPTO` |
| `src/jobpulse_v15/ats.py` | `percentiles_semanticas` (semántica compartida CLI/UI) |
| `src/jobpulse_v15/cli.py` | Comandos `viabilidad`, `postulaciones`, `enrich profile-canonico` |
| `src/jobpulse_v15/ui_v2/data/vacantes.py` | `AtsStore` con viabilidad + filtros/tiles por banda |
| `src/jobpulse_v15/ui_v2/tabs/vacantes.py` | Columnas Ajuste/Banda, combo, "Solo aplicar", detalle |
| `src/jobpulse_v15/ui_v2/i18n.py` | Textos nuevos (es/en) |
| `src/jobpulse_v15/migrations/017_educacion_granular.sql` | **(NUEVO)** |
| `src/jobpulse_v15/migrations/018_postulaciones.sql` | **(NUEVO)** |
| `src/jobpulse_v15/migrations/019_google_workspace.sql` | **(NUEVO)** |
| `tests/test_viabilidad.py` | **(NUEVO)** 12 tests |
| `tests/test_postulaciones.py` | **(NUEVO)** 21 tests |
| `tests/test_postulaciones_persistencia.py` | **(NUEVO)** 8 tests |
| `tests/test_correo_postulaciones.py` | **(NUEVO)** 12 tests |
| `tests/test_workday_postulaciones.py` | **(NUEVO)** 13 tests |
| `tests/test_perfil_canonico.py` | **(NUEVO)** 14 tests (capa B + cola) |
| `tests/test_migraciones.py` | **(NUEVO)** 14 tests (017/018/019) |
| `tests/test_cli_viabilidad.py` | **(NUEVO)** 10 tests (CLI) |
| `tests/test_conceptos.py` | +6 tests (resolver slug↔texto) |
| `docs/MOTOR_VIABILIDAD.md` | **(NUEVO)** Referencia del motor |
| `AGENTS.md` | Secciones nuevas + gotchas 34-39 + estado de referencia |
| `DESARROLLO_v15.md` | Decisiones + historial + comandos |

---

## 7. Datos de contexto

- **BD real `data/jobpulse_v15.db`**: 535 avisos, **esquema 19** (migraciones
  017-019 aplicadas el 2026-11-04, ver §2.7), corrida Paso 5 vigente
  `20261103_155215` (calificada 173 · revisar 107 · sin_requisitos 129 ·
  descartada 87 · datos_insuf 39). 62 sitios resueltos. **La capa B ya es
  efectiva en la BD real** (el backfill sería un no-op).
- **Perfil real**: 23 skills (el `google-workspace` ya corregido por la 019),
  2 idiomas (espanol nativo, ingles B2), 2 educación (`bachiller-en-educacion-media`
  → educacion-secundaria, `diplomado-en-electronica` → educacion-tecnica),
  9 experience (value_code = **títulos de puesto**, no conceptos; sin código
  por diseño), 4 certificaciones, contactos y summary. **Sin título
  universitario** → causa las 87 descartadas.
- **Requisitos vigentes**: skill ambiguous 307 / required 10 / preferred 10;
  experience ambiguous 185 / required 42; language ambiguous 146 / required
  13; education inferred 80 / required 61 / ambiguous 75; license inferred
  25 / required 9. **Sin `codigo_canonico`: 49 skills + 29 licenses** → poca
  señal por requisito (motivo del score degenerado sin imputación).
- **"Req." = 0 no significa "sin requisitos"**: 122 de las 173 calificadas lo
  tienen (el Paso 5 decide por el texto).
- **Commits**: `8d5db3b` (O2.2+O3) · `5395c2b` (viabilidad + postulaciones +
  capa B) · `8936d0a` (docs) — **pusheados** a `origin/main` con la
  confirmación del usuario (2026-11-04).
- **CDP**: Brave debe correr con `--remote-debugging-port=9222` y el perfil
  real (raíz `User Data`, nunca `User Data\Default`).
- **Tests**: `python -m pytest tests/ -q` (python del SISTEMA); app/CLI con
  `.\.venv\Scripts\python.exe -X utf8`.

---

## 8. Pendiente inmediato

1. **Validación en vivo** de los colectores (necesita al usuario):
   - `postulaciones workday` → requiere Brave con CDP abierto:
     `.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones workday --apply`
   - `postulaciones correo` → requiere la app-password de Gmail en el
     keyring (credencial `gmail`):
     `.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones correo --dias 90 --apply`
2. **Firma de 2ª persona** de las `educacion_no_confirmada`
   (`docs/PASO5_REVISION_PENDIENTES.md`) — sigue ABIERTO.
3. **Calibración del motor** cuando haya postulaciones reales: comparar
   banda vs. resultado del proceso (el score **no** se reentrena con los
   rechazos; solo se ajustan los priors documentados).

> El backfill de la capa B **ya no es pendiente**: es un no-op (ver §2.7).

---

## 9. Commits de esta sesión

- `8d5db3b` — O2.2 + O3 (sesión previa).
- `5395c2b` — motor de viabilidad + postulaciones + capa B +
  migraciones 017-019 + CLI + UI v2 + tests.
- `8936d0a` — documentación (`docs/MOTOR_VIABILIDAD.md`, este handoff,
  `AGENTS.md`, `DESARROLLO_v15.md`).

**PUSHEADOS** a `origin/main` (`7f50596..8936d0a`) con la confirmación
explícita del usuario (2026-11-04).

---

*Sesión cerrada: 2026-11-04 mediodía. Commits pusheados a `origin/main`.*
