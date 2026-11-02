# Handoff — Sesión 2026-11-01 (noche): **corrida manual del usuario (535 avisos) + estimado final de extracción + 3 correcciones**

## TL;DR

El usuario hizo la **corrida manual por la UI** sobre la BD limpia y luego
pidió: *(a)* revisar si el servidor de IA tenía actividad y *(b)* un **estimado
final del % de información extraída con éxito, % no extraíble por falta de
dato y % error de código**.

Hechos de la corrida:

- **535 avisos** (antes 354: ahora entra **Harvie**, que sí se raspó → 181
  avisos de Harvie), 129/129 sitios intentados, **0 errores de scrape** salvo
  1 aviso sin ubicación (`workday-synnex`, marcado `review_required`).
- El **servidor de IA sí trabajó**: `llama-server` (PID 10752) arrancó a las
  18:11:54, procesó el corpus y terminó a las ~18:55; el pase de enriquecimiento
  llenó skills (533/535), languages (511/535), employment_type (493/535),
  work_mode (352/535), city (389/535), region (432/535).
- **El fix del salario de la tarde FUNCIONÓ**: `salary_min` pasó de **0 % a
  9 avisos** (antes 0). Pero al revisar los 19 que la puerta marcaba, se
  descubrió que la puerta era **demasiado laxa** (8 falsos positivos) y que
  el recorte de contexto se centraba en la palabra y no en la cifra.

**Correcciones de esta noche (todas con tests):**

1. **`salario.py`: la puerta ahora exige MARCA + CIFRA con MONEDA en la misma
   frase** (≤80 chars, sin cruzar un punto). Antes (marca + moneda a cualquier
   distancia) disparaba con "Compensation: Paid in USD", con "your hourly rate
   in USD" (le pide la tarifa al candidato) y con el funding de "$26 million"
   de un aviso de Ashby. Los 8 falsos positivos salen; los 11 avisos que sí
   declaran siguen entrando (y los 9 ya extraídos siguen entrando).
2. **`contexto_salario` se centra en la CIFRA**, no en la palabra: el caso
   `ashby-owner` ("The estimated base salary for this role is $19,984,600 CRC
   annually") gastaba los dos fragmentos en un párrafo de relleno y el modelo
   nunca veía la cifra.
3. **`workable.py` ya no descarta la columna Salary** de la tabla de
   Workable ("USD 65,000–100,000"): se pasaba como `salary_raw` (como
   elempleo/indeed/ane/procomer). En este corpus los tableros CR tenían "—",
   pero el campo se perdía en cualquier tablero que sí lo publique.
4. **`SALARY_PROMPT` endurecido** con los dos casos que el modelo falló
   ("Salary: ₡ 625000" → 625000 CRC; "$19,984,600 CRC" → manda el código).

**Estimado final (8 campos × 535 avisos = 4280 celdas):**

| Categoría | Celdas | % |
|---|---|---|
| **Extraído con éxito** | 3254 | **76.0 %** |
| **No extraíble: el aviso no publica el dato** | 1023 | **23.9 %** |
| **Error de código / extracción** | 3 | **0.07 %** |

Los 3 casos de error son **de nivel modelo, no de lógica**: 2 de salario
(`ashby-owner` "$19,984,600 CRC" e `indeed` "₡ 625000" — el modelo devolvió
null; prompt ya endurecido, falta re-verificar con la IA) y 1 de idiomas
(`harvie-6088`, "Inglés Conversacional, (B2)").

Cierre: **517 tests verdes** + 195 subtests, commit en `main` **sin pushear**,
IA local **APAGADA** (puerto 8081 libre), BD con el corpus de 535 avisos
(**no se vació**: es la evidencia de la corrida y el usuario la está usando).

## Lo que se hizo

### 1. Vigilancia del servidor de IA

- 18:11:54 → `llama-server` (PID 10752) escuchando en 8081, `/health` 200.
- Actividad real medida: `prompt_tokens_total` +548 en 8 s, `requests_processing:
  1`, slot 0 `is_processing: true`, `temperature 0.1` (extracción de campos),
  MTP activo (`spec_decode_num_accepted_tokens_total` 12 131).
- El corpus se enriqueció de 18:11 a ~18:55 (`job_field_status.checked_at` en
  UTC 00:11–00:55). El servidor quedó **apagado** al terminar (8081 libre al
  cierre de esta sesión).

### 2. Calidad del scrape (129 sitios)

| Estado | Sitios | Lectura |
|---|---|---|
| `ok` | 67 | 535 avisos (workday 259 · harvie 181 · indeed 15 · cinde 15 · workable 13 · recruitee 13 · greenhouse 12 · ashby 11 · successfactors 7 · linkedin 7 · procomer 1 · elempleo 1) |
| `zero_results` | 61 | **Correcto**: tablero sin vacantes de CR. Verificado a mano en `bask-health-1` (29 vacantes, todas US/UK/España/Egipto) y `cynet-corp` / `utopia-life-worth-living` (las filas CR dicen "—" en Salario). Los 39 de Workable son tableros **reales** con `consecutive_zero_runs = 9` y `health_status = needs_review` → el sistema ya los marca |
| `error` | 1 | `workday-synnex`: "El anuncio '/job/Custumer-Service-Supervisor---Night-shift_R38059' no informa ubicacion" → `review_required = 1` (dato faltante, no fallo del scraper) |

ANE aparece como `zero_results`: **sin sesión iniciada** (se omite limpio).

### 3. Auditoría campo por campo (535 avisos)

| Campo | Extraído | Huecos | Causa de los huecos |
|---|---|---|---|
| `date_published` | 535 (100 %) | 0 | — |
| `city` | 389 (72.7 %) | 146 | 93 solo país/remoto · 49 solo provincia (Heredia/Alajuela/Cartago; por diseño: una provincia no es una ciudad) · 4 sin dato |
| `region` | 432 (80.7 %) | 103 | 103 solo país/remoto |
| `work_mode` | 352 (65.8 %) | 183 | 0 marcas literales de modalidad en el texto (la regla determinista y la IA coinciden: no hay dato) |
| `employment_type` | 493 (92.1 %) | 42 | sin declaración de jornada |
| `salary_min` | 9 (1.7 %) | 526 | **524 no declaran compensación** · 2 declaran cifra y el modelo devolvió null (error de modelo) |
| `skills` | 533 (99.6 %) | 2 | ambos con descripción basura (<200 chars, login-wall) |
| `languages` | 511 (95.5 %) | 24 | 23 sin nivel CEFR declarado · 1 error de modelo |

- **Requisitos (calidad de la extracción rules/IA)**: **1071 vigentes · 0 sin
  `evidence` · 0 con evidencia no literal** → 100 % trazables.
- **Descripciones basura**: 22 (<200 chars) → login-wall (O5.3), no bug.
- **`posting_language`**: 0 `undetermined` (el detector determinista cubre).
- **`job_match` = 0**: la UI **no persiste** el Paso 5 (como estaba
  documentado). Para el corpus nuevo hay que correr `run_paso5.py`.
- **El título NO sirve como fuente de ubicación**: se probó pasarle los
  títulos de los 146 huecos de `city` al catálogo y devuelve basura (la
  ciudad sale igual que el título: "Senior Accountant"). Decisión: no hacerlo.

### 4. Corrección de la puerta del salario (`salario.py`)

Regla nueva (fuente única, Python y SQL con el mismo regex):

> Un aviso declara salario si en la **misma frase** (≤80 chars, sin cruzar un
> punto) hay **marca** ("compensation", "salary", "salario", "hourly rate",
> "pay range", "stipend"...) **y una cifra con moneda** ("$20,000", "₡ 625000",
> "420,000 colones", "USD 1,400").

Efecto medido sobre el corpus: **19 → 11** avisos "declaran salario"; de
esos, 9 ya extraídos, 2 pendientes reales (error de modelo) y **8 falsos
positivos eliminados** (mimica/Series B, 2 de LinkedIn sin cifra, 5 de
TransPerfect que le piden la tarifa al candidato).

`contexto_salario` ahora recorta **alrededor de la cifra** (garantiza que el
modelo ve el número) y `SALARY_PROMPT` tiene ejemplos para "₡ 625000" y para
"$19,984,600 CRC" (manda el código de moneda, no el símbolo).

### 5. `workable.py`: la columna Salary ya no se descarta

El parser de la tabla markdown leía la columna Salary y la tiraba: el aviso
llegaba sin `salary_raw`. Ahora viaja como texto (los "—" se normalizan a
`None`). Test nuevo en `tests/test_workable.py`.

## Decisiones de diseño (esta sesión)

1. **La puerta del salario exige la CIFRA, no solo la moneda**: "Paid in USD"
   o "your hourly rate in USD" no son un dato de salario; contarlos como
   "pendientes" hacía que el panel mintiera (8 avisos) y gastaba llamadas de
   IA. La cifra la juzga el modelo; la puerta solo decide si vale la llamada.
2. **La ventana de 80 chars y el corte por punto**: la marca y la cifra deben
   estar en la misma frase. Sin el corte por punto, "Competitive salary. We
   raised $200 million." volvería a entrar.
3. **El contexto del extractor se centra en la CIFRA**: la palabra sola no es
   dato y consumía los dos fragmentos disponibles.
4. **La puerta del Workable ("country_query") funciona**: 39 tableros con
   `zero_results` se verificaron a mano → ninguno tiene vacantes de CR. No
   es bug del adaptador ni del filtro.
5. **El título de un aviso no es una fuente de ubicación** (produce basura):
   se descarta esa vía.
6. **El "error de código" real que queda es del MODELO, no de la lógica**:
   los 3 casos pendientes son prompting (ya endurecido) y requieren la IA
   encendida para re-verificarse.
7. **Umbrales intactos** (cobertura 0.60 / puntaje 0.80). **No pushear** sin
   confirmación del usuario.

## Estado de objetivos (tabla O1–O10)

| Objetivo | Estado |
|---|---|
| O1 enriquecimiento IA | 🟢 local + veredicto + puerta del salario **verificada en producción** (9 avisos extraídos de 11 declarados) |
| O2 búsqueda data-first | 🟡 O2.1 locations Indeed + O2.2 filtro "Req." |
| O3 fetchers ATS | 🟢 7/7 ATS + browser · Harvie cableado en la UI (entró en la corrida: 181 avisos) |
| O4 calibración gate-vs-IA | ⏳ redefinir |
| O5 higiene de datos | 🟡 22 descripciones basura (login-wall) → O5.3 pendiente · **+ columna Salary de Workable recuperada** |
| O6 perfil del candidato | 🟡 30 `educacion_no_confirmada` ABIERTAS · Paso 7 pendiente |
| O7 operación UI-first | 🟢 completo (corrida manual de 535 avisos) |
| O8 ciclo de vida | 🟡 O8.1 ✅ · O8.2 pendiente |
| O9 optimización UI | ⏳ placeholder |
| O10 mejorar filtros | 🟡 filtro por área ✅ · filtro "Idioma anuncio" ✅ |

## Cómo retomar

```powershell
# Estado de llenado (panel de la UI / snapshot)
.\.venv\Scripts\python.exe -X utf8 -c "from jobpulse_v15.ia_estado import snapshot_enriquecimiento as s; print(s())"
.\.venv\Scripts\python.exe tools\huecos_restantes.py

# Re-verificar los 3 casos de error de modelo (IA encendida: .\ia-server.bat)
#   1) ashby-owner-f1fa9fcd...  ($19,984,600 CRC annually)
#   2) indeed-3a8925374e63beab  (Salary: ₡ 625000)
#   3) harvie-6088              (Inglés Conversacional, (B2))

# Paso 5 con el corpus nuevo (corrida NUEVA; la UI no persiste job_match)
.\.venv\Scripts\python.exe -X utf8 run_paso5.py
.\.venv\Scripts\python.exe -X utf8 generar_evidencia_paso5.py
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py

# Tests (python del SISTEMA; el venv NO tiene pytest)
python -m pytest tests/ -q

# ANE (sigue sin sesión): login + re-barrido
.\.venv\Scripts\python.exe login_ane.py
```

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/jobpulse_v15/salario.py` | La regla «declara salario» = **marca + cifra con moneda en la misma frase**; `contexto_salario` centrado en la **cifra**; `predicado_sql_hueco()`; `registrar_funciones(con)` (SQLite `RE`) |
| `src/jobpulse_v15/ia_enrichment.py` | Puerta del salario + `SALARY_PROMPT` endurecido (₡ y `$`+código) |
| `src/jobpulse_v15/workable.py` | La columna **Salary** de la tabla ya no se descarta (`salary_raw`) |
| `tests/test_salario.py` | 16 tests: cifra obligatoria, funding, "Paid in USD", tarifa al candidato, contexto centrado en la cifra, paridad Python/SQL |
| `tests/test_workable.py` | Test nuevo: la columna Salary viaja (y "—" no) |
| `docs/HANDOFF_SESION_2026-11-01_tarde.md` | Handoff anterior (3 bugs de la tarde) |
| `AGENTS.md` | Estado de referencia (estado de la BD, regla del salario, estimated) |

## Datos de contexto

- **BD al cierre**: corpus de la corrida manual, **535 avisos** (no vaciada a
  propósito: es la evidencia y el usuario la está usando). `jobs` 535 ·
  `job_analysis` vigentes 535 · `job_area` 535 · `job_requirements` 1071 ·
  **`job_match` 0** (falta correr el Paso 5) · `source_runs` 129 ·
  `source_run_sites` 129 (67 ok / 61 zero_results / 1 error). `db check` →
  `integrity ok`.
- **Perfil/config conservados**: 48 facts de perfil · 129 sitios · 14
  plataformas · 20 áreas · 51 reglas de área · 70 conceptos.
- **IA local APAGADA** al cierre (puerto 8081 libre).
- **Scripts de análisis** (fuera del repo,
  `C:\Users\giova\AppData\Local\Temp\opencode`): `estimado_final.py` (clasificación
  extraído/falta/error), `desglose.py` (causa de cada hueco), `que_palabra.py`
  (qué palabra disparaba la puerta), `snippets.py` (texto literal de los
  casos), `salario_origen.py`, `verificar_puerta.py` (regla nueva vs corpus),
  `scrape2.py` (corridas), `titulo_lugar3.py` (el título no sirve), `workable_cfg.py`.
- **Gotchas nuevas**:
  - `sqlite3` crudo sin `salario.registrar_funciones(con)` revienta con
    «no such function: RE» al ejecutar `SECUNDARIOS["salary"]`.
  - La función SQLite `RE()` solo existe en la conexión de `ia_estado`.
  - La fila de Workable con celdas corridas ("Auxiliar de Limpieza" con una
    celda de más) se **descarta** (el filtro de país no la deja pasar): no se
    guarda basura, pero se pierde ese aviso.
  - `job_field_status` NO tiene categoría `salary` (es education/experience/
    language/license/skill): el estado del salary se ve en `jobs.salary_min`.
  - PowerShell `>` escribe UTF-16: usar `Out-File -Encoding utf8`.
- `main` va **sin pushear** (no pushear sin confirmación del usuario).

## Pendiente inmediato

1. **Re-verificar los 3 casos de error de modelo** con la IA encendida
   (`.\ia-server.bat`): los 2 de salario (prompt ya endurecido) y el de
   idiomas (`harvie-6088`, "Inglés Conversacional, (B2)"). Si el modelo
   vuelve a fallar, la salida es un **extractor determinista** de salario
   (cifra + moneda + periodo) y una regla de idioma con nivel.
2. **Correr el Paso 5 sobre el corpus de 535** (`run_paso5.py` + evidencia +
   verificador): la UI no persiste `job_match` y el corpus está sin calificar.
3. **Las 30 `educacion_no_confirmada` siguen ABIERTAS**: las firma una
   **segunda persona** en `docs/PASO5_REVISION_PENDIENTES.md`. NO actualizar
   estados hasta esa firma.
4. **Capa B — taxonomía educativa**: migración **`017`** + crecer `concepto`
   para los requisitos sin `codigo_canonico` (47 en el corpus de 354; medir
   en el nuevo) — el Paso 5 los descarta silenciosamente.
5. **O5.3**: re-barrido de las **22 descripciones basura** (login-wall).
6. **ANE**: sin sesión → el barrido se omite limpio (`login_ane.py`).
7. **Paso 5 desde la UI** sin persistir `job_match` (y O8.2, O2.1/O2.2, O4
   redefinir, O9, sucursal de Harvie en el título).
8. **No tocar los umbrales** (cobertura 0.60 / puntaje 0.80) sin acuerdo
   explícito. **No pushear sin confirmación del usuario.**
