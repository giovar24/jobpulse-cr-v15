# AGENTS.md — JobPulse CR v1.5

Instrucciones para agentes IA que trabajan en este repo
(`giovar24/jobpulse-cr-v15` — hasta 2026-10-26 fue la carpeta `v1_5` dentro
del repo `jobpulse_cr`). Objetivo: orientación instantánea sin re-explorar.

## Al iniciar sesión

1. **Lee el handoff más reciente**: `docs/HANDOFF_SESION_*.md` — estado exacto,
   objetivos (O1–O10), decisiones y pendiente inmediato. Esta hoja solo
   guarda lo DURADERO; lo puntual vive en el handoff.
2. Arquitectura y objetivos O1–O10 (lista canónica en §3): `DESARROLLO_v15.md`.
3. Este es un repo PROPIO e independiente (desde 2026-10-26). El proyecto
   principal v1.x sigue en `D:\Proyectos\jobpulse_cr`, **congelado** (solo
   lectura — no modificarlo). Sus comandos (`main.py`, `unittest`,
   `tools/auditar.py`) NO aplican aquí. **Peligro**: la rama `fork-v15` del
   repo viejo conserva la password de ANE previa a la purga — jamás pushearla
   a GitHub.
4. **No pushear sin confirmación del usuario.**

## Al cerrar sesión (OBLIGATORIO)

Cuando el usuario dice "vamos a otra sesión":
- Escribir `docs/HANDOFF_SESION_YYYY-MM-DD[_turno].md` (varias sesiones el
  mismo día → sufijo `_tarde`/`_noche`) con la estructura estándar: TL;DR,
  lo que se hizo, decisiones de diseño, estado de objetivos (tabla), cómo
  retomar (comandos), archivos clave, datos de contexto, pendiente inmediato.
- Commitear los cambios de la sesión.

## Mapa de documentación

| Documento | Qué es |
|---|---|
| `docs/HANDOFF_SESION_*.md` | Bitácora por sesión (empezar siempre por el más nuevo) |
| `docs/IA_ENRIQUECIMIENTO.md` | Operación del pase IA: modelo local, caché, depuración |
| `docs/SITIOS_PROBLEMATICOS.md` | Guía ANE / Indeed / LinkedIn (login-wall, Cloudflare) |
| `docs/PASO5_EVIDENCIA_*.md` | Evidencia literal del matching (GENERADO — no editar a mano) |
| `docs/PASO5_REVISION_PENDIENTES.md` | Hoja de firma: `educacion_no_confirmada` (sin veredictos, regenerable) |
| `docs/UI_V2_ARQUITECTURA.md` | UI v2 (plana y modular): capas, cómo agregar una pestaña, patrones de Tk |
| `docs/FLUJO_CLI_VS_UI.md` | CLI vs. UI paso a paso: qué comparten y qué hace solo cada uno |
| `DESARROLLO_v15.md` | Arquitectura, objetivos O1–O10 (canónicos en §3), decisiones |
| `README.md` | Setup equipo nuevo: venv, `pip install -e .`, `init-db`, backup |

## Reglas del proyecto (no negociables, acordadas con el usuario)

- **Pensar en general, no "para mí"**: nada del usuario hardcodeado. Perfil =
  facts en BD; filtros de sitios = `site_config` declarativo; credenciales =
  Credential Manager (`credenciales.py`).
- **Límites IA solo opt-in**: `IA_MAX_LLAMADAS`/`IA_RPM` en `.env` o args;
  servidores locales sin tope por defecto.
- **Scrapers browser reciben `port` CDP** del caller; el fetcher nunca crea
  navegador.
- **Config declarativa**: plataformas/sitios en BD (`init-sources`), no en
  código.
- **Dedupe conservador** (O8 de v1.x): duplicado EXACTO (empresa|título|
  ubicación y/o huella de descripción idéntica) se auto-marca `dup_of` /
  hereda estado al ingest; lo DUDOSO lista `quality duplicates` para revisión
  manual. **NUNCA se borra ni se funde datos.**
- **Esquema solo con migraciones**: cambio de BD = archivo nuevo
  `src/jobpulse_v15/migrations/00N_*.sql`; nunca `ALTER` manual ni editar una
  migración ya aplicada.
- **Secretos y datos personales NUNCA al repo**: `.env`, `data/usuario/`,
  `data/empresas/` y CVs (`*.pdf`/`*.docx`/`*.doc`) están gitignoreados a
  propósito — no "arreglar" el `.gitignore` ni commitear rutas con datos.
- **Cada fetcher nuevo** lleva test en `tests/test_<nombre>.py`.

## Comandos esenciales

```powershell
# Regla general: app con el python del VENV; tests con el python del SISTEMA.
# Añadir -X utf8 a cualquier CLI/script que imprima datos de la BD (ver gotcha 7).

# Arranque: venv + Brave CDP 9222 + UI (la IA no se pre-arranca: la UI la
# levanta bajo demanda — botón "Enriquecer")
.\jobpulse-v15.bat   # ruta de Brave hardcodeada al PC del usuario; portátil: .\jobpulse-v15.ps1

# CLI de orquestación: scrape, site, platform, credenciales, login, run, quality…
.\.venv\Scripts\python.exe -m jobpulse_v15 --help

# Servidor IA local (Gemma 3n E2B QAT, puerto 8081) — verificar/arrancar
.\ia-server.bat                # o: .\.venv\Scripts\python.exe start_ia_server.py

# Instalador IA para equipo nuevo (modelo Unsloth + llama.cpp; idempotente)
.\instalar-modelo-ia.bat       # --check = solo verificar

# Flujo end-to-end: scrape → reglas → IA → veredicto (--only-scrape, --no-notify)
.\.venv\Scripts\python.exe -X utf8 run_full_flow.py

# Enriquecimiento (idempotente: solo procesa lo que falta)
.\.venv\Scripts\python.exe run_enriquecimiento.py

# Paso 5 (matching) — corrida NUEVA cada vez que cambia una regla
.\.venv\Scripts\python.exe -X utf8 run_paso5.py [--dry] [--evaluar-todo]

# Areas de empleo (taxonomía del sistema + clasificación de las vacantes)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 init-areas [--classify]
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 areas list
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 areas classify [--dry-run]

# Idioma del aviso (determinista, SIN IA): solo rellena los 'undetermined'.
# Es el dato de la REGLA de requisito de idioma del matching (ver Matching).
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich posting-language
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich posting-language --apply

# Evidencia / verificación del matching (exit 0 = TODO CUADRA)
# El GENERADOR nombra el archivo según la CORRIDA VIGENTE
# (PASO5_EVIDENCIA_<fecha>.md) y el VERIFICADOR elige el doc de esa corrida
# (no el de nombre más alto): si no, una corrida nueva da falsos fallos.
.\.venv\Scripts\python.exe -X utf8 generar_evidencia_paso5.py
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py
.\.venv\Scripts\python.exe -X utf8 generar_revision_pendientes.py

# Diagnóstico BD (SQLite: data/jobpulse_v15.db)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 db check   # integrity + FK (exit≠0 si falla)
.\.venv\Scripts\python.exe tools\estado_bd.py                  # resumen
.\.venv\Scripts\python.exe tools\progreso_enriquecimiento.py   # % por campo
.\.venv\Scripts\python.exe tools\huecos_restantes.py           # basura vs recuperable
# Chequeo puntual enriquecimiento (los monitores ad-hoc son desechables):
.\.venv\Scripts\python.exe -X utf8 -c "from jobpulse_v15.ia_estado import snapshot_enriquecimiento as s; print(s())"

# BD limpia para corrida de prueba (requiere argumento literal SI; conserva
# perfil y config). OJO: reinicia conteos como el de jobs.
.\.venv\Scripts\python.exe -X utf8 clean_run.py SI

# Tests: pytest vive en el python del SISTEMA (el venv NO lo tiene).
python -m pytest tests/ -q   # baseline 2026-11-03: 613 passed + 209 subtests

# UI clásica (completa, intacta)
.\.venv\Scripts\python.exe -m jobpulse_v15.ui

# UI v2 (plana y modular; por ahora: Datos crudos + Perfil + Vacantes +
# Configuración) — ver docs/UI_V2_ARQUITECTURA.md. Agregar una pestaña =
# módulo + 1 línea en PESTANIAS.
.\jobpulse-v15-v2.bat
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15.ui_v2

# UI v2 SIN ventana (humo de verdad: monta el shell, refresca y cuenta filas)
.\.venv\Scripts\python.exe -X utf8 -c "from jobpulse_v15.ui_v2.app import crear_app; r,s=crear_app(); [r.update() for _ in range(20)]; t=s.pestana_activa(); t.refresh(); print(t.key, len(t._widgets['tabla'].get_children())); r.destroy()"
```

## Verificar que el scrape llega bien a la BD (receta)

El scraping NO es una sola llamada: una vacante nueva solo "existe" para el
motor cuando pasa por las 4 etapas. Para comprobarlo con datos frescos:

```powershell
# 1. Scraping explícito (solo con red; los tableros API no necesitan browser)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 scrape workday --site workday-abbott --pages 1
#    Salida: run_id, jobs_found, jobs_new, jobs_duplicate, jobs_skipped.
#    jobs_new = 0 y jobs_duplicate = N → la oferta ya estaba: se ACTUALIZA
#    (last_seen_at) y no se duplica. jobs_new > 0 → se insertó de verdad.

# 2. Análisis (idempotente: solo lo que falta)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 analysis extract-pending --limit 10 [--dry-run]

# 3. Matching: CORRIDA NUEVA (nunca UPDATE de la anterior)
.\.venv\Scripts\python.exe -X utf8 run_paso5.py
.\.venv\Scripts\python.exe -X utf8 generar_evidencia_paso5.py
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py    # exit 0 = TODO CUADRA

# 4. Comprobaciones en SQL (la BD manda)
```

Qué mirar después (es lo que fallaba antes del 2026-10-30):

| Comprobación | Query / dónde | Señal de problema |
|---|---|---|
| La vacante existe | `jobs` + `job_source_records` + `source_job_memory` | `jobs_new` > 0 pero no aparece |
| Tiene área | `job_area` (se clasifica **al guardar**, `Repository.save_job`) | `job_area` sin fila → clasificación rota |
| Tiene análisis | `job_analysis` (`is_current = 1`) + `job_requirements` | `analysis extract-pending` los lista como pendientes |
| El matching la ve | `job_match` de la corrida vigente: `total_req > 0` | `total_req = 0` + `sin_requisitos` → requisitos **sin `codigo_canonico`** (ver Matching) |
| El estado cuadra | `GROUP BY estado` de la corrida vigente = nº de jobs | la suma no cuadra → la corrida quedó a medias |
| La BD está sana | `-m jobpulse_v15 db check` | `integrity_check != ok` o FK violadas |

Ojo: un requisito sin concepto queda con `codigo_canonico = NULL` **a
propósito** (se encola en `concepto_no_normalizado`) → esa vacante puede
evaluarse con menos requisitos de los que tiene. Para saber si es un bug o
una taxonomía incompleta, mira la cola.

## Scrapers de navegador: ANE, Indeed, LinkedIn (y Elempleo vía CDP)

**Guía completa: `docs/SITIOS_PROBLEMATICOS.md`** — leer ANTES de depurar
cualquiera de estos sitios. Reglas de oro:

1. **Brave corre con CDP 9222 y el perfil real**: `--user-data-dir` apunta a
   la raíz `User Data`, **NUNCA** a `User Data\Default` (crea perfil vacío y
   todos los logins "fallan"; fix O7.1 en `browser_manager.py` — combinado con
   `--profile-directory={perfil}`). Verificar: `curl http://127.0.0.1:9222/json/version`.
   Si tu Brave diario corre SIN CDP, la app no puede abrir el puerto
   (Chromium delega en la instancia viva): ciérralo del todo y reintenta.
   El barrido de la UI abre/cierra Brave solo (solo si ella lo abrió).
2. **ANE (ane.cr)**: sesión obligatoria; sin sesión el barrido se omite limpio
   (no es error). Re-login desde la UI (botón "Re-login ANE") o via CLI:
   `.\.venv\Scripts\python.exe login_ane.py` → re-barrido
   `.\.venv\Scripts\python.exe run_scrapes.py ane`. La credencial se resuelve
   en este orden (`credenciales.py::credencial`): **keyring de Windows**
   (Administrador de Credenciales) → `data/empresas/credenciales.json` →
   `.env` (`ANE_USER`/`ANE_PASSWORD`). NUNCA en código ni en el repo.
   ANE **republica vacantes con IDs nuevos** (minoría; desc. idéntica + fecha
   movida): revisar con `quality duplicates`, dedupe manual — nunca automerge.
3. **Indeed (cr.indeed.com)**: SSO Google. El popup de alertas intercepta
   clics — resuelto con `_cerrar_popups`; popup nuevo → agregar su selector
   en `_POPUP_SELECTORES`.
4. **LinkedIn**: sesión PRIMERO, login MANUAL una vez en tu Brave (el
   auto-login dispara CAPTCHA/2FA). Rate-limit 429 en `jobs-guest`: esperar y
   reducir `pages`.

## Matching / Paso 5 — reglas de negocio duras

Módulo real: `src/jobpulse_v15/matching.py` (tests: `tests/test_matching.py`,
87 casos con frases literales de la BD). Cada cambio de regla = **corrida
NUEVA** en `job_match` (`corrida_id` + `valida`); nunca `UPDATE` in-place de
una corrida emitida.

### Regla de IDIOMA del aviso (2026-11-01)

**El requisito de idioma de un aviso es EL IDIOMA EN QUE ESTÁ ESCRITO el
aviso**, salvo que el aviso **pida** uno o varios idiomas como requisito; en
ese caso mandan los que pide. Implementación: `matching.requisitos_efectivos`
(tests `TestReglaIdiomaDelAviso`) + `idiomas.py` (detector).

- El idioma del aviso sale de `jobs.posting_language` (lo declara la fuente, o
  lo detecta **deterministamente** `idiomas.detectar_idioma_del_aviso`: cuenta
  palabras funcionales es/en, sin IA; `mixed`/`undetermined` si no se
  distingue).
- `es` → `espanol`, `en` → `ingles` (`idiomas.CODIGO_IDIOMA`).
- Idioma pedido con `requirement_level='preferred'` **NO es requisito** (misma
  regla dura: "Preferred" no bloquea) → manda el idioma del aviso.
- **`mixed`/`undetermined` NO generan requisito** (no hay un idioma único).
- **El idioma del aviso solo cuenta si el aviso tiene OTROS requisitos**: una
  oferta no se califica solo porque su idioma se cumpla (si no hay más
  requisitos queda `sin_requisitos`).
- Perfil **sin ningún idioma registrado** → `no_verificable` (**nunca**
  faltante). Con otros idiomas pero sin este → `revisar_a_mano` +
  `idioma_no_comparable`.
- **`posting_language` de la fuente no se pisa**: la detección solo rellena
  `undetermined` (origin `detected`), al guardar (`save_job`) y con el backfill
  `enrich posting-language` (idempotente, dry-run por defecto).
- La **comparación de la UI** aplica la MISMA regla
  (`Repository._requisitos_con_regla_de_idioma`): UI y CLI no divergen.

### Regla de EDUCACIÓN del título (2026-10-30)

- `descartada` **solo** si el TEXTO de la oferta confirma título universitario
  obligatorio, sin negación y sin alternativa (en la cláusula/grupo completo);
  ante la duda → `revisar_a_mano`. **Nunca descartar por falta de
  información** (sin hechos educativos → `educacion_no_verificable`).
- "bachiller"/"bachillerato" a secas NO es universitario (en CR es
  secundaria); **"bachillerato universitario" SÍ**; "licenciatura" sí.
- La **obligatoriedad la decide el TEXTO** ("Required/Basic Qualifications",
  "must have", "degree or above"), no el `requirement_level` del extractor;
  "Preferred" no bloquea. `bachelor` sin `degree` cerca es el título del
  puesto, no un requisito.
- "or equivalent field of study" NO es vía alternativa;
  "or advanced coursework/university studies" y "alternatively, N years of
  experience" SÍ. **Alcance por GRUPO de enumeración**: "Bachelor's/University
  degree, Master's degree preferred" EXIGE el bachelor's; "Bachelor's or
  Master's degree preferred" NO exige ninguno.
- **Estudiante activo** ("currently pursuing", "must be enrolled") es criterio
  distinto → `titulo_universitario_en_curso_requerido`.
- **Mecánicas generales (2026-10-30)**: M1 el nivel lo declara el TEXTO
  (ancla: `job_requirements.evidence`; gana la frase más larga) · M2 una vía
  académica está o no DISPONIBLE según el nivel del perfil (vías por
  experiencia NO confirman descarte) · M3 "X % de un bachelor" = estudios
  parciales (cumplen título o estar en curso) · M4 sin lógica por país.
  Decisiones de negocio ya resueltas con fuente (ISCED 2011/OECD): "advanced
  university studies" = posgrado (4) · "two year college degree"/"associate
  degree" = ciclo corto (2) · "% de completitud" = parciales (3 sin título).

### Transversales del Paso 5 (umbrales, código canónico, firma)

- **Umbrales congelados** (cobertura 0.60 / puntaje 0.80): no tocar sin
  acuerdo explícito.
- **Las sumas de estado se confirman por `GROUP BY estado`** — la BD manda sobre
  cualquier resumen transcribido.
- **`codigo_canonico` se resuelve AL GUARDAR** (`src/jobpulse_v15/conceptos.py`,
  tests `tests/test_conceptos.py`): `Repository.save_analysis` mapea
  `value_code` → `concepto.codigo_canonico` (variante = `LOWER(TRIM(value_code))`,
  misma regla que el backfill de la migración 010). El Paso 5 **descarta los
  requisitos sin código** (`AND codigo_canonico IS NOT NULL`): sin código la
  vacante se evalúa con `total_req = 0` y cae en `sin_requisitos` **sin
  avisar**. Antes de 2026-10-30 el código solo lo rellenaba la migración 010
  (backfill one-time) → todo requisito nuevo nacía en NULL. **Nunca insertes
  requisitos por SQL directo**: usa `Repository.save_analysis`.
  - Variante sin concepto → `codigo_canonico = NULL` (correcto) y se encola en
    `concepto_no_normalizado` (`veces` acumula) para crecer la taxonomía.
    Mapean hoy: `six_sigma`, `java`, `tableau`, `autocad`, `c++`, `c#`,
    `typescript`, `solidworks` (skills) y `b3`/`b4`/`d3` (licencias).
  - La migración `017` (filas `concepto` de master/MBA/associate/técnico
    superior) sigue PENDIENTE: sin ella el nivel educativo no es granular.
- **Pendiente ABIERTO**: las `educacion_no_confirmada` solo las firma una
  SEGUNDA persona con `docs/PASO5_REVISION_PENDIENTES.md` (el veredicto del
  autor de la regla se descarta por sesgo). NO actualizar estados hasta esa
  firma.

## Filtro por ÁREA de empleo (nuevo 2026-10-30)

Módulo real: `src/jobpulse_v15/areas.py` (tests: `tests/test_areas.py`).
Taxonomía del SISTEMA en la BD (`area` + `area_regla`, sembrada desde
`src/jobpulse_v15/seeds/areas.json` con `init-areas`); el perfil solo marca o
desmarca (pestaña **“Áreas de empleo”** en `ui_perfil.py` → hechos
`candidate_profile_facts.category='area'`).

- **20 áreas** (lista canónica: `src/jobpulse_v15/seeds/areas.json`; `otros`
  absorbe ambigüedades y ofertas sin clasificar).
- La clasificación es por el **TÍTULO** y es la MISMA para cualquier fuente
  (Workday, ANE, Indeed, LinkedIn, Elempleo, Harvie, CINDE, Procomer): al
  guardar una vacante nueva se clasifica sola (`Repository.save_job`).
  Cambiar las reglas → `areas classify` (o `init-areas --classify`).
- Reglas por **prioridad**; si dos áreas empatan en la prioridad máxima el
  aviso es **ambiguo** → área `otros`.
- **Conservador por diseño**: sin áreas marcadas NO hay filtro (se evalúa
  todo); `otros` y las ofertas sin clasificar **siempre se evalúan** (una
  clasificación dudosa no oculta ofertas).
- En el motor (Paso 5) la oferta de otra área queda con estado
  **`fuera_de_area`** (motivo `fuera_de_area_del_perfil`) y **no se evalúan
  sus requisitos**; la corrida sigue con una fila por vacante (auditable).
  “Evaluar todo” = `run_paso5.py --evaluar-todo`.
- En la UI principal: filtro “Área” + casilla “Solo áreas de mi perfil” y
  columna “Área”.

## Gotchas que cuestan horas

1. **Caché IA en disco** (`data/usuario/ia_cache/`): en pruebas/benchmarks
   responde instantáneo y falsea resultados. Aislar con `JOBPULSE_IA_CACHE`
   (como hace `tools/comparar_ia.py`).
2. **`work_mode='unknown'` es honesto**: no forzarlo; la caché hace la
   re-selección instantánea.
3. **Descripción basura** (login-wall): el enriquecimiento NO la recupera;
   requiere re-barrido del scraper (O5.3). Un desc de `<200` chars no cuenta
   como fallo de la IA al medir.
4. **`/metrics` del llama-server** requiere arrancar con `--metrics` (ya está
   en `start_ia_server.py`); sin él devuelve 501.
5. **`only_critical` solo filtra la SELECCIÓN**: `enrich_job_fields` llena
   TODOS los huecos de los jobs seleccionados. Efecto idempotente; no
   sorprenderse en los logs.
6. **A/B de modelos**: usar `tools/comparar_ia.py` (caché aislada + mismos
   jobs).
7. **`-X utf8` SIEMPRE en CLI/scripts que imprimen datos de la BD**: un
   `\uf0b7` en una descripción revienta la salida (los saves se completan
   igual — idempotente). Para CSV por consola: `[Console]::OutputEncoding =
   UTF8` antes (un NEL `\x85` parte líneas y falsea conteos).
8. **Venv movido con el repo, no recreado**: los `activate` y `pip.exe`
   apuntan a la ruta vieja y fallan. Siempre
   `.\.venv\Scripts\python.exe` / `python.exe -m pip` (nunca `pip.exe`).
9. **`--profile-compatibility` se aplica DESPUÉS de `--limit`**: un límite
   chico puede devolver 0 filas aunque haya coincidencias más atrás.
10. **Los launchers NO reinstalan deps si el venv ya existe**: tras añadir
    deps a `pyproject.toml` → `python.exe -m pip install -e .` a mano.
11. **Tests del cliente IA DEBEN parchear `asegurar_servidor`**:
    `patch("jobpulse_v15.ui_perfil.asegurar_servidor", return_value=None)` —
    sin el patch, el worker arranca el llama-server REAL en plena suite
    (saturación de RAM; ya ocurrió).
12. **Roots Tk de test fallan a veces en Windows** ('Can't find a usable
    tk.tcl' — transitorio): los tests usan `_tkroot_reintentos()`
    (tests/test_ui.py); si falla, reintentar.
13. **Embeddings (`search_engine.py`)**: funcionales (fallback
    `paraphrase-multilingual-mpnet` 768d, ES↔EN OK). **Desde el 2026-11-03
    están cableados** en la pestaña "Vacantes" de la UI v2 (ranking ATS).
    `gate.py`/`ia_calibracion.py` siguen sin callers — no borrar sin redefinir
    O2/O4. OJO: `EmbeddingGemma` está *gated* (401) → el motor cae al
    fallback solo; el texto se codifica **normalizado** (ver gotcha 25).
14. **`failed` en `run_ia_enrichment` NO es error de red**: cuenta jobs cuya
    respuesta fue null/"no mencionado"; la caché de disco los repite
    instantáneo. Errores REALES = WARNING "IA extract {campo} fallo tras 3
    intentos".
15. **`matched` suele ser 0 en BD real**: 372/449 análisis son `partial` y el
    repo exige `complete` → `needs_review`, así que no filtrar por `matched`
    a ciegas (usar `ui.elegir_filtro_compatibilidad`). `solo_vigentes` oculta
    publicaciones con `date_published` fuera de la ventana de 6 meses aunque
    se hayan scrapeado hoy.
16. **`jobs.requirements_raw` es NULL en casi todos los Workday**: el texto
    real está en `description_raw` (~4–5k chars) → buscar en ambos campos.
17. **`jobs.posting_language` es NOT NULL**: en tests hay que darle un valor
    (`undetermined` si no se quiere idioma); un `INSERT` sin él revienta con
    `IntegrityError`. `mixed` es un valor VÁLIDO y **real** (el aviso mezcla
    idiomas): simplemente no genera requisito en el matching. La columna
    `concepto` **no** tiene `nombre`: es `codigo_canonico` + `variante`.
18. **`job_field_status` NO tiene categoría `salary`** (es education/
    experience/language/license/skill): el estado del salary se mira en
    `jobs.salary_min`. La regla "declara salario" vive en
    `src/jobpulse_v15/salario.py` (**marca + CIFRA con moneda en la MISMA
    frase**, ≤80 chars): "Compensation: Paid in USD" y "your hourly rate in
    USD" NO son un dato de salario.
19. **`workable.py` parsea la columna Salary de la tabla markdown** y la
    pasa como `salary_raw` ("—" → `None`). No descartarla (bug corregido el
    01-11): la cifra no llegaba al extractor.
20. **El TÍTULO de un aviso NO es una fuente de ubicación**: el catálogo
    devuelve el título entero como ciudad ("Senior Accountant"). No hacerlo.
21. **Fuentes Tk con espacio van entre LLAVES** (`{Segoe UI} 10`), no en tupla
    ni entre comillas. Tk parte la especificación por espacios: `Segoe UI` se
    lee como familia `Segoe` + tamaño `UI` → `expected integer but got "UI"`.
    Síntoma traicionero: la app **arranca bien** pero los textos de algunos
    widgets (p. ej. las FILAS de un `ttk.Treeview`) **no se pintan**. Aplica
    igual a `option_add("*Font", …)` (lleva llaves y tamaño). Ver
    `ui_v2/theme.py`.
22. **Nunca mezclar `pack` y `grid` en el mismo padre**: es `TclError`. El
    estado vacío de una tabla se posiciona con el MISMO gestor que la tabla
    (`grid()`/`grid_remove()`, no `pack`/`pack_forget`).
23. **El callback de `yscrollcommand` solo actualiza el scrollbar** (`bar.set`).
    Tocar el canvas ahí dentro produce **reentrada infinita** (el
    `scrollregion` se recalcula en `<Configure>`). Patrón en
    `ui_v2/widgets.py::ScrollFrame`.
24. **Crear un widget hijo NO lo coloca**: hay que `pack`/`grid`arlo. Un
    componente sin gestor queda en **1x1 (invisible)** — pasó con `StatTile`
    (la franja de métricas salía vacía). En tests sin ventana visible, verifica
    con `widget.winfo_manager()` (no `winfo_ismapped()`, que da 0 si el root
    está oculto).
25. **La caché de embeddings NO se guardaba** (bug corregido el 2026-11-03):
    `np.save` **agrega `.npy`** al nombre del temporal, así que
    `embeddings_cache.npy.tmp` se escribía como `...tmp.npy` y el `replace()`
    fallaba ("no existe el temporal") → **cada arranque re-vectorizaba los 535
    avisos** (77 s). El temporal debe terminar en `.npy`
    (`embeddings_cache.npy.tmp.npy`). Hay **dos** cachés (documento y título)
    y las dos se versionan (`CACHE_VERSION`): si cambia cómo se codifica el
    texto, la caché vieja se descarta. El texto se codifica **normalizado**
    (minúsculas, sin acentos): medido en el corpus, sin normalizar los avisos
    de soporte TI quedan en la posición 59/535 y normalizados en 37/535.
26. **El ranking ATS es un RANKING, no una calificación**: no toca los
    umbrales congelados del Paso 5 ni sus estados. `"preferred"` **no
    bloquea** (no entra al denominador). Para que los avisos sean
    **comparables entre sí** el score usa **pesos fijos** y **imputa** el
    promedio del corpus a los componentes sin dato (así la falta de
    información ni premia ni castiga; si se redistribuye el peso, un aviso
    con menos datos sube solo). El componente semántico es el **percentil**
    del corpus (los cosenos viven comprimidos en 0.1–0.6 y no distinguen).
    Fórmula semántica calibrada: media de los cosenos entre los **cargos del
    perfil** y el **título** del aviso (65 %) y el **aviso completo** (35 %).
27. **`jobs.skills` mezcla herramientas con frases de tarea** ("elaborar
    cotizaciones", "soporte a equipos Dell"): como denominador bruto
    distortiona el score. El denominador del componente de skills son los
    requisitos **obligatorios** del aviso ∪ las skills **útiles** del aviso
    (las frases de tarea se filtran: `ats.es_frase_de_tarea`). El numerador
    son las que el perfil cubre (cotejo por tokens, con alias de
    fabricante: "Microsoft Excel" ≈ "Excel Avanzado").

## Estado de referencia (verificado 2026-11-03, tras la pestaña de Configuración)

- Suite: **613 tests verdes** + 209 subtests (`python -m pytest tests/ -q`,
  ~2 min); `test_matching.py` 87, `test_areas.py` 20, `test_ubicaciones_cr.py`
  34, `test_idiomas.py` 7, `test_salario.py` 16, `test_ats_ranking.py` 44,
  `test_ui_v2.py` 52.
- **UI v2 (`src/jobpulse_v15/ui_v2/`, 2026-11-02)**: interfaz **plana y
  modular** que convive con la UI clásica (`ui.py`, intacta). Lanzador
  `jobpulse-v15-v2.bat` o `python -m jobpulse_v15.ui_v2`. Capas: `theme.py`
  (única fuente de estilo), `widgets.py`, `dialogs.py`, `configuracion.py`
  (persistencia **sin Tk**), `data/` (stores **sin Tk**), `tabs/base.py`
  (contrato), `tabs/*.py`, `app.py` (shell + `PESTANIAS`).
  Agregar una pestaña = módulo nuevo + 1 línea en `PESTANIAS`. Pestañas:
  **Datos crudos** (avisos con valores originales + panel de texto crudo +
  export CSV), **Perfil** (importar CV con diálogo de revisión revertible +
  alta/edición manual de `candidate_profile_facts`), **Vacantes**
  (**ranking ATS** de los avisos contra el perfil: score 0-100, veredicto,
  desglose y skills que faltan; export CSV) y **Configuración** (IA local
  —arrancar/detener, O7.3—, IA externa → `.env`, sondas de scraping
  on/off, esquema de color, directorio por defecto de CSV). Detalle y
  patrones de Tk: `docs/UI_V2_ARQUITECTURA.md`; gotchas 21–24.
- **BD `data/jobpulse_v15.db` = corpus REAL del usuario** (corrida manual del
  01-11, sin vaciar: es la evidencia en uso). NO "limpiarla" sin confirmación
  explícita — la única vía es `clean_run.py SI`. Esquema versión **16**; la
  migración `017` sigue pendiente. Censos vivos: `tools/estado_bd.py`,
  `tools/progreso_enriquecimiento.py`, `ia_estado.snapshot_enriquecimiento` —
  no confiar en números transcritos de ningún doc.
- **La UI NO persiste el Paso 5**: solo `run_paso5.py` crea corridas en
  `job_match`; desde la UI el matching se calcula sin quedarse guardado.
- **Invariantes de calidad**: todo requisito vigente lleva `evidence` literal
  (trazable al texto del aviso) — uno sin evidence es un bug. El salario casi
  nunca existe como dato (~1–2 % de avisos declara cifra con moneda): la
  ausencia es falta de dato real, NO error del extractor (gotcha 18).
- Corridas exitosas con **0 ofertas** en racha → sitio `needs_review`
  (`consecutive_zero_runs`): nunca se desactiva solo; revisar a mano antes de
  reactivar (`site mark-reviewed`).
- Modelo local canónico: **Gemma 3n E2B QAT** (8k ctx, MTP draft, puerto
  8081); Qwen 3.5 2B descartado (~6.5x más lento). Ver
  `docs/IA_ENRIQUECIMIENTO.md`. La IA no se pre-arranca: la UI la levanta
  bajo demanda (botón "Enriquecer") y la apaga al terminar.
- Fuentes activas: 7/7 plataformas ATS validadas (seeds versionados en
  `src/jobpulse_v15/seeds/*.json`) + ANE/Indeed/LinkedIn/Elempleo (browser) +
  Harvie/CINDE/Procomer. ANE requiere sesión iniciada (si no, se omite
  limpio).
- Pipeline real: scrape (adaptadores **en el paquete raíz**:
  `workday.py`, `greenhouse.py`, `ashby.py`, `lever.py`, `recruitee.py`,
  `workable.py`, `successfactors.py`, `ane.py`, `indeed.py`, `linkedin.py`,
  `elempleo.py`, `harvie.py`, `cinde.py`, `procomer.py`; `providers/` solo
  tiene el login automático) → análisis reglas (`analysis.py`) →
  enriquecimiento IA (`ia_enrichment.py`; veredicto `ia_estado.py`; señal de
  salario `salario.py`) → matching (`matching.py`) → UI de perfil
  (`ui_perfil.py`, sobre `candidate_profile_facts`; la UI v2 tiene su propia
  pestaña de Perfil en `ui_v2/tabs/perfil.py`).
- Ubicación: catálogo único `ubicaciones_cr` (jerarquía país→provincia→cantón→
  distrito + tabla de lugares); backfills deterministas `location normalize`,
  `enrich work-mode` e `enrich posting-language` (idempotentes, dry-run por
  defecto, sin IA). `save_job` valida la ciudad con `ciudad_es_valida`
  (planta/sede/país/empresa no son ciudad).
- **Hueco del PERFIL (visible, capa B pendiente)**: `save_candidate_profile_facts`
  **no** escribe `codigo_canonico` y el Paso 5 exige
  `codigo_canonico IS NOT NULL` para skill/idioma/educación (`matching.py`
  `_cargar_facts`). Por eso los facts del perfil son **invisibles para el
  motor** hasta resolver la capa B (reutilizable: `conceptos.resolver`). La UI
  v2 lo muestra en la columna "Canónico" para no ocultarlo.
- Pendientes: ver "Pendiente inmediato" del handoff más reciente (capa B
  `codigo_canonico` del perfil + migración `017`, las `educacion_no_confirmada`
  sin firma de segunda persona, O5.3 re-barrido de descripciones basura, O6.4
  dedupe de slugs ES/EN al importar CV, sucursal de Harvie en el título,
  Paso 7, O8.2/O8.4, O2/O4/O9, O10 `solo_vigentes`, Paso 5 desde la UI
  (persistir corridas) y pestañas nuevas de la UI v2 — el shell ya está listo).
