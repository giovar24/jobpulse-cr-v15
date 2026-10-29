# Handoff — Sesión 2026-10-29: O6.3 / Paso 5 (matching requisitos vs. perfil) — bloqueante educativo cerrado

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
`revisar_a_mano` con motivo `educacion_no_confirmada`. Resultado: **8 falsos
descartes corregidos** (40 → 32 `descartada`), corrida vigente
**`20261029_171039`** (447 filas, `valida=1`; las 4 corridas previas quedan con
`valida=0`). Evidencia literal de las 32 descartadas y de las 20 por revisar en
`docs/PASO5_EVIDENCIA_2026-10-29.md`. Suite: **324 tests verdes** (se arregló
`tests/test_database.py`, que fijaba la versión de esquema en `8` y ya fallaba
desde la migración 009). **No se cambió ningún umbral** (cobertura 0.60 /
puntaje 0.80) y **no se revisó** ninguna de las 20 `revisar_a_mano`.

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
- **`tests/test_matching.py`** (nuevo): 31 casos — 20 unitarios + 11
  **regresiones con frases literales copiadas de la BD real**
  ("No university degree required.", "Associate's or bachelor's degree…",
  "Bachelor's degree or certification…", "equivalent practical experience may be
  considered", "or an equivalent combination…", "or other technical/scientific
  experience", "Intern - Bachelor's Tech", negación lejana que NO invalida).
- **`tests/test_database.py`**: la versión de esquema se calculaba con `8`
  fijo (fallaba desde la migración 009) → ahora `len(self.database._migrations())`.
- **Herramientas en la raíz** (verificables, no producto):
  `run_paso5.py` (runner con `--dry`), `evidencia_descartadas.py` (evidencia
  literal por `descartada`), `resumen_bloqueo.py` (veredicto del análisis
  educativo), `verificar_corridas.py` (trazabilidad `valida`).
- **`docs/PASO5_EVIDENCIA_2026-10-29.md`** (nuevo): trazabilidad, conteo por
  estado/motivo, las 32 `descartada` con su frase literal y las 20
  `revisar_a_mano / educacion_no_confirmada` con el motivo de la no confirmación.
- **Limpieza**: 75 scripts ad-hoc de la raíz eliminados (`paso5_*.py`,
  `check*.py`, `dump_*.py`, `ctx_*.py`, `dry_paso5.py`, `monitor_ia*.py`,
  `status_ia.py`, `vigilar_enriquecimiento.py`, `normalizar_facts_perfil*.py`,
  `*_licencias.py`, `cerrar_punto4*.py`, …).
- **`DESARROLLO_v15.md`**: fila O6 → O6.3 ✅; bloque nuevo "O6.3 — Matching
  (Paso 5)"; §5 próximos pasos (Paso 6/7); §7 decisiones de diseño (confirmar en
  el texto, corrida nueva por cambio de regla); §8 historial 2026-10-29; tabla
  de objetivos fechada 2026-10-29; conteo de tests actualizado (25 suites / 324).

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
   enrolled…").
6. **Nada del candidato hardcodeado**: los hechos salen de
   `candidate_profile_facts` y los niveles de `concepto`; el mismo código sirve
   para otro perfil.

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
.\.venv\Scripts\python.exe -X utf8 evidencia_descartadas.py 20261029_171039 out_evidencia.txt
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
| `tests/test_matching.py` | 31 tests (11 regresiones con frases de la BD real) |
| `tests/test_database.py` | Versión de esquema dinámica (ya no fija `8`) |
| `run_paso5.py` | Runner del paso 5 (`--dry`) |
| `evidencia_descartadas.py` | Evidencia literal de cada `descartada` |
| `resumen_bloqueo.py` | Veredicto del análisis educativo (estado × detección) |
| `verificar_corridas.py` | Trazabilidad de corridas + delta entre corridas |
| `docs/PASO5_EVIDENCIA_2026-10-29.md` | Evidencia literal completa (32 + 20 vacantes) |
| `DESARROLLO_v15.md` | Objetivos O1–O10 + bloque O6.3/Paso 5 |

## Datos de contexto

- **Corridas de `job_match`** (todas de 447 filas; solo la última es vigente):
  `132455` (50 `descartada`), `133621` (2), `160358` (40), `170343` (34),
  **`171039` (32 ← vigente, `valida=1`)**.
- **Corrida vigente `20261029_171039`**: calificada 102 · revisar_a_mano 141 ·
  sin_requisitos 141 · **descartada 32** · datos_insuficientes 31.
- De las **52** vacantes con requisito universitario **obligatorio**:
  32 confirmadas (`descartada`), 18 con alternativa, 1 con negación
  (`linkedin-4483157697`), 1 sin término en el texto
  (`workday-Associate--Repair-III_R-118081`) → esas 20 van a `revisar_a_mano`.
- Perfil real: 2 hechos de educación (`bachiller-en-educacion-media` =
  `educacion-secundaria` nivel 1; `diplomado-en-electronica` =
  `educacion-tecnica` nivel 2) → **nivel máximo 2**; los requisitos
  `educacion-universitaria` (nivel 3) y `educacion-posgrado` (4) son los
  bloqueantes. `nivel_req < 3` nunca bloquea.
- `job_requirements.requirement_level` real: `required` 60 · `inferred` 75 ·
  `ambiguous` 66 · `preferred` 18 (solo `required` bloquea).
- `jobs.requirements_raw` es `NULL` en casi todos los Workday: el texto real
  está en `description_raw` (~4–5k chars) → se buscan **ambos**.
- Tests con el python del sistema (`python -m pytest`), app con
  `.\.venv\Scripts\python.exe -X utf8`. El venv no tiene pytest.
- v1.x congelado en `D:\Proyectos\jobpulse_cr` — SOLO lectura, nunca modificar.

## Pendiente inmediato

1. **Paso 6 — revisión manual de las 20 `revisar_a_mano / educacion_no_confirmada`**
   (corrida `20261029_171039`): decidir una por una si el título es realmente
   obligatorio (el listado y la frase literal están en
   `docs/PASO5_EVIDENCIA_2026-10-29.md` §4). **No se revisaron todavía.**
2. **Paso 7 — decisiones finales + UI + export** de los resultados de
   `job_match` (hoy la UI no lee `job_match`).
3. **No tocar los umbrales** (cobertura 0.60 / puntaje 0.80) sin acuerdo explícito.
4. Pendientes de siempre: O8 (ciclo de vida, plan de 7 pasos) · O5.3 (re-barrido
   de las ~46 descripciones basura) · O2.1/O2.2 · O6.4 · O9 · O3 (83/122
   tableros con jobs) · O4 (redefinir).
