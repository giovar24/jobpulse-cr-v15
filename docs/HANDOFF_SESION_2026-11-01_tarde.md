# Handoff — Sesión 2026-11-01 (tarde): **auditoría de la corrida por la UI (354 avisos) + 3 bugs de extracción corregidos**

## TL;DR

El usuario terminó la corrida por la UI y pidió: *analizar los registros de la
BD y confirmar que los campos no llenados sean por **falta de dato real** y no
por **errores de extracción***. Resultado del análisis (354 avisos): **3 bugs
reales de extracción**, todos corregidos y con tests:

1. **Harvie nunca se raspó desde la UI** (189 avisos de menos): el
   `fetcher_map` de `ui.py` no tenía `"harvie"` → el barrido se saltaba el
   sitio entero («no hay fetcher implementado»). 354 en vez de ~543.
2. **El extractor de salario nunca disparaba**: la puerta era
   `job["salary_raw"]`, que las APIs de empleo casi nunca traen (**0 de
   354**) → `salary_min` en 0 % aunque **14 avisos declaran su compensación**
   ("Estimated base salary: $19,984,600 CRC annually", "Compensation is of
   420,000 colones per month", "Hourly Rate: $10 to $23 USD"...). Nuevo
   módulo `salario.py`: marca de salario + moneda en el texto, **el mismo
   regex** para el extractor (Python) y para el contador de huecos (SQL, vía
   función SQLite `RE()`).
3. **9 avisos con ciudad basura** (`BSC`×5, `Dry Plant`, `LifeSync
   Amphenol`×2, `Brazil`): `save_job` no validaba la ciudad del adaptador, la
   IA devolvía plantas como ciudad y `resolver_direccion` aceptaba el nombre
   de la empresa como lugar. Puerta nueva `ciudad_es_valida` en las TRES
   entradas (adaptador, IA, catálogo) + backfill aplicado.

**Veredicto sobre el resto de los huecos: falta real de dato, 0 errores** —
895 requisitos con evidencia literal al 100 %, `work_mode`/`employment_type`/
`skills`/`languages` sin señales reales en el texto, `posting_language` con
**0** `undetermined`.

Cierre: **511 tests verdes** + **190 subtests** (antes 486+179), commit en
`main` **sin pushear**, IA local **APAGADA** (el vigilante registró el apagado
a las **12:35:28**), y **BD vaciada** (`clean_run.py SI`) para que el usuario
haga una **corrida manual nueva** y vea los resultados con los bugs corregidos.

## Lo que se hizo

### 1. Vigilante IA (aviso pedido)

`monitorear_ia.py` (temp): INICIO 11:10:25 con health OK → **INCIDENTE
12:35:28: el servidor IA se APAGÓ** (tras 85 min activo; puerto 8081 libre).
Queda en `monitoreo_ia.log` + `estado_ia.json`. Confirmado al cierre: **8081
libre**.

### 2. Auditoría del corpus de la UI (354 avisos)

Integridad del pipeline: 354 jobs = 354 source_records = 354 memory = 354
áreas = 354 análisis vigentes; 895 requisitos; `job_match` **0** (la UI no
persiste el Paso 5, como estaba documentado); **0 errores** en las corridas de
scrape (`source_runs` 128/129 sitios ok; faltó **harvie-cr**).

Causa de cada hueco (el chequeo pedido):

| Campo | Llenado | Huecos | Causa |
|---|---|---|---|
| city | 218/354 | 136 | **78 país/remoto** · **49 por diseño** (solo nombra la provincia) · **9 sin dato** (7 sin lugar + 2 que son el nombre de la empresa) · **0 fallo de lógica** |
| region | 252/354 | 102 | 78 país/remoto · 24 sin dato · 0 fallos |
| work_mode | 172/354 | 182 | la regla determinista reconoce **0** (las 15 "señales" eran falsos positivos: boilerplate "Flex Work", "hybrid retrieval", "Video Remote Interpreter") → falta real |
| employment_type | 345/354 | 9 | 0 señales → falta real |
| date_published | 354/354 | 0 | — |
| salary_min | 0/354 | 354 | **BUG de la puerta** (14 avisos declaran compensación) |
| skills | 352/354 | 2 | 0 señales → falta real |
| languages | 346/354 | 8 | 0 señales → falta real |
| descripción <200 | — | 19 | indeed 15 login-wall, cinde 2, workday 1, recruitee 1 → **O5.3 re-barrido**, no bug |

- **Requisitos (extracción reglas/IA)**: 895 vigentes; **0 sin `evidence`**;
  **0 con evidencia no literal** en el texto del aviso → extracción correcta.
  47 sin `codigo_canonico` (tableau 11, six_sigma 11, java 8, c++ 5,
  typescript 3, c# 3, autocad 3, solidworks 1, NULL 2) → cola de taxonomía
  (migración `017`), no es bug del extractor.
- **`posting_language`**: en/detected 257 · es/detected 42 · es/source 32 ·
  mixed/detected 23 → **0 `undetermined`** ✓.
- **Áreas**: 354/354 clasificadas (Informática 86, Otros 42, Producción 37...).

### 3. Bug 1 — Harvie en la UI

`ui.py::fetcher_map` (dentro del diálogo de barrido) no tenía la entrada
`"harvie"` → `site harvie-cr` caía en «no hay fetcher implementado» y el
barrido de la UI traía 354 avisos en vez de ~543 (189 de Harvie). Añadidos el
`import` y `"harvie": HarvieFetcher()` (la firma la resuelve
`scrape_dispatch.construir_llamada`).

### 4. Bug 2 — la puerta del salario

- **`src/jobpulse_v15/salario.py` (NUEVO, fuente única)**: la regla «este
  aviso declara su compensación» = **marca de salario** (`compensation`,
  `salary`, `salario`, `remuneración`, `hourly rate`, `pay range`, `base pay`,
  `stipend`, `honorarios`, `sueldo`, `compensacion`, `earn`...) **Y** **moneda**
  (`$`, `₡`, `€`, `USD`, `CRC`, `colones`, `dólares`). Tolerante a acentos.
  - `declara_salario(*textos)` → puerta del extractor.
  - `contexto_salario(*textos)` → recorta el texto **alrededor de la marca**
    (la sección de compensación suele ir al final del aviso, fuera de los
    2000 chars que ve el modelo).
  - `predicado_sql_hueco()` → el hueco "salary" del panel, con **el MISMO
    regex**: `ia_estado._connect()` registra la función SQLite
    `RE(patron, texto)` (`registrar_funciones`).
- **`ia_enrichment.enrich_job_fields`**: la puerta ahora es `salary_raw` **o**
  `declara_salario(descripcion, requisitos)`; al modelo se le manda el
  `contexto_salario`. `SALARY_PROMPT` endurecido (ignora funding/revenue/PTO).
  `needs_secondary_enrichment` usa la misma regla.
- **`ia_estado.SECUNDARIOS["salary"]`** usa `predicado_sql_hueco()` → el panel
  ahora ve los **18** avisos pendientes (antes 0).
- Verificado en la BD: Python y SQL concuerdan **exactamente** (18 avisos);
  los falsos positivos conocidos (revenue `$200 million`, `Series D`,
  `$500 million`, `$42 billion`, `masteries`) quedan **fuera**.

### 5. Bug 3 — ciudades basura

- **`ubicaciones_cr.py`**:
  - `es_ciudad_plausible` rechaza **países** (`_PAISES_NO_CIUDAD`).
  - `coincide_con_empresa(ciudad, empresa)`: las PALABRAS de la ciudad no
    pueden ser las de la empresa ("LifeSync Amphenol" ≡ "LifeSync -
    Amphenol").
  - **`ciudad_es_valida(ciudad, region, empresa)` (NUEVA, puerta de
    guardado)**: solo rechaza lo que NO PUEDE ser un lugar — planta/sede
    (`_PALABRAS_NO_CIUDAD`), país, dígitos, "costa rica", guion bajo,
    abreviatura en mayúsculas ≤5, "provincia+zona" ("Alajuela Coyol") y el
    nombre de la empresa. **No** aplica el filtro de descriptores ni la regla
    de nombres ambiguos: "San Antonio de Belén" → ciudad válida con región
    Heredia (decisión del 31-10) y el centinela "Verified City" del backfill
    de Workday se conserva.
  - `resolver_direccion(..., empresa=...)`: la parte desconocida ya no se
    guarda si es la empresa.
  - `es_provincia_valida(region)`: la región debe ser provincia del catálogo.
- **`repository.save_job`**: valida la ciudad del ADAPTADOR (si es basura la
  descarta y re-resuelve desde `location_raw`), resuelve con el catálogo como
  antes y **re-valida** lo que devuelve el catálogo.
- **`ia_enrichment.enrich_job_fields`**: el `city`/`region` que devuelve la IA
  pasan por la misma puerta (5 `BSC` + 1 `Dry Plant` venían de aquí).
- **Backfill**: `list_location_records` trae `company` y
  `location normalize` pasa `empresa` a `resolver_direccion` /
  `ciudad_es_basura`. **Aplicado**: 9 correcciones, 345 sin cambios, 0
  regiones tocadas; `db check` → `integrity ok`, 0 FK.

### 6. Tests y verificación

- **`tests/test_salario.py` (NUEVO, 11 + 7 subtests)**: declaraciones reales,
  marca sin monto, cifra que no es salario (funding), acentos, contexto,
  predicado SQL con memoria SQLite y **mismo regex que Python**.
- **`tests/test_ia_enrichment.py` (+3 clases)**: salario por texto sin
  `salary_raw` (el prompt se dispara y persiste), sin declaración no se pide,
  `needs_secondary_enrichment` por texto, y la ciudad basura de la IA no se
  guarda (la válida sí).
- **`tests/test_ubicaciones_cr.py` (+1 clase, 7 casos)**: planta/sede/país/
  empresa no son ciudad; `ciudad_es_valida`; `es_provincia_valida`.
- **`tests/test_repository.py` (+2)**: `save_job` descarta las 4 basuras
  (region correcta: Cartago) y conserva "San Antonio"/Heredia.
- **`tests/test_workday.py`** (ajuste): la ciudad basura del parser viejo ya
  no se guarda → se simula el dato heredado con `UPDATE` directo para seguir
  probando la corrección del backfill.
- **Suite completa**: `python -m pytest tests/ -q` → **511 passed, 190
  subtests passed** (~1 min 25 s).
- **Snapshot de enriquecimiento** (panel de la UI): `salary` pasa de 0 a **18**
  huecos pendientes (17 recuperables) — ahora el extractor los va a intentar.

## Decisiones de diseño (esta sesión)

1. **Una sola verdad para la señal de salario**: el extractor (Python) y el
   contador de huecos (SQL) usan **el mismo regex** (función SQLite `RE`
   registrada en la conexión de `ia_estado`). Con `LIKE` había divergencias
   (`%earn%` encontraba "learning", `%pay%` encontraba "payroll"): la lección
   de "lógica duplicada = divergencia" aplicada antes de que ocurra.
2. **La puerta del salario exige marca Y moneda**: "compensation" genérico o
   una cifra de funding no disparan el prompt; el modelo juzga la cifra,
   la puerta decide si el aviso merece la llamada.
3. **El contexto del salario se recorta alrededor de la marca**: mandar los
   primeros 2000 chars perdía las secciones de compensación que van al final
   del aviso (caso Workday/LinkedIn).
4. **Puerta de ciudad conservadora y en 3 entradas**: adaptador (save_job),
   IA (enrich_job_fields) y catálogo (tras resolver). Solo se rechaza lo
   que no puede ser un lugar; los nombres ambiguos y los descriptores siguen
   decidiéndose en `es_ciudad_plausible` (que es para TROZOS DE TEXTO).
5. **`ciudad_es_basura` ≠ `ciudad_es_valida`**: la primera es para CORREGIR
   datos heredados (agresiva, marca ambiguos de varias provincias); la
   segunda, para GUARDAR (conservadora, solo lo inequívoco).
6. **La ciudad de la IA nunca entra sin validar** (era el origen real de los
   5 `BSC` y el `Dry Plant`: el catálogo los rechazó bien, la IA los metió).
7. **Los 9 avisos corregidos quedan honestos**: ciudad `NULL` (no hay dato),
   región la que da el catálogo ("Costa Rica-Cartago-BSC" → Cartago).
8. **Umbrales intactos** (cobertura 0.60 / puntaje 0.80). **No pushear** sin
   confirmación.

## Estado de objetivos (tabla O1–O10)

| Objetivo | Estado |
|---|---|
| O1 enriquecimiento IA | 🟢 servidor local + veredicto + work_mode e idioma deterministas · **+ puerta del salario arreglada (18 avisos por extraer)** |
| O2 búsqueda data-first | 🟡 O2.1 locations Indeed + O2.2 filtro "Req." |
| O3 fetchers ATS | 🟢 7/7 ATS + browser · **+ harvie cableado en la UI (189 avisos que faltaban)** |
| O4 calibración gate-vs-IA | ⏳ redefinir |
| O5 higiene de datos | 🟡 **9 ciudades basura corregidas (01-11)** · O5.3 pendiente con 19 descripciones basura (15 Indeed login-wall) |
| O6 perfil del candidato | 🟡 30 `educacion_no_confirmada` ABIERTAS · Paso 7 pendiente |
| O7 operación UI-first | 🟢 completo |
| O8 ciclo de vida | 🟡 O8.1 ✅ · O8.2 pendiente |
| O9 optimización UI | ⏳ placeholder |
| O10 mejorar filtros | 🟡 filtro por área ✅ · filtro "Idioma anuncio" ✅ |

## Cómo retomar

```powershell
# Corrida manual nueva (la BD ya está limpia): UI con Brave CDP 9222
.\jobpulse-v15.bat          # o: .\jobpulse-v15.ps1 (portátil)

# Ver el estado de llenado en cualquier momento
.\.venv\Scripts\python.exe -X utf8 -c "from jobpulse_v15.ia_estado import snapshot_enriquecimiento as s; print(s())"
.\.venv\Scripts\python.exe tools\huecos_restantes.py

# Backfill de ubicacion (idempotente, dry-run por defecto)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 location normalize [--apply]

# Tests (python del SISTEMA; el venv NO tiene pytest)
python -m pytest tests/ -q

# Paso 5 con el corpus nuevo: corrida NUEVA (nunca UPDATE de una corrida emitida)
.\.venv\Scripts\python.exe -X utf8 run_paso5.py
.\.venv\Scripts\python.exe -X utf8 generar_evidencia_paso5.py
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py
```

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/jobpulse_v15/salario.py` | **NUEVO**: la regla «declara salario» (marca + moneda), `contexto_salario`, `predicado_sql_hueco()` y `registrar_funciones(con)` (función SQLite `RE`) |
| `src/jobpulse_v15/ia_enrichment.py` | Puerta del salario por texto + contexto recortado · validación de la ciudad/región que devuelve la IA · `SALARY_PROMPT` endurecido |
| `src/jobpulse_v15/ia_estado.py` | `SECUNDARIOS["salary"]` con el predicado nuevo · `RE()` registrada en su conexión |
| `src/jobpulse_v15/ubicaciones_cr.py` | `_PAISES_NO_CIUDAD` · `coincide_con_empresa` · **`ciudad_es_valida`** · `es_provincia_valida` · `resolver_direccion(empresa=)` |
| `src/jobpulse_v15/repository.py` | `save_job` valida la ciudad (adaptador + catálogo) · `list_location_records` trae `company` |
| `src/jobpulse_v15/ui.py` | `fetcher_map` con `"harvie"` (import + entrada) |
| `src/jobpulse_v15/cli.py` | `location normalize` pasa `empresa` (corrector de basura heredada) |
| `tests/test_salario.py` | **NUEVO**: la regla y su paridad Python/SQL |
| `tests/test_ia_enrichment.py` | Puerta de salario por texto · ciudad de la IA validada |
| `tests/test_ubicaciones_cr.py` | 7 casos de ciudad no válida / válida |
| `tests/test_repository.py` | `save_job` descarta basura y conserva "San Antonio" |
| `AGENTS.md` | Estado de referencia actualizado (511 tests, 3 bugs, BD vaciada) |

## Datos de contexto

- **BD al cierre**: **VACIADA** con `clean_run.py SI` (conserva perfil,
  fuentes/128+1 sitios, áreas, taxonomía y `concepto`): jobs 0 ·
  job_source_records 0 · source_job_memory 0 · job_area 0 · job_analysis 0 ·
  job_match 0. `db check` → `integrity ok`. Es la base para la **corrida
  manual nueva** del usuario.
- **Estado de la auditoría** (354 avisos de la corrida de hoy, ANTES de
  vaciar): llenado city 61.6 % · region 71.2 % · work_mode 48.6 % ·
  employment_type 97.5 % · date_published 100 % · skills 99.4 % ·
  languages 97.7 % · **salary_min 0 % (bug corregido; 18 avisos lo declaran)**.
- **El vigilante IA** (temp): `monitoreo_ia.log` / `estado_ia.json` — apagado
  a las 12:35:28. **IA local APAGADA al cierre** (puerto 8081 libre).
- **Scripts de análisis** (fuera del repo,
  `C:\Users\giova\AppData\Local\Temp\opencode`): `analisis_ui_354.py`,
  `verificar_extraccion.py` (señales por campo),
  `verificacion_final.py` (regla determinista de work_mode, puerta del
  salario, sitios), `clasificar_huecos.py` (causa city/region),
  `auditar_ciudades.py`, `casos_bugs.py`, `rastro_ciudad.py`,
  `impacto_ciudad.py`, `impacto_final_ciudad.py` (impacto de la puerta: solo
  los 9 basura), `verificar_regla_salario.py` (paridad Python/SQL),
  `discordantes_salario.py`, `impacto_salario.py`, `casos_salario.py`,
  `origen_ciudad.py`, `verificar_final.py`, `monitorear_ia.py`.
- **Gotchas nuevas**:
  - **`city` del adaptador se valida en `save_job`**: una sede/planta/país/
    empresa ya no entra. Si un test siembra basura heredada, hay que hacerlo
    con `UPDATE` directo (como `test_workday.py`).
  - **La función SQLite `RE()`** solo existe en la conexión de `ia_estado`
    (y donde se llame `salario.registrar_funciones(con)`): un `sqlite3`
    crudo que ejecute `SECUNDARIOS["salary"]` sin registrarla revienta con
    «no such function: RE».
  - **La IU no persiste `job_match`** (sigue siendo así): el Paso 5 por la UI
    no deja corrida; para evidencia, `run_paso5.py`.
  - PowerShell `>` escribe UTF-16: usar `Out-File -Encoding utf8` y abrir con
    `encoding='utf-8-sig'` en Python.
- `main` va **sin pushear** (no pushear sin confirmación del usuario).

## Pendiente inmediato

1. **Corrida manual nueva por la UI** (lo pidió el usuario, BD ya limpia):
   comprobar que ahora entren los **189 de Harvie**, que `source_runs` quede
   con **0 errores** en 129/129 sitios, que **no haya ciudades basura** y que
   el pase de enriquecimiento llene `salary_min` en los **~18** avisos que
   declaran compensación (con la IA local encendida: `.\ia-server.bat`).
2. **Las 30 `educacion_no_confirmada` siguen ABIERTAS**: las firma una
   **segunda persona** en `docs/PASO5_REVISION_PENDIENTES.md` (hoja
   regenerable). NO actualizar estados hasta esa firma.
3. **Capa B — taxonomía educativa**: migración **`017`** + crecer `concepto`
   para los **47 requisitos sin `codigo_canonico`** del corpus nuevo (el
   Paso 5 los descarta silenciosamente).
4. **O5.3**: re-barrido de las **19 descripciones basura** (15 Indeed por
   login-wall → sesión).
5. **Paso 5 desde la UI** sin persistir `job_match` (y O8.2, O2.1/O2.2, O4
   redefinir, O9, sucursal de Harvie en el título, extractor de rango de
   salario real — la IA ya extrae el salario puntual).
6. **No tocar los umbrales** (cobertura 0.60 / puntaje 0.80) sin acuerdo
   explícito. **No pushear sin confirmación del usuario.**
7. **ANE**: sigue sin sesión → el barrido de ANE se omite limpio. Para
   cubrirlo: `login_ane.py` (o botón "Re-login ANE") y re-barrido.
