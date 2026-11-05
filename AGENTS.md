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
| `docs/PASO5_EVIDENCIA_*.md` | Evidencia literal del matching (GENERADO — no editar a mano) · la vigente = `PASO5_EVIDENCIA_2026-11-03.md` (corrida `20261103_155215`) |
| `docs/PASO5_REVISION_PENDIENTES.md` | Hoja de firma: `educacion_no_confirmada` (sin veredictos, regenerable) — regenerada el 2026-11-04 contra la corrida vigente (30 casos) |
| `docs/UI_V2_ARQUITECTURA.md` | UI v2 (plana y modular): capas, cómo agregar una pestaña, patrones de Tk |
| `docs/FLUJO_CLI_VS_UI.md` | CLI vs. UI paso a paso: qué comparten y qué hace solo cada uno |
| `docs/MOTOR_VIABILIDAD.md` | Motor de **ajuste técnico** (viabilidad): bandas, pesos, imputación, vetos y por qué NO es probabilidad de contratación |
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
- **Ajuste técnico ≠ resultado del proceso** (acordado 2026-11-04): el
  score de `viabilidad.py` dice si el perfil **cumple lo que pide el aviso**;
  el estado de postulación (`applied`/`interview`/`rejected`…) dice cómo va
  el **proceso de selección**. **Ser rechazado NO significa que el perfil no
  califique**: el reclutador humano decide por presupuesto, timing,
  competencia, sesgos y azar. Por eso los rechazos **NUNCA** se usan como
  etiqueta de aptitud ni para reentrenar pesos: son señal operativa
  (no reprocesar lo postulado, medir el funnel propio, revisar posibles
  falsos positivos del ranking).
- **Privacidad de las señales**: del correo/portal solo se guardan
  derivados mínimos (estado, fecha, remitente, asunto, referencia del
  aviso). **El cuerpo del mensaje nunca se guarda**.

## Comandos esenciales

```powershell
# Regla general: app con el python del VENV; tests con el python del SISTEMA.
# Añadir -X utf8 a cualquier CLI/script que imprima datos de la BD (ver gotcha 7).

# Arranque: venv + Brave CDP 9222 + UI (la IA no se pre-arranca: la UI la
# levanta bajo demanda — botón "Enriquecer")
.\jobpulse-v15.bat   # ruta de Brave hardcodeada al PC del usuario; portátil: .\jobpulse-v15.ps1

# CLI de orquestación: scrape, site, platform, credenciales, login, run, quality…
.\.venv\Scripts\python.exe -m jobpulse_v15 --help

# Salud de los sitios (O3): listar los marcados y resolver la revision manual
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 site list --needs-review
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 site mark-reviewed --id <site_id>
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 site mark-reviewed --all-needs-review

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

# CAPA B: codigo canonico de los hechos del perfil (sin esto el perfil es
# INVISIBLE para el motor: el Paso 5 exige codigo_canonico).
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich profile-canonico
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich profile-canonico --apply

# MOTOR DE VIABILIDAD = AJUSTE TECNICO (0-100) + banda. NO es probabilidad
# de contratacion (ver docs/MOTOR_VIABILIDAD.md).
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list [--banda aplicar]
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad top --limit 20
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list --format csv --output out.csv
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list --semantica  # con embeddings

# POSTULACIONES = estado del PROCESO (no de aptitud). Dry-run por omision.
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones correo --dias 90
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones correo --apply
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones workday --apply
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 postulaciones list --estado interview

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
python -m pytest tests/ -q   # baseline 2026-11-04: 846 passed + 241 subtests

# UI clásica (completa, intacta)
.\.venv\Scripts\python.exe -m jobpulse_v15.ui

# UI v2 (plana y modular; por ahora: Datos crudos + Perfil + Vacantes +
# Scraping + Cuentas + Configuración) — ver docs/UI_V2_ARQUITECTURA.md.
# Agregar una pestaña = módulo + 1 línea en PESTANIAS.
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
   **El puerto CDP ya NO está fijo**: `BRAVE_CDP_PORT` (del `.env`) es la
   única fuente — `browser_manager.puerto_cdp_configurado()`; la UI v2 lo
   edita en la tarjeta "Navegador" (Configuración) y la pestaña "Scraping"
   lo usa por defecto. El perfil se detecta en disco (`User Data/*` con su
   archivo `Preferences`) y se guarda en `BRAVE_PERFIL`.
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
  - **Fallback slug ↔ texto** (`conceptos._variantes_alternas`): el
    importador de CV produce slugs (`active-directory`) y la taxonomía está
    en texto natural (`active directory`) → son la MISMA variante y resuelven
    al mismo código. Aplica también a guiones bajos.
  - La migración `017` (filas `concepto` de master/MBA/associate/técnico
    superior) **ya está escrita** (2026-11-04): `master`/`mba` → posgrado (4),
    `associate degree`/`two year college degree` → ciclo corto (2),
    `bachiller` a secas → **secundaria** (1) en CR.
- **Pendiente ABIERTO**: las `educacion_no_confirmada` solo las firma una
  SEGUNDA persona con `docs/PASO5_REVISION_PENDIENTES.md` (el veredicto del
  autor de la regla se descarta por sesgo). NO actualizar estados hasta esa
  firma.

## CAPA B — el perfil debe llevar `codigo_canonico` (2026-11-04)

El motor (`matching._cargar_facts`) exige `codigo_canonico IS NOT NULL`: sin
él, **el perfil es INVISIBLE** para el Paso 5 y para el motor de viabilidad
(todas las vacantes salen `sin_requisitos`).

- `Repository.save_candidate_profile_fact` / `import_candidate_profile_facts`
  resuelven el código **al guardar** (misma regla que los requisitos:
  `conceptos.resolver`).
- `Repository.backfill_candidate_profile_canonico()` rellena solo los `NULL`
  (idempotente, no destructivo: un código escrito a mano se respeta).
- CLI: `enrich profile-canonico [--apply]` (simulación por omisión).
- **La cola del perfil solo crece con CONCEPTOS**
  (`conceptos.CATEGORIAS_PERFIL_CONCEPTO` = skill/language/license/education):
  los hechos de `experience` del CV son **títulos de puesto**
  ("Soporte Técnico"), no conceptos que falten → se quedan en `NULL` y **no**
  se encolan. Si un hecho de experience **sí** es un concepto
  (`years_experience` → `experiencia-anos`), recibe su código igual.
- La UI v2 muestra la columna "Canónico" para que el hueco sea visible.

## Motor de VIABILIDAD = ajuste técnico (2026-11-04)

`src/jobpulse_v15/viabilidad.py` (tests `tests/test_viabilidad.py`).
Responde: **"¿el perfil cumple lo que pide este aviso?"** — NO es
probabilidad de contratación y **no toca** los umbrales congelados del Paso 5
(0.60/0.80) ni los estados de `job_match`.

- Bandas: `aplicar` (≥85) · `revisar` (80-85) · `no_prioritario` (<80) ·
  `sin_datos` · `veto`.
- **Tope duro**: si falta ≥1 requisito `required` → banda máxima `revisar`
  (nunca `aplicar`). `preferred` no bloquea; `ambiguous`/`inferred` pesan
  como "incierto" (1.0) y no activan el tope.
- Pesos por categoría: skill 0.40 · education 0.25 · experience 0.15 ·
  language 0.10 · license 0.10 · semántica 0.15 (componente ruidoso, solo
  ordena). Peso interno: obligatorio 2.0 · incierto 1.0 · deseable 0.5.
- **DOS PASADAS con imputación del corpus** (igual que el ranking ATS,
  gotcha 26): pesos fijos + promedio del corpus para los componentes sin
  dato. Sin esto el score es degenerado (todo 100) porque casi todos los
  requisitos carecen de `codigo_canonico`.
- Vetos: `fuera_de_area` (reutiliza `areas.es_fuera_de_area`: `otros` nunca
  se veta) y `titulo_universitario_requerido` (texto confirmado).
  Licencia sin comparación → `no_verificable` (no penaliza).
- Reutiliza `matching.EvaluadorPaso5` (no duplica la regla del texto).
- CLI: `viabilidad list|top` (`--banda`, `--limit`, `--evaluar-todo`,
  `--semantica`, `--format csv|json`, `--output`).
- UI v2 (pestaña Vacantes): columnas **"Ajuste"** y **"Banda"**, combo de
  bandas, casilla "Solo aplicar", franja de tiles por banda y detalle con
  "Ajuste técnico" / "Faltantes obligatorios".
- La semántica (percentil del corpus) la calcula **una sola vez**:
  `ats.percentiles_semanticas` (compartida por CLI y UI).

## POSTULACIONES — estado del proceso (2026-11-04)

**Regla dura: ser rechazado NO significa que el perfil no califique.** El
reclutador humano decide por presupuesto, timing, competencia, sesgos y azar.
Estas señales NUNCA se usan como etiqueta de aptitud ni para reentrenar
pesos.

- Núcleo puro `postulaciones.py` (tests `tests/test_postulaciones.py`):
  `Senal`, `clasificar`, `portal_del_remitente`, `referencia_de_url`,
  `estado_mas_avanzado`.
- Estados (alineados con `applications.application_status`): `applied` ·
  `recruiter_contact` · `interview` · `offer` · `rejected` · `withdrawn`.
  **El avance nunca se degrada**: un `interview` posterior no vuelve a
  `rejected`.
- Persistencia (migración `018`): `postulacion_senal` (bitácora) +
  `postulacion` (estado actual por vacante). Se guarda SOLO lo mínimo:
  estado, fecha, remitente, asunto, referencia del aviso. **El cuerpo del
  correo nunca se guarda.**
- `correo_postulaciones.py`: lector IMAP (Gmail) con `X-GM-RAW` y fallback
  `SINCE`; la credencial va al keyring (`credenciales.credencial("gmail")`).
  Los correos **parten las URLs en varias líneas** → se pegan antes de
  buscar el REQID (bug real, ya corregido).
- `workday_postulaciones.py`: parsers puros (JSON + HTML) y fetch por CDP
  de "Mis postulaciones" (reutiliza la sesión del navegador; el fetcher NUNCA
  crea un navegador).
- CLI: `postulaciones correo|workday|list` (dry-run por omisión; `--apply`
  para guardar).

## Conteo de requisitos obligatorios — O2.2 (2026-11-04)

Una sola definición, compartida por CLI, UI clásica y UI v2:
`req_obligatorios` = nº de requisitos con `requirement_level='required'` del
análisis **vigente** (`job_analysis.is_current = 1`). Los `preferred` NO
cuentan ("Preferred" no bloquea, misma regla dura del Paso 5) y los análisis
viejos tampoco.

- Definición + filtro en SQL: `Repository.search_jobs` → parámetro
  `solo_requisitos_obligatorios` y columna `req_obligatorios` en cada fila.
  **La definición vive en el repositorio, no en cada UI** (paridad CLI/UI).
- UI clásica (`ui.py`): columna **"Req."** en la tabla de vacantes + casilla
  "Solo vacantes con requisitos obligatorios" (se resetea con los demás
  filtros).
- UI v2 (`ui_v2/tabs/vacantes.py`): columna **"req"** ("Req.") antes de
  "Paso 5" + casilla "Solo con requisitos obligatorios" (i18n es/en).
- CLI: `search --solo-requisitos-obligatorios`; el CSV de búsqueda añade
  `requisitos_obligatorios` **al final** (no desplaza los índices de las
  columnas ya publicadas).
- El ranking ATS (score 0-100) es otra cosa: un RANKING, no una calificación.
  No toca los umbrales congelados ni los estados del Paso 5.
- **Alcance (importante)**: la columna "Req." cuenta solo lo que el
  EXTRACTOR marcó `required`. El motor del Paso 5 decide la obligatoriedad
  por el **TEXTO** ("Required Qualifications: ..." → obligatorio aunque el
  extractor lo haya marcado `ambiguous`/`inferred`), así que hay avisos
  `calificada` con "Req." = 0 (en la BD real: 122 de 173). "Req." = 0
  significa **"el extractor no confirmó ningún requisito obligatorio"**, NO
  "el aviso no tiene requisitos": el filtro es un triage conservador, no el
  veredicto del motor. La definición vive en SQL (paridad CLI/UI); alinearla
  con el texto del aviso exigiría llamar al motor, no al repositorio.

## Salud de los sitios — O3 (2026-11-04)

`source_sites.review_required = 1` = el sitio pidió revisión manual (3 ceros
seguidos → `needs_review`; un error → `error`). La revisión es el **acuse de
recibo** del sitio:

- `Repository.mark_site_reviewed` **reinicia `consecutive_zero_runs = 0`**
  (sin ese reset, un sitio con 12 ceros volvía a marcarse en la siguiente
  corrida con 0 y la revisión manual no servía de nada). No desactiva el
  sitio ni borra datos: solo baja la bandera y deja el último estado
  observado.
- `clean_run.py` reinicia también la salud de los sitios
  (`health_status='unknown'`, rache=0, `review_required=0`): la salud se
  deriva de las corridas, y si se borran las corridas se borra su veredicto.
- CLI: `site list --needs-review` y `site mark-reviewed --id <site_id>` /
  `--all-needs-review` (mutuamente excluyentes). `list_sites` acepta
  `needs_review_only=True`.

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
28. **Las contraseñas NUNCA se muestran ni se guardan en el JSON**: la clave
    va al **Administrador de Credenciales de Windows** (keyring) y
    `data/empresas/credenciales.json` (gitignored) solo guarda metadatos
    (`password_almacen="keyring"`). Por eso `tiene_credencial` NO puede
    mirar el JSON: tiene que **preguntar al almacén** (si no, toda cuenta
    con clave en el keyring salía "sin credencial" — bug corregido el
    2026-11-03). En la UI (pestaña "Cuentas") el campo de contraseña arranca
    vacío y vacío = "conserva la guardada".
29. **Las cachés se limpian SOLO por patrón** (`src/jobpulse_v15/caches.py`):
    la caché IA borra únicamente archivos `[0-9a-f]{32}.json` (los que
    escribe `ia_api._cache_key`); un archivo ajeno del usuario en esa
    carpeta no se toca. La caché de embeddings son los 4 archivos
    conocidos (`embeddings_cache.npy` + `_meta.json` y los de títulos).
    Borrar la caché IA **cuesta dinero** (se vuelven a pagar las llamadas
    al LLM); la de embeddings solo tiempo (re-vectorizar, ~1-2 min).
30. **`with ... as X` BORRA el nombre al salir del bloque** (comportamiento
    de Python, no de Tk): en los tests, si hay que usar el mock después
    del bloque, guardarlo en otra variable (`parche.start()` →
    `mock = parche.start()`), porque `with patch(...) as m:` deja `m`
    sin definir fuera del `with` (NameError).
31. **La retención OCULTA, nunca borra** (O8/O10): `JobsStore` y `AtsStore`
    (UI v2) pasan `solo_vigentes` + `ventana_retencion_meses` a
    `Repository.search_jobs`; la política vive en `ui_config.json`
    (`retencion_puestos_meses`, `solo_vigentes`) — el MISMO archivo que usa
    la UI clásica, así que todo se escribe con merge
    (`ui_v2/data/retencion.py::RetencionStore`).
32. **El diagnóstico es de SOLO LECTURA**: `jobpulse_v15/diagnostico.py`
    reúne `Database.check_integrity()` + `ia_estado.snapshot_enriquecimiento(bd)`
    + `Repository.get_data_quality_summary()`. `snapshot_enriquecimiento`
    ahora acepta la ruta de la BD (`bd=...`) para medir la base abierta
    por la UI y no la del proyecto.
33. **La salud de los sitios se deriva de las corridas**: `consecutive_zero_runs`
    NO se reinicia solo; hay que hacer el acuse (`site mark-reviewed`) o
    limpiar la BD (`clean_run.py` lo hace por ti). Un rache alto sin
    resolver = sitios marcados en la siguiente corrida con 0.
34. **El score sin imputación es DEGENERADO**: si cada vacante se puntúa con
    los componentes que tiene, una vacante con UN solo requisito cubierto
    saca 100 y sube sola en el ranking (así salía el motor de viabilidad:
    50 de 50 con ajuste 100). La salida: **dos pasadas** — componentes de
    todas las vacantes → promedio del corpus → puntaje con pesos FIJOS
    imputando el promedio a lo que no tiene dato (igual que el ranking ATS).
35. **`Database.connection()` es un context manager**: el evaluador
    (`matching.EvaluadorPaso5`) carga el perfil, los requisitos y los textos
    **al construirse** → la conexión debe VIVIR durante toda la evaluación y
    el evaluador debe ser NUEVO por evaluación (si no, ve datos viejos).
    En Windows, cerrar la conexión ANTES de borrar el temporal
    (`TemporaryDirectory.cleanup()` falla con `PermissionError` si no).
36. **Los correos PARTEN las URLs largas en varias líneas**: el link al aviso
    llega en 2-3 renglones. Hay que pegarlos antes de buscar la URL
    (`postulaciones._RE_URL_PARTIDA`), si no el REQID no se encuentra y la
    señal no se casa con ninguna vacante.
37. **El REQID conserva las MAYÚSCULAS**: `Support-Engineer_R38059` ≠
    `support-engineer_r38059`. La comparación con el corpus es exacta
    (`job_source_records.source_job_id`).
38. **`job_requirements` NO tiene `job_id`**: tiene `analysis_id` (FK a
    `job_analysis`). Para insertar requisitos a mano (tests) hay que crear
    primero el `job_analysis`.
39. **La taxonomía tiene la variante en texto natural**: `active directory`
    (no `active-directory`). El importador de CV produce slugs → el resolver
    prueba las dos formas (`conceptos._variantes_alternas`).
40. **LA CLI MIGRAR LA BASE AL ABRIRLA** (convención del proyecto: CLI, UI
    clásica, UI v2, scrapers y tools llaman `Database.initialize()`): cualquier
    comando aplica las migraciones pendientes. Por eso el CLI **avisa**
    (`[esquema] Se aplicaron las migraciones N-M`) — una migración nunca
    debe aplicarse en silencio sobre la base real. Ojo: `init-db`, `backup` y
    `db check` NO migran (son los comandos explícitos).

## Estado de referencia (verificado 2026-11-04, tras O2.2 + O3 + viabilidad)

- Suite: **846 tests verdes** + 241 subtests (`python -m pytest tests/ -q`,
  ~3:05 min); `test_matching.py` 87, `test_areas.py` 20, `test_ubicaciones_cr.py`
  34, `test_idiomas.py` 7, `test_salario.py` 16, `test_ats_ranking.py` 44,
  `test_scraper.py` 11, `test_browser_manager.py` 21, `test_cuentas.py` 9,
  `test_paso5.py` 6, `test_caches.py` 12, `test_diagnostico.py` 6,
  `test_retencion.py` 13, `test_ui_v2.py` 95 (O2.2), `test_repository.py` 51
  (O2.2 + O3), `test_clean_run.py` 6 (O3), `test_cli_sitios.py` 6 (O2.2 + O3),
  `test_viabilidad.py` 12, `test_postulaciones.py` 21,
  `test_postulaciones_persistencia.py` 8, `test_correo_postulaciones.py` 12,
  `test_workday_postulaciones.py` 13, `test_perfil_canonico.py` 14,
  `test_conceptos.py` 9, `test_migraciones.py` 14, `test_cli_viabilidad.py` 10.
- **Esquema 19** (migraciones aplicadas solo en BDs de prueba: la real sigue
  en 16): `017` educación granular · `018` postulaciones · `019` corrección
  del alias `google-workspace` (NO es `microsoft-365`).
- **Capa B IMPLEMENTADA** (perfil con `codigo_canonico`): resolver al
  guardar + backfill idempotente + `enrich profile-canonico`. La cola del
  perfil solo recibe conceptos (nada de títulos de puesto).
- **Motor de VIABILIDAD implementado** (ajuste técnico, no probabilidad de
  contratación): `viabilidad.py` + CLI `viabilidad list|top` + columnas
  "Ajuste"/"Banda" en la UI v2. Calibración real sobre copia de la BD
  (535 avisos): **aplicar 5 · revisar 17 · no prioritario 284 · sin datos
  142 · veto 87** (sin semántica).
- **Postulaciones implementadas** (estado del proceso, no de aptitud):
  núcleo puro + persistencia (018) + lector IMAP + parser de "Mis
  postulaciones" de Workday + CLI. **Pendiente de validación en vivo**:
  falta CDP (Brave con puerto de depuración) y la app-password de Gmail.
- **O2.2 COMPLETADO**: columna "Req." + filtro "solo con requisitos
  obligatorios" en UI clásica, UI v2 y CLI (ver §"Conteo de requisitos
  obligatorios"). Definición única en `Repository.search_jobs`.
- **O3 COMPLETADO**: los 62 sitios marcados (61 `zero_results` + 1 `error`)
  se resolvieron con `site mark-reviewed --all-needs-review` (la BD real:
  0 pendientes, 0 raches, 535 avisos intactos). Ojo: **el 0 no siempre es
  legítimo** — `workday-intel` devolvía 2 ofertas CR en vivo con 13 ceros
  acumulados; los raches altos venían de corridas borradas por `clean_run`,
  que hasta ahora NO reiniciaba la salud de los sitios (ya corregido).
  `workday-synnex` es el único `error` real (anuncio caído en Workday).
- **UI v2 (`src/jobpulse_v15/ui_v2/`, 2026-11-03)**: interfaz **plana y
  modular** que convive con la UI clásica (`ui.py`, intacta). Lanzador
  `jobpulse-v15-v2.bat` o `python -m jobpulse_v15.ui_v2`. Capas: `theme.py`
  (única fuente de estilo + **densidades**), `widgets.py` (traducción
  automática con `i18n.t()`), `dialogs.py`, `i18n.py` (catálogo es→en),
  `configuracion.py` (persistencia **sin Tk**), `data/` (stores **sin Tk**),
  `tabs/base.py` (contrato + hilos cola+vigilante), `tabs/*.py`,
  `app.py` (shell + `PESTANIAS` + `reconstruir_con_paleta` que aplica
  densidad+idioma+paleta).
  Agregar una pestaña = módulo nuevo + 1 línea en `PESTANIAS`. Pestañas:
  **Datos crudos** (avisos con valores originales + panel de texto crudo +
  export CSV), **Perfil** (importar CV con diálogo de revisión revertible +
  alta/edición manual de `candidate_profile_facts`), **Vacantes**
  (**ranking ATS** de los avisos contra el perfil: score 0-100, veredicto,
  desglose y skills que faltan; columna **"Req."** (requisitos obligatorios
  del aviso) + casilla "Solo con requisitos obligatorios"; **columnas
  "Ajuste"/"Banda"** del motor de viabilidad + combo de bandas + casilla
  "Solo aplicar" + franja de tiles por banda; export CSV;
  botón **Ejecutar Paso 5** que
  deja la corrida PERSISTIDA en `job_match` + casilla "Evaluar todo"),
  **Scraping** (lanzar un
  barrido de las fuentes: grupos `directos`/`cr-gov`/`cr-jobs`, páginas,
  puerto CDP, bitácora en vivo; dominio en `src/jobpulse_v15/scraper.py`),
  **Cuentas** (credenciales de los sitios que piden login: tabla + formulario;
  la contraseña va al keyring y NUNCA se muestra) y
  **Configuración** (IA local —arrancar/detener, O7.3—, IA externa → `.env`,
  **navegador Brave/CDP** —ruta, perfil y puerto; Verificar/Abrir/Detener—,
  sondas de scraping on/off, **apariencia** —esquema de color + **densidad**
  (compacta/normal/amplia) + **idioma** (es/en)—, **cachés** —tamaño y
  limpieza de la caché IA y de embeddings—, **retención** —ventana de
  meses y "solo vigentes"—, **diagnóstico** —integridad, calidad y
  huecos—, directorio por defecto de
  CSV). Detalle y patrones de Tk: `docs/UI_V2_ARQUITECTURA.md`; gotchas
  21–24, 29–32.
- **BD `data/jobpulse_v15.db` = corpus REAL del usuario** (corrida manual del
  01-11, sin vaciar: es la evidencia en uso). NO "limpiarla" sin confirmación
  explícita — la única vía es `clean_run.py SI`. Esquema versión **19**
  (migraciones 017-019 aplicadas el 2026-11-04: solo fueron **aditivas** —
  25 filas de `concepto`, 2 tablas vacías de postulación y 1 corrección del
  alias `google-workspace`; ningún dato borrado, `integrity_check` ok y 0
  violaciones FK). **La capa B ya es EFECTIVA en la BD real** (skill 23/23,
  language 2/2, education 2/2; `experience/total` = 16 años se lee por
  `numeric_value`): el backfill `enrich profile-canonico --apply` sería un
  **NO-OP** (los 9 hechos sin código son títulos de puesto de `experience`,
  que por diseño quedan sin código y **no** se encolan). Decisión del
  usuario (2026-11-04): no hace falta escribir. Censos vivos:
  `tools/estado_bd.py`,
  `tools/progreso_enriquecimiento.py`, `ia_estado.snapshot_enriquecimiento` —
  no confiar en números transcritos de ningún doc.
- **El Paso 5 SÍ se persiste desde la UI v2**: el botón "Ejecutar Paso 5"
  (pestaña Vacantes) llama a `matching.ejecutar_paso5` y deja una corrida
  NUEVA en `job_match` (store `ui_v2/data/paso5.py`; "Evaluar todo" =
  `--evaluar-todo`). Las corridas nunca se actualizan: cada una es nueva y
  las anteriores quedan con `valida = 0`. El **ranking ATS** (score) NO se
  persiste: se regenera al pedirlo.
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
- **Capa B del PERFIL RESUELTA y EFECTIVA (2026-11-04)**:
  `save_candidate_profile_facts` **sí** escribe `codigo_canonico` (reutiliza
  `conceptos.resolver`, con fallback slug↔texto) y el backfill idempotente
  es `enrich profile-canonico --apply`. **La BD real ya la tiene**: las
  migraciones 017-019 están aplicadas (esquema 19) y el perfil real ya es
  visible para el motor (skill 23/23 · language 2/2 · education 2/2 ·
  `experience/total` = 16 años). El backfill es un **no-op** (los 9 hechos
  sin código son títulos de puesto de `experience`, que por diseño quedan
  sin código y no se encolan) → **no hace falta correrlo**. La UI v2 lo
  muestra en la columna "Canónico" para no ocultarlo.
- **Punto 7 completado**: densidad (3 niveles, `font_scale` + métricas) + i18n
  (es/en, ~130 textos, componentes traducen solos, selector en Configuración
  → Apariencia, reconstrucción en caliente).
- Pendientes: ver "Pendiente inmediato" del handoff más reciente (validación
  en vivo de `postulaciones workday` (CDP) y `postulaciones correo`
  (app-password de Gmail), la `educacion_no_confirmada`
  sin firma de segunda persona, O5.3 re-barrido de descripciones basura, O6.4
  dedupe de slugs ES/EN al importar CV, sucursal de Harvie en el título,
  Paso 7, O8.2/O8.4, O4 (sin objeto: el gate ya no existe → proponer cerrarlo
  como *superseded*), O9 y pestañas nuevas de la
  UI v2 — el shell ya está listo). **O2 y O3 ya NO están pendientes**
  (O2.2 y O3 completados el 2026-11-04).
