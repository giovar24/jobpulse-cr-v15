# Handoff — Sesión 2026-10-30: cierre del bloque educativo (mecánicas M1–M4) + FILTRO por ÁREA de empleo de punta a punta (O8.1/O10); las 30 `educacion_no_confirmada` ABIERTAS para firma de segunda persona

## TL;DR

Sesión con **dos bloques**. El primero cerró el bloqueante educativo del
**Paso 5** con cuatro mecánicas **generales** (M1–M4) y tres decisiones de
negocio resueltas **con fuente** (ISCED 2011 / OCDE); quedó la corrida vigente
**`20261030_151648`** (447 filas, `valida=1`; las 7 previas quedan `valida=0`):
calificada 104 · revisar_a_mano 90 · **descartada 82** · datos_insuficientes 30
· sin_requisitos 141 (sumas verificadas por `GROUP BY estado` = 447). La
evidencia literal se regeneró en `docs/PASO5_EVIDENCIA_2026-10-30.md` (1756
líneas) y `verificar_evidencia.py` da **125 verificaciones con frase literal,
0 fallos**. `docs/PASO5_REVISION_PENDIENTES.md` quedó con **30 casos**, texto
completo verbatim y **sin veredictos**: los firma una segunda persona.

El segundo bloque implementó de **punta a punta** el **filtro por ÁREA de
empleo** que pidió el usuario: la **taxonomía la define el sistema** (20 áreas
+ 51 reglas en la BD, migración `016_areas.sql`, esquema v16), la
**clasificación es por TÍTULO y es la MISMA para cualquier fuente** (Workday,
ANE, Indeed, LinkedIn, Elempleo, Harvie, CINDE, Procomer — al guardar una
vacante nueva se clasifica sola), el **perfil marca/desmarca** las áreas en una
pestaña nueva **“Áreas de empleo”**, y el **motor del Paso 5** deja las ofertas
de otras áreas con estado **`fuera_de_area`** (motivo
`fuera_de_area_del_perfil`) sin evaluar sus requisitos, conservando una fila
por vacante para que la exclusión sea auditable. En la UI principal: combo
“Área”, casilla “Solo áreas de mi perfil” y columna “Área”.

**Medición real (447 vacantes):** 447/447 clasificadas → informática 92 ·
producción 43 · ventas 42 · administración 38 · **otros 34** (32 sin encaje + 2
ambiguos) · alimentación 32 · servicio 20 · logística 18 · automotriz 17 ·
ingeniería 16 · marketing 16 · salud 15 · almacén 14 · calidad 12 ·
mantenimiento 12 · RR.HH. 10 · legal 7 · educación 5 · seguridad 4 ·
construcción 0. **Sin áreas marcadas los resultados son IDÉNTICOS a la corrida
vigente** → no hizo falta corrida nueva. Con “todo menos informática” se
excluyen exactamente las 92; con solo “administración” se excluyen 375 (se
evalúan 72).

Suite completa: **393 tests verdes** (+ 65 subtests). Todo **sin commitear al
momento de escribir este handoff** → el commit de la sesión va después (rama
`main`, **sin pushear**: 38 commits adelante de `origin/main`).

## Lo que se hizo

### Parte 1 — Cierre del bloque educativo (mecánicas generales M1–M4)

- **M1 — el nivel lo declara el TEXTO**: el ancla es `job_requirements.evidence`
  y gana la frase más larga (no el `requirement_level` del extractor).
- **M2 — una vía académica está o no DISPONIBLE** según el nivel del perfil;
  las **vías por experiencia NO confirman descarte**.
- **M3 — “X % de un bachelor” = estudios parciales**: cumplen el título
  terminado O estar en curso.
- **M4 — sin lógica por país** en las reglas.
- **3 decisiones de negocio resueltas CON FUENTE** (no por impulso):
  - “advanced university studies” = **posgrado** (nivel 4);
  - “two year college degree” / “associate degree” = **ciclo corto** (nivel 2);
  - “% de completitud” de un bachelor = **parciales** (nivel 3 sin título).
- **Corrida `20261030_151648`**: `descartada` 80 → **82**;
  `educacion_no_confirmada` 19 → **30** (más casos a revisar en la hoja, sin
  cambiar los umbrales: cobertura 0.60 / puntaje 0.80).
- **`docs/PASO5_EVIDENCIA_2026-10-30.md`** (GENERADO, no editado a mano):
  §1.1 mecánicas + §7 delta. `verificar_evidencia.py` → **125 verificaciones,
  0 fallos** (82 `descartada` + 30 `educacion_no_confirmada` + las 13 promovidas
  de la corrida `20261029_183231`).
- **`generar_revision_pendientes.py`** regeneró la hoja de firma: **30 casos**
  con el texto completo verbatim, **sin veredictos**.
- **Mejora de `verificar_evidencia.py`**: ahora usa por defecto el documento de
  evidencia **más reciente** (`docs/PASO5_EVIDENCIA_*.md`); antes seguía
  apuntando al del 29-10 y fallaba en falso (8 casos) al haber una corrida
  nueva.

### Parte 2 — Filtro por ÁREA de empleo (O8.1 + O10)

- **Migración `src/jobpulse_v15/migrations/016_areas.sql`** (esquema v15 → v16):
  tablas `area`, `area_regla`, `job_area`; reconstrucción de
  `candidate_profile_facts` (CHECK `category` + `'area'`) y de `job_match`
  (CHECK `estado` + `'fuera_de_area'`), copiando **48 facts** y **3576 filas** de
  `job_match` y recreando 5 índices. `check_integrity` → **ok**, 0 violaciones
  FK. Ninguna migración aplicada se editó.
- **Semilla versionada `src/jobpulse_v15/seeds/areas.json`**: **20 áreas**
  (19 del sistema + `otros`) y **51 reglas** con prioridad. Se siembra con
  `init-areas [--classify]` (idempotente).
- **Módulo nuevo `src/jobpulse_v15/areas.py`**: `clasificar_texto` (gana la
  regla de **mayor prioridad**; empate en la prioridad máxima → **ambiguo** →
  `otros`), `guardar_clasificacion`, `clasificar_todas`, `areas_del_perfil`
  (hechos `category='area'`), `fact_de_area` y el predicado **conservador**
  `es_fuera_de_area`.
- **Clasificación al INGESTAR** (`Repository.save_job` → `_clasificar_area`):
  cada vacante nueva se clasifica al guardarse → **un puesto nuevo de
  cualquier fuente** (no solo CINDE) queda con área desde el primer momento.
  `areas classify` reclasifica todo en lote cuando cambian las reglas.
- **Motor del Paso 5** (`src/jobpulse_v15/matching.py`): estado
  `ESTADO_FUERA_DE_AREA = "fuera_de_area"`, motivo
  `MOTIVO_FUERA_DE_AREA = "fuera_de_area_del_perfil"`,
  `EvaluadorPaso5(..., aplicar_filtro_areas=True)` y
  `ejecutar_paso5(..., aplicar_filtro_areas=True)`; early-return **antes** de
  evaluar requisitos (la fila queda con `total_req=0`, `puntaje=NULL`).
- **`run_paso5.py`**: flag **`--evaluar-todo`** (desactiva el filtro) + línea de
  estado del filtro en la salida.
- **UI del perfil** (`ui_perfil.py`): pestaña **“Áreas de empleo”**
  (`_SeccionAreas`) con casillas por área (muestra el nº de vacantes), botón
  “Guardar áreas” y **mensaje en línea** (nada de `messagebox` bloqueante);
  `otros` va anotado como “siempre se evalúan”. Las áreas marcadas se guardan
  como hechos `candidate_profile_facts.category='area'`.
- **UI principal** (`ui.py`): combo **“Área”**, casilla **“Solo áreas de mi
  perfil”** y columna **“Área”** en la tabla.
- **CLI** (`cli.py`): `init-areas [--classify]`, `areas list`,
  `areas classify [--dry-run]`.
- **Tests**: `tests/test_areas.py` (nuevo: 20 tests + 21 subtests, con títulos
  **LITERALES** de la BD real), test de UI de marcar/desmarcar en
  `tests/test_ui.py` y ajuste de `tests/test_seed_ats.py` (ignora `areas.json`,
  que no es una lista). Suite completa: **393 passed, 65 subtests**.

## Decisiones de diseño (esta sesión)

1. **La taxonomía de áreas la define el SISTEMA y vive en la BD**
   (`area` + `area_regla`); el perfil solo **marca o desmarca**. Nada del
   perfil actual hardcodeado en el código.
2. **La clasificación es por TÍTULO y es la MISMA para cualquier fuente**: la
   fuente no aparece en ninguna regla (Workday, ANE, Indeed, LinkedIn,
   Elempleo, Harvie, CINDE, Procomer).
3. **Reglas por PRIORIDAD**; si dos áreas empatan en la prioridad máxima el
   aviso es **ambiguo** → `otros` (2 casos reales en 447:
   “Payroll, Time & Benefits Specialist” y “Recepcionista Hospital Curridabat”).
4. **La descripción NO clasifica**: en miles de caracteres cualquier palabra
   aparece por casualidad; su pasada queda como informativa futura
   (confianza `descripcion`, nunca excluye).
5. **El filtro va en el MOTOR del Paso 5** (decisión del usuario), no solo en
   la UI: estado `fuera_de_area`, **sin evaluar requisitos**, pero la corrida
   conserva **una fila por vacante** (la exclusión es auditable).
6. **Filtro conservador por diseño**: sin áreas marcadas **no hay filtro**
   (se evalúa todo); `otros` y las ofertas **sin clasificar** **siempre se
   evalúan** — una clasificación dudosa nunca oculta una oferta.
7. **“Evaluar todo” es explícito**: `run_paso5.py --evaluar-todo`
   (`aplicar_filtro_areas=False`).
8. **Cada cambio de regla = una corrida nueva** (regla del repo, intacta): la
   clasificación se recalcula en `job_area` (tabla derivada) sin tocar los
   avisos; **nada se borra ni se funde**.
9. **Los umbrales siguen congelados** (cobertura 0.60 / puntaje 0.80) y las
   3 decisiones de negocio (“advanced university studies” / “two year college
   degree” / “% de completitud”) se resolvieron **con fuente** (ISCED 2011 /
   OCDE), no por impulso.
10. **La evidencia se verifica POR CONSULTA** (125 verificaciones con frase
    literal), no a ojo.

## Estado de objetivos (tabla O1–O10)

| Objetivo | Estado |
|---|---|
| O1 enriquecimiento IA | ✅ completo (veredicto IA 28-10) |
| O2 búsqueda data-first | 🟡 O2.1 locations Indeed + O2.2 filtro “Req.” |
| O3 fetchers ATS | 🟢 7/7 plataformas validadas (83/122 tableros con jobs CR) |
| O4 calibración gate-vs-IA | ⏳ redefinir (sin gate semántico no hay contra-qué) |
| O5 higiene de datos | 🟢 solo O5.3 (re-barrido ~46 basura) |
| O6 perfil del candidato | 🟡 **O6.3 matching: regla + mecánicas M1–M4 ✅ (30-10); las 30 `educacion_no_confirmada` ABIERTAS (firma de segunda persona) + Paso 7 (decisiones/UI/export)** · O6.4 dedupe semántico pendiente |
| O7 operación UI-first | ✅ completo |
| O8 ciclo de vida | 🟡 **O8.1 ✅ primera versión = taxonomía de áreas (30-10)** · O8.2 recurrentes/aplicadas ocultas + herencia: pendiente |
| O9 optimización UI | ⏳ placeholder |
| O10 mejorar filtros | 🟡 `elegir_filtro_compatibilidad` (28-10) + **filtro por área ✅ (30-10)** |

## Cómo retomar

```powershell
# Áreas de empleo (taxonomía + clasificación + filtro)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 init-areas [--classify]
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 areas list
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 areas classify [--dry-run]

# Paso 5 (corrida NUEVA; las anteriores quedan con valida=0)
.\.venv\Scripts\python.exe -X utf8 run_paso5.py            # con el filtro del perfil
.\.venv\Scripts\python.exe -X utf8 run_paso5.py --evaluar-todo
.\.venv\Scripts\python.exe -X utf8 run_paso5.py --dry

# Evidencia / verificación (exit 0 = TODO CUADRA)
.\.venv\Scripts\python.exe -X utf8 generar_evidencia_paso5.py
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py    # 125 verificaciones
.\.venv\Scripts\python.exe -X utf8 generar_revision_pendientes.py

# Tests (python del SISTEMA; el venv no tiene pytest)
python -m pytest tests/ -q

# UI
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15.ui
```

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/jobpulse_v15/areas.py` | **Módulo real del filtro por área** (clasificación, perfil, predicado, siembra) |
| `src/jobpulse_v15/seeds/areas.json` | Taxonomía (20 áreas) + 51 reglas con prioridad (versionada) |
| `src/jobpulse_v15/migrations/016_areas.sql` | Esquema v16: `area`, `area_regla`, `job_area` + CHECK de `fuera_de_area` |
| `src/jobpulse_v15/matching.py` | Integración del filtro (`fuera_de_area`) + mecánicas M1–M4 |
| `src/jobpulse_v15/repository.py` | `save_job` clasifica al guardar; `PROFILE_FACT_CATEGORIES` con `'area'` |
| `src/jobpulse_v15/ui_perfil.py` | Pestaña **“Áreas de empleo”** (casillas + “Guardar áreas”) |
| `src/jobpulse_v15/ui.py` | Filtro “Área”, casilla “Solo áreas de mi perfil”, columna “Área” |
| `src/jobpulse_v15/cli.py` | `init-areas`, `areas list`, `areas classify` |
| `run_paso5.py` | Runner del Paso 5 (`--dry`, `--evaluar-todo`) |
| `tests/test_areas.py` | **Nuevo**: 20 tests + 21 subtests del filtro por área |
| `docs/PASO5_EVIDENCIA_2026-10-30.md` | Evidencia literal de la corrida vigente (GENERADO) |
| `docs/PASO5_REVISION_PENDIENTES.md` | Hoja de firma (30 casos, sin veredictos) |
| `DESARROLLO_v15.md` | Objetivos O1–O10 + bloque “O8.1/O10 — Filtro por ÁREA” |
| `AGENTS.md` | Reglas/commands del filtro por área (sección “Filtro por ÁREA de empleo”) |

## Datos de contexto

- **Esquema v16** · 447 jobs · 20 áreas sembradas · 51 reglas · `job_area` con
  447 filas clasificadas.
- **Perfil real: 0 áreas marcadas** (el usuario todavía no las ha marcado) →
  el filtro está **inactivo** y el Paso 5 evalúa todo. La próxima corrida tras
  marcarlas producirá las filas `fuera_de_area`.
- **Corridas de `job_match`** (todas de 447 filas; solo la última vigente):
  `20261029_132455`, `_133621`, `_160358`, `_170343`, `_171039`, `_183231`,
  `_205348` (las 7 con `valida=0`) y **`20261030_151648` (vigente, `valida=1`)**.
- **Corrida vigente `20261030_151648`** (`GROUP BY estado` = 447): sin_requisitos
  141 · calificada 104 · revisar_a_mano 90 · descartada 82 · datos_insuficientes
  30. Motivos: 58 `titulo_universitario_requerido` + 24
  `titulo_universitario_en_curso_requerido` (descartada) · 30
  `educacion_no_confirmada` + 42 `educacion_no_cumple` + 11 `skill_faltante` +
  4 `experiencia_no_verificable` + 3 `licencia_no_comparable` (revisar_a_mano).
- **Distribución por área (447)**: informática 92 · producción 43 · ventas 42 ·
  administración 38 · **otros 34** · alimentación 32 · servicio_cliente 20 ·
  logística 18 · automotriz 17 · ingeniería 16 · marketing 16 · salud 15 ·
  almacenamiento 14 · calidad 12 · mantenimiento 12 · recursos_humanos 10 ·
  cumplimiento 7 · educación 5 · seguridad 4 · construcción 0.
- **Perfil real (hechos)**: 5 `contact`, 1 `summary`, 2 `education`,
  9 `experience`, 23 `skill`, 2 `language`, 6 `certification`, **0 `area`**.
- **Tests con el python del SISTEMA** (`python -m pytest tests/ -q`), app con
  `.\.venv\Scripts\python.exe -X utf8`. El venv NO tiene pytest.
- **Gotcha de la sesión**: `messagebox` en un test **cuelga la suite** → en la
  UI de áreas el mensaje va **en línea** (etiqueta), no en un diálogo.
- **Scripts de medición** (fuera del repo, en
  `C:\Users\giova\AppData\Local\Temp\opencode`): `demo_areas.py`,
  `medir_areas.py`, `medir_empates.py`, `demo_perfiles.py`, `medir_cambios.py`.
- v1.x congelado en `D:\Proyectos\jobpulse_cr` — SOLO lectura, nunca modificar.
- `main` va **38 commits adelante de `origin/main`**, **sin push** (no pushear
  sin confirmación del usuario).

## Pendiente inmediato

1. **El usuario marca sus áreas en la UI** (perfil → pestaña **“Áreas de
   empleo”**). Hasta entonces no hay filtro (se evalúa todo). Después, la
   próxima corrida del Paso 5 deja el resto con `fuera_de_area`
   (o `--evaluar-todo`).
2. **Capa B — extractor educativo** (aprobada por el usuario, parqueada):
   - migración **`017`** con filas `concepto` (master / MBA / associate /
     técnico superior);
   - **`Repository.save_analysis` no rellena `codigo_canonico`** → los
     requisitos re-analizados quedarían NULL y el Paso 5 los ignoraría;
   - **`run_full_flow.py::run_analysis()`** llama
     `IngestionService.analyze_job`, que **no existe** en `ingestion.py`;
   - luego: re-analizar las 447 vacantes y su propia corrida (nueva, con
     `valida=1`).
3. **Las 30 `revisar_a_mano / educacion_no_confirmada` siguen ABIERTAS**: las
   firma una **segunda persona** en `docs/PASO5_REVISION_PENDIENTES.md` (el
   autoveredicto del autor de la regla se descarta por sesgo). NO actualizar
   estados hasta esa firma.
4. **Paso 7**: tabla `job_match_decision` (migración numerada) con decisiones
   firmadas (veredicto, criterio, revisor, fecha) que el Paso 7 lee; si el
   registro cambia estados → **corrida nueva**, nunca `UPDATE` in-place.
5. **O8.2 ciclo de vida** (recurrentes/aplicadas ocultas por defecto, herencia
   por compañía + huella de descripción, ventana temporal configurable).
6. **O5.3**: re-barrido de las ~46 descripciones basura (login-wall).
7. **No tocar los umbrales** (cobertura 0.60 / puntaje 0.80) sin acuerdo
   explícito.
8. **No pushear sin confirmación del usuario**: antes, confirmar la suite en la
   rama exacta y verificar que no se sube nada de `fork-v15`.
9. Pendientes de siempre: O2.1/O2.2 · O3 (83/122 tableros con jobs) · O4
   (redefinir) · O6.4 · O9.
