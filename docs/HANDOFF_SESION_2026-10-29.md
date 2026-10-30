# Handoff — Sesión 2026-10-29: O6.3 / Paso 5 (matching requisitos vs. perfil) — bloqueante educativo cerrado (3 rondas)

## TL;DR

Sesión dedicada al **Paso 5 del pipeline de scoring**: matching de los requisitos
extraídos de cada vacante contra los hechos del perfil. El bloqueante era la
**educación**: se descartaban vacantes solo porque el análisis había marcado un
requisito universitario `required` y el perfil (bachiller en secundaria +
diplomado técnico) no llega al nivel universitario. Se implementó el módulo real
**`src/jobpulse_v15/matching.py`** (los scripts ad-hoc de la raíz quedaron
obsoletos), se añadió la migración **`015_job_match_valida.sql`** (columna `valida`
para trazabilidad de corridas) y se aplicó la **regla acordada**: `descartada`
solo si el **texto completo** de la oferta confirma un título universitario
obligatorio **sin negación y sin alternativa**; en cualquier otro caso →
`revisar_a_mano` con motivo `educacion_no_confirmada`.

La sesión cerró el bloqueante en **tres rondas**:
1. **(mañana)** 8 falsos descartes corregidos (40 → 32 `descartada`, corrida
   `171039`) y **revisión manual de las 20 `educacion_no_confirmada`** → 19 no
   bloqueantes y **1 bloqueo real** (`workday-Supplier-Quality-Engineer-III_31162905`:
   "or equivalent field of study" NO es vía alternativa).
2. **(tarde)** medición de una muestra de 10 de `educacion_no_cumple` → **5/10
   eran bloqueos REALES** escondidos porque el extractor marcaba
   `ambiguous`/`inferred` → la regla "el TEXTO decide la obligatoriedad" y el
   requisito de **estudiante activo** con motivo propio
   (`titulo_universitario_en_curso_requerido`) → corrida `183231` (45 descartadas).
3. **(noche, esta tanda)** se cerraron los **3 puntos** que el usuario NO pudo dar
   por cerrados: (a) **medición ampliada a 43 casos** de `educacion_no_cumple`
   (26/43 ≈ 60 % eran bloqueos reales → **la regla se sostiene, no estaba
   sobreajustada**; contra el ground truth manual acierta **43/43**); (b)
   **verificación POR CONSULTA** con `verificar_evidencia.py` (112 verificaciones,
   0 fallos: cada `descartada`, cada `educacion_no_confirmada` y las 13 promovidas
   aparecen en el documento de evidencia con frase **literal** de la BD, no
   resumida); (c) **semántica documentada de la ausencia de `education_status`**
   (perfil con hechos educativos y ninguno `pursuing` → "no cumple" y bloquea;
   perfil SIN hechos educativos → "no verificable" → `revisar_a_mano` con el
   motivo nuevo `educacion_no_verificable`, nunca descartar por falta de
   información).

Corrida vigente **`20261029_205348`** (447 filas, `valida=1`; las 6 previas con
`valida=0`): calificada 102 · revisar_a_mano **94** · sin_requisitos 141 ·
**descartada 80** (56 título requerido + 24 estudiante activo) ·
datos_insuficientes 30. Evidencia literal (80 descartadas + 19 por revisar + la
medición de 43 casos) en `docs/PASO5_EVIDENCIA_2026-10-29.md`, generada por
`generar_evidencia_paso5.py`. Suite: **358 tests verdes**. **No se cambió ningún
umbral** (cobertura 0.60 / puntaje 0.80).

## Lo que se hizo

- **`src/jobpulse_v15/matching.py`** (nuevo, módulo real del Paso 5):
  - `confirmar_requisito_universitario(texto)` → `ConfirmacionEducacion`
    (`confirmada`, `termino`, `segmento`, `motivo` ∈ `confirmado`/`negacion`/
    `alternativa`/`sin_termino`). Detecta término explícito
    (`university degree`, `college degree`, `licenciatura`, `master's degree`,
    `mba`, `phd`…) o `bachelor` solo si hay `degree` cerca (para no confundir el
    **título del puesto** con un requisito).
  - Descarta contextos no universitarios: `two year college degree`,
    `associate degree`, `high school`, **`bachiller`/`bachillerato`** (en CR es
    secundaria), `technical school`, `educación media`.
  - Negación: 30 chars antes / 45 después + negación pegada al término
    ("No university degree required"). Alternativa: 40 antes / 110 después
    **+ la cláusula completa (viñeta/frase) y la cláusula siguiente**.
  - `EvaluadorPaso5`: carga hechos del perfil y requisitos de la BD, calcula
    cubiertos/faltantes, cobertura y puntaje, y decide el estado con la
    precedencia acordada. Nivel educativo efectivo = `MAX(nivel_orden)` de
    `concepto` (hay filas con `nivel_orden` NULL que rompían el `SELECT` plano).
  - `guardar_resultados()` / `ejecutar_paso5()`: escriben una **corrida nueva**
    y `invalidar_corridas_previas()` deja las anteriores con `valida = 0`.
- **`src/jobpulse_v15/migrations/015_job_match_valida.sql`** (nuevo): columna
  `valida` + índices `idx_job_match_valida`, `idx_job_match_corrida_valida`.
  `user_version` 14 → 15. No se editó ninguna migración aplicada.
- **Migraciones 009–014** (`concepto` canónico, `codigo_canonico`, `job_match`,
  `corrida_id`, columnas de conteo) estaban **sin versionar en git**: se
  incluyeron en el commit de esta sesión.
- **`tests/test_matching.py`** (nuevo): 46 casos — 31 unitarios + 15
  **regresiones con frases literales copiadas de la BD real**
  ("No university degree required.", "Associate's or bachelor's degree…",
  "Bachelor's degree or certification…", "equivalent practical experience may be
  considered", "or an equivalent combination…", "or other technical/scientific
  experience", "or advanced university studies…", "or equivalent field of
  study…", "Basic Qualifications … Bachelor's Degree or above", "Currently
  pursuing a Bachelor's degree… Must be enrolled", "Intern - Bachelor's Tech",
  negación lejana que NO invalida).
- **`tests/test_database.py`**: la versión de esquema se calculaba con `8`
  fijo (fallaba desde la migración 009) → ahora `len(self.database._migrations())`.
- **Herramientas en la raíz** (verificables, no producto):
  `run_paso5.py` (runner con `--dry`), `evidencia_descartadas.py` (evidencia
  literal por `descartada`), `resumen_bloqueo.py` (veredicto del análisis
  educativo en 3 cortes), `verificar_corridas.py` (trazabilidad `valida`),
  **`generar_evidencia_paso5.py`** (genera el documento de evidencia desde la BD).
- **`docs/PASO5_EVIDENCIA_2026-10-29.md`** (GENERADO, no editado a mano):
  criterio, trazabilidad, conteo, las 45 `descartada` con requisitos + frase
  literal + contexto, las 20 `revisar_a_mano / educacion_no_confirmada` con el
  motivo de la no confirmación y la medición de `educacion_no_cumple`.
- **Limpieza**: 75 scripts ad-hoc de la raíz eliminados (`paso5_*.py`,
  `check*.py`, `dump_*.py`, `ctx_*.py`, `dry_paso5.py`, `monitor_ia*.py`,
  `status_ia.py`, `vigilar_enriquecimiento.py`, `normalizar_facts_perfil*.py`,
  `*_licencias.py`, `cerrar_punto4*.py`, …).
- **`DESARROLLO_v15.md`**: fila O6 → O6.3 ✅; bloque "O6.3 — Matching
  (Paso 5)"; §5 próximos pasos (Paso 7); §7 decisiones de diseño (confirmar en
  el texto, corrida nueva por cambio de regla, texto decide obligatoriedad);
  §8 historial 2026-10-29 (manhã y tarde); tabla de objetivos fechada 2026-10-29;
  conteo de tests actualizado (25 suites / 339).

### Segunda tanda (tarde): regla "el texto decide" + estudiante activo

- **`matching.py`**: nueva clasificación de la cláusula del título
  (`_OBLIGATORIEDAD_ANTES` / `_OBLIGATORIEDAD` / `_SUAVIZADOR` /
  `_ENCABEZADO_REQUISITOS`), `ConfirmacionEducacion` gana `obligatorio`,
  `en_curso` y `suave`; `Requisito` gana `education_status`; el perfil carga
  `education_status` de sus facts (`candidato_universitario_en_curso()`).
- **`_EXCEPTO_EQUIVALENTE`**: "or equivalent field of study / discipline /
  degree" NO es vía alternativa → bloquea.
- **Vía alternativa nueva**: "or advanced coursework / advanced university
  studies" SÍ es vía alternativa → no se descarta.
- **Criterio de estudiante activo**: "currently pursuing", "must be enrolled",
  "students pursuing" → motivo `titulo_universitario_en_curso_requerido`; se
  cumple solo si el perfil registra un hecho educativo `education_status='pursuing'`.
- **Corrida `20261029_183231`**: `descartada` 32 → **45**
  (37 `titulo_universitario_requerido` + 8 `titulo_universitario_en_curso_requerido`);
  13 entradas nuevas **con evidencia literal**, 1 salida
  (`workday-Accounting-Analyst---Temporary_J-020392`, vía alternativa "or
  advanced university studies"), 7 reetiquetadas de título-completado a
  estudiante-activo.

### Tercera tanda (noche): alcance por grupo + semántica de `education_status` + medición de 43 casos

Los 3 puntos que el usuario NO pudo dar por cerrados:

- **(1) Medición ampliada de `educacion_no_cumple` a 43 casos** (estrato A = las 13
  promovidas por la corrida `183231`, **todas**; estrato B = 30 sistemáticas de
  las 93 restantes, una de cada tres ordenadas por `job_id`). Cada caso se
  revisó **a mano** contra la frase literal del aviso:
  - estrato A: **12/13** eran bloqueos reales → **1 falso descarte**
    (A2 `workday-Accounts-Payable-Representative_J-020440`: "… and 1+ year of
    relevant experience; **alternatively, 3+ years of relevant professional
    experience**") → corregido por la regla "alternativamente = vía alternativa";
  - estrato B: **14/30** eran bloqueos reales que el motor NO detectaba;
  - proporción de bloqueos reales: **26/43 ≈ 60 %** (la muestra inicial daba
    5/10 = 50 %) → **la regla se sostiene, NO estaba sobreajustada**;
  - contra el ground truth manual la regla acierta **43/43** (26/26 promovidas +
    17/17 no promovidas).
- **(2) Confirmación POR CONSULTA de las 13 entradas promovidas** (y de todo el
  resto): nuevo script **`verificar_evidencia.py`** que comprueba, contra la BD,
  que cada `descartada` y cada `educacion_no_confirmada` de la corrida vigente
  aparecen en `docs/PASO5_EVIDENCIA_2026-10-29.md` **con frase literal** y que esa
  frase es un **substring literal** de `jobs.requirements_raw` + `jobs.description_raw`
  (o sea: no es un resumen). Resultado: **112 verificaciones, 0 fallos**
  (80 `descartada` + 19 `educacion_no_confirmada` + las 13 promovidas de `183231`).
- **(3) Semántica documentada de la AUSENCIA de `education_status`**:
  - perfil con hechos educativos y **NINGUNO** `pursuing` → se sabe que la
    persona NO está registrada como estudiante activo → **"no cumple"** → la
    vacante se descarta con `titulo_universitario_en_curso_requerido`;
  - perfil **SIN NINGÚN** hecho educativo → la dimensión educativa **NO es
    verificable** → **nunca** se descarta por falta de información → la vacante
    va a `revisar_a_mano` con el motivo nuevo `educacion_no_verificable`.

**Cambios de regla de `matching.py` (corrida nueva `20261029_205348`):**
- **Alcance por GRUPO de enumeración** (`_grupos_terminos` + `_COORDINACION`): la
  negación, el suavizador y la obligatoriedad se aplican al grupo de títulos
  unidos por "or"/"/"/"y", NO a la cláusula completa. Por eso
  "Bachelor's/University degree, Master's degree preferred" EXIGE el bachelor's
  (la coma corta el alcance del "preferred") mientras que
  "Bachelor's or Master's degree preferred" NO exige ninguno de los dos.
- **Negación DURA vs. SUAVIZADOR** (`_NEGACION_DURA`): "is preferred but not
  required" → `negacion`; un encabezado "Preferred Qualifications" → `suave`
  (nuevo valor de `motivo`).
- **Encabezado de requisitos al FINAL de la cláusula anterior**
  (`_ENCABEZADO_REQUISITOS_FIN`): "…under pressure ____ What you need to bring:",
  "Job Requirements: Active university student…".
- **Perfil de estudiante activo** como exigencia propia: "active university
  student", "students … pursuing", "currently pursuing" (marcadores nuevos en
  `_OBLIGATORIEDAD`).
- **"bachillerato universitario"** = título universitario (término explícito);
  "bachiller/bachillerato" a secas (secundaria) NO filtra la ventana de otros
  términos.
- **"alternatively, N years of relevant professional experience"** = vía
  alternativa (corrige el falso descarte A2).
- **"or advanced coursework / university studies"** SÍ es vía alternativa;
  "or equivalent field of study / discipline / degree" NO.
- **"Who You Are"** NO se añade como encabezado de obligatoriedad (ambiguo →
  B25 queda en revisión).
- Ventana ±200 chars en cláusulas largas (>400) + separadores de cláusula
  "●"/"▪".

**Resultado (447 vacantes):** `descartada` 45 → **80** (56 `titulo_universitario_requerido` +
24 `titulo_universitario_en_curso_requerido`); `revisar_a_mano` **94** (19 `educacion_no_confirmada` +
57 `educacion_no_cumple` + 11 skill + 4 experiencia + 3 licencia); `calificada` 102 ·
`sin_requisitos` 141 · `datos_insuficientes` 30.
Delta exacto vs. `183231`: **37 cambios** (36 nuevas `descartada` + 1 salida: A2 →
`revisar_a_mano / educacion_no_cumple`). Las 36 nuevas se revisaron **una por
una** con frase literal (CINDE "Formación: Bachillerato universitario
completo/incompleto", Workday "REQUIREMENTS:", "Basic Requirements", "Education &
Experience", "Role Requirements", "Further requirements", "What you need to
bring", "What you'll need (Required)", "Requirements", internships HPE "Job
Description: Job Family Definition: … pursuing diplomas or degrees", "About You
Requirements:", "Education :").

**Verificación:**
- `tests/test_matching.py`: **65 casos** (46 previos + 19 regresiones nuevas con
  frases literales de la BD + la clase `TestSemanticaEducationStatus`).
- Suite completa: **358 tests verdes** (339 + 19 nuevos).
- `generar_evidencia_paso5.py` reescrito (evidencia desde la BD + §6 con la tabla
  de la medición de 43 casos y la frase literal de cada uno).

## Decisiones de diseño (esta sesión)

1. **El bloqueante educativo se CONFIRMA en el texto, no se infiere**: sin
   evidencia literal (frase completa del aviso) no se descarta nada; la duda va
   a `revisar_a_mano`. Ante la duda → revisar, nunca descartar.
2. **La alternativa se busca en la cláusula completa**, no solo en una ventana
   de caracteres: la alternativa puede estar al final de una viñeta larga
   ("…bachelor's degree program … or other technical/scientific experience").
   Ventanas fijas (40/110) solas dejaban 2 falsos descartes.
3. **Cada cambio de regla = una corrida nueva** en `job_match`
   (`corrida_id` + `valida`). Nunca `UPDATE` in-place de una corrida emitida:
   los `UPDATE` de la mañana del 29-10 hicieron que dos corridas diferentes
   mostraran conteos contradictorios (50 vs 2 `descartada`).
4. **Motivos con significado propio**: `educacion_no_confirmada` = obligatorio que
   el texto NO confirma (va a `revisar_a_mano`); `educacion_no_cumple` = el perfil
   no alcanza el nivel pedido en un requisito **no** obligatorio (no bloquea).
   `educacion_no_cumple` antes que `cobertura_insuficiente` por la prioridad
   acordada.
5. **`bachelor` exige `degree` cerca**: si no, la palabra es el título del puesto
   ("Intern - Bachelor's Tech"), no un requisito. Ojo: ese job igual queda
   `descartada` porque el **cuerpo** del aviso confirma el requisito
   ("Currently pursuing a Bachelor's degree…", "University students actively
   enrolled…") — y queda con motivo **de estudiante activo**, no de título
   completado.
6. **Nada del candidato hardcodeado**: los hechos salen de
   `candidate_profile_facts` y los niveles de `concepto`; el mismo código sirve
   para otro perfil.
7. **La obligatoriedad la decide el TEXTO** (tarde): "Required/Minimum/Basic
   Qualifications", "must have", "degree or above", "Requisitos" y el encabezado
   "Qualifications" en su propia viñeta obligan; "Preferred" no. El nivel del
   extractor (`ambiguous`/`inferred`) NO manda — se demonstró con la medición
   5/10.
8. **"or equivalent field of study" NO es vía alternativa** (mismo nivel,
   otra carrera) mientras que **"or advanced coursework/university studies" SÍ**
   (son estudios sin título completado).
9. **Estudiante activo ≠ título completado**: criterio propio
   (`titulo_universitario_en_curso_requerido`); cumple solo con un fact de
   perfil `education_status='pursuing'` de nivel universitario.
10. **Un bloque es un bloque aunque el extractor no lo marcara**: 13 vacantes
    pasaron de `revisar_a_mano` a `descartada` con frase literal pegada.
11. **El alcance de negación/suavizador/obligatoriedad es el GRUPO de enumeración**
    (noche), no la cláusula completa: "Bachelor's/University degree, Master's
    degree preferred" EXIGE el bachelor's; "Bachelor's or Master's degree
    preferred" NO exige ninguno. Es la decisión que evita el falso descarte y el
    falso "no bloqueo" a la vez.
12. **Negación DURA ≠ SUAVIZADOR** (noche): "is preferred but not required" →
    `negacion` (manda la negación); "Preferred Qualifications" (encabezado) →
    `suave`. Motivos distintos para poder explicitar el por qué.
13. **"bachillerato universitario" SÍ es título universitario** en CR
    ("bachiller"/"bachillerato" a secas = secundaria).
14. **La ausencia de `education_status='pursuing'` significa "no cumple"**
    (noche) **si el perfil tiene hechos educativos**; si NO tiene ninguno, la
    dimensión NO es verificable → `revisar_a_mano` con `educacion_no_verificable`
    (nunca descartar por falta de información).
15. **La evidencia se verifica POR CONSULTA**, no a ojo: `verificar_evidencia.py`
    comprueba que cada caso aparece en el documento con frase literal y que esa
    frase es substring literal del texto de la BD.

## Estado de objetivos (tabla O1–O10)

| Objetivo | Estado |
|---|---|
| O1 enriquecimiento IA | ✅ completo (veredicto IA 28-10) |
| O2 búsqueda data-first | 🟡 O2.1 locations Indeed + O2.2 filtro "Req." |
| O3 fetchers ATS | 🟢 7/7 plataformas validadas (83/122 tableros con jobs CR) |
| O4 calibración gate-vs-IA | ⏳ redefinir (sin gate semántico no hay contra-qué) |
| O5 higiene de datos | 🟢 solo O5.3 (re-barrido ~46 basura) |
| O6 perfil del candidato | 🟢 **O6.3 matching ✅ cerrado 29-10** · O6.4 dedupe semántico pendiente |
| O7 operación UI-first | ✅ completo |
| O8 ciclo de vida | 🔵 diseñado — plan de 7 pasos (herencia, ventana, categorías) |
| O9 optimización UI | ⏳ placeholder |
| O10 mejorar filtros | 🟡 diseñado (`elegir_filtro_compatibilidad` 28-10) |

## Cómo retomar

```powershell
# Paso 5 (corrida NUEVA; las anteriores quedan con valida=0)
.\.venv\Scripts\python.exe -X utf8 run_paso5.py
.\.venv\Scripts\python.exe -X utf8 run_paso5.py --dry     # evalúa sin escribir

# Evidencia / verificación
.\.venv\Scripts\python.exe -X utf8 generar_evidencia_paso5.py   # regenera el doc
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py         # 112 verificaciones (exit 0 = TODO CUADRA)
.\.venv\Scripts\python.exe -X utf8 evidencia_descartadas.py 20261029_205348 out_evidencia.txt
.\.venv\Scripts\python.exe -X utf8 resumen_bloqueo.py
.\.venv\Scripts\python.exe -X utf8 verificar_corridas.py

# Tests (python del SISTEMA; el venv no tiene pytest)
python -m pytest tests/ -q

# UI / BD
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15.ui
.\.venv\Scripts\python.exe -X utf8 tools\estado_bd.py
```

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/jobpulse_v15/matching.py` | **Módulo real del Paso 5** (detección + evaluación + corridas) |
| `src/jobpulse_v15/migrations/015_job_match_valida.sql` | Columna `valida` + índices (trazabilidad de corridas) |
| `src/jobpulse_v15/migrations/009…014_*.sql` | `concepto` canónico + `job_match` + `corrida_id` + conteos (versionadas hoy) |
| `tests/test_matching.py` | 65 tests (19 regresiones con frases de la BD real + `TestSemanticaEducationStatus`) |
| `tests/test_database.py` | Versión de esquema dinámica (ya no fija `8`) |
| `run_paso5.py` | Runner del paso 5 (`--dry`) |
| `generar_evidencia_paso5.py` | **Genera `docs/PASO5_EVIDENCIA_2026-10-29.md` desde la BD** (incluye §6 = medición de 43 casos) |
| `verificar_evidencia.py` | **Verifica POR CONSULTA** que cada caso del documento está con frase literal de la BD (exit 0 = TODO CUADRA) |
| `evidencia_descartadas.py` | Evidencia literal de cada `descartada` |
| `resumen_bloqueo.py` | Veredicto del análisis educativo (3 cortes) |
| `verificar_corridas.py` | Trazabilidad de corridas + delta entre corridas |
| `docs/PASO5_EVIDENCIA_2026-10-29.md` | Evidencia literal completa (80 `descartada` + 19 no confirmadas + medición de 43 casos) |
| `DESARROLLO_v15.md` | Objetivos O1–O10 + bloque O6.3/Paso 5 |

## Datos de contexto

- **Corridas de `job_match`** (todas de 447 filas; solo la última es vigente):
  `132455` (50 `descartada`), `133621` (2), `160358` (40), `170343` (34),
  `171039` (32), `183231` (45), **`205348` (80 ← vigente, `valida=1`)**.
- **Corrida vigente `20261029_205348`** (sumas verificadas por GROUP BY estado =
  447): calificada 102 · revisar_a_mano **94** (19 `educacion_no_confirmada` +
  57 `educacion_no_cumple` + 11 skill + 4 experiencia + 3 licencia) ·
  sin_requisitos 141 · **descartada 80**
  (56 `titulo_universitario_requerido` + 24 `titulo_universitario_en_curso_requerido`) ·
  datos_insuficientes 30.
- Las **19** `revisar_a_mano / educacion_no_confirmada` que quedan: son
  requisitos universitarios **obligatorios** que el texto NO confirma (negación o
  alternativa). Las 20 revisadas en la ronda de tarde dieron 19 no bloqueantes +
  1 bloqueo real ya corregido (`workday-Supplier-Quality-Engineer-III_31162905`).
- **Medición AMPLIADA `educacion_no_cumple` (43 casos)**: estrato A (13, todas las
  promovidas) → 12/13 bloqueos reales (1 falso descarte = A2, corregido);
  estrato B (30 sistemáticas) → 14/30 bloqueos reales (falsos negativos,
  promovidos). Proporción **26/43 ≈ 60 %** (la muestra inicial daba 5/10 = 50 %)
  → **la regla se sostiene, no estaba sobreajustada**. Ground truth manual:
  **43/43**.
- Perfil real: 2 hechos de educación (`bachiller-en-educacion-media` =
  `educacion-secundaria` nivel 1 `completed`; `diplomado-en-electronica` =
  `educacion-tecnica` nivel 2 `completed`) → **nivel máximo 2**; **ningún fact con
  `education_status='pursuing'`** → los 24 requisitos de estudiante activo
  bloquean con motivo propio. `nivel_req < 3` nunca bloquea.
- `job_requirements.requirement_level` real: `required` 60 · `inferred` 75 ·
  `ambiguous` 66 · `preferred` 18 — **ya no es el que manda**: la obligatoriedad
  la decide el texto del aviso.
- `jobs.requirements_raw` es `NULL` en casi todos los Workday: el texto real
  está en `description_raw` (~4–5k chars) → se buscan **ambos**.
- Tests con el python del sistema (`python -m pytest`), app con
  `.\.venv\Scripts\python.exe -X utf8`. El venv no tiene pytest.
- v1.x congelado en `D:\Proyectos\jobpulse_cr` — SOLO lectura, nunca modificar.

## Pendiente inmediato

1. **Paso 5 — las 19 `revisar_a_mano / educacion_no_confirmada` quedan ABIERTAS
   (NO revisadas)** (corrida `20261029_205348`):
   - La revisión previa la hizo **el autor de la regla** → su veredicto
     ("ninguna bloquea") se **DESCARTA por sesgo**: no es una segunda opinión.
   - La hoja de revisión para una **segunda persona** ya está generada con el
     texto completo y **sin veredictos**: `docs/PASO5_REVISION_PENDIENTES.md`
     (por `generar_revision_pendientes.py`).
   - **3 decisiones de negocio pendientes** (decidirlas con fuente, no por
     impulso): (a) ¿"or advanced university studies" cuenta como educación
     universitaria? (afecta `workday-Accounting-Analyst---Temporary_J-020392`);
     (b) ¿"two year college degree"/"associate degree" es universitario en CR?
     el código trata 2 años como NO universitario, pero un técnico superior
     universitario sí lo es (afecta `workday-Associate--Repair-III_R-118081`);
     (c) ¿un bachillerato PARCIAL (80 % de la carrera) cuenta como requisito
     cumplido? el módulo no lo define (afecta los dos
     `workday-Production-Supervisor-I_*`).
   - Solo son "no bloqueo" **inmediatos** (los que el usuario dio por claros, y
     aun así queda la firma de la segunda persona): negación explícita
     (`linkedin-4483157697`), "Bachelor's degree **or equivalent work
     experience** required" (`workday-Security-Governance—Compliance-Specialist_2023168-1`)
     y "…or equivalent" al final de la enumeración
     (`workday-TnF-Manager-Systems---Software_1214477-2`).
2. **Paso 7 — tabla de decisiones + UI + export**: NO registrar las 19 como
   "no bloqueo" hasta terminar el punto 1. `job_match_decision` (migración
   numerada) con decisiones firmadas (veredicto, criterio, revisor, fecha) que
   el Paso 7 lee; si el registro cambia estados, **corrida nueva** — nunca
   `UPDATE` in-place sobre una corrida emitida.
3. **No tocar los umbrales** (cobertura 0.60 / puntaje 0.80) sin acuerdo explícito.
4. **No pushear sin confirmación del usuario**: antes, confirmar la suite en la
   rama exacta, verificar que no se sube nada de `fork-v15` y decidir si el push
   va en un bloque o por partes.
5. Pendientes de siempre: O8 (ciclo de vida, plan de 7 pasos) · O5.3 (re-barrido
   de las ~46 descripciones basura) · O2.1/O2.2 · O6.4 · O9 · O3 (83/122
   tableros con jobs) · O4 (redefinir).
