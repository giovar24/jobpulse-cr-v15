# JobPulse CR 1.5 — Blueprint

> Contrato raíz (EGM "Hay"). Las instrucciones operativas para agentes están en
> [`AGENTS.md`](AGENTS.md); el contrato de cada directorio vive en su `README.md`.

## System Overview

JobPulse CR v1.5 es un pipeline de búsqueda de empleo sobre **SQLite** con dos
fachadas que comparten una única implementación: el **CLI** (`jobpulse-v15`) y la
**UI v2** de escritorio (`python -m jobpulse_v15.ui_v2`). El orquestador
(`pipeline.py`) encadena el flujo `scrape → análisis por reglas → IA →
re-análisis → backfill → Paso 5 → evidencia` y el veredicto auditable es el
**Paso 5** (`matching.py`), que deja su resultado en `job_match` y su
justificación por vacante en `docs/PASO5_EVIDENCIA_*.md`. La base del corpus es
`data/jobpulse_v15.db` (no versionada); el esquema se versiona solo con
migraciones y el esquema actual es la versión **28**.

**Por qué el orden no se puede alterar**

El orquestador (`pipeline.py`) ejecuta siete etapas. Cuando lo invoca
`run_full_flow.py`, las corre en este orden:

`1 scrape → 2 análisis → 3 IA → 4 re-análisis → 5 backfill → 6 Paso 5 → 7 evidencia`

(La lista canónica es `pipeline_metricas.ETAPAS`; el **Paso 5 es la etapa 6**,
porque la numeración del «Paso 5» es histórica y no coincide con la posición
dentro del flujo.)

- **Etapas 2 y 3 antes que la 4**: la etapa 2 deja el análisis por reglas sobre
  el que trabaja la etapa 4, y la etapa 3 añade `jobs.skills` y `jobs.languages`,
  que los scrapers no rellenan. Sin la etapa 3, la etapa 4 no tiene nada que
  integrar y la taxonomía queda sin cubrir.
- **Etapa 4 antes que la 5**: la etapa 4 **añade** requisitos nuevos; la 5 es la
  que les rellena `codigo_canonico`. Si se invierte, el Paso 5 evalúa esos
  requisitos sin código y **los ignora en silencio**. La etapa 4 la implementa
  `enrich requirements-source --apply`.
- **Etapa 5 antes que la 6**: `enrich requirements-canonico --apply` rellena
  `job_requirements.codigo_canonico` solo donde falta; **un requisito sin
  `codigo_canonico` se ignora en silencio**, así que la vacante se evalúa con
  menos requisitos de los que realmente pide.
- **Etapa 6 = corrida nueva**: cada ejecución escribe filas nuevas en
  `job_match` con su `corrida_id` y marca `valida=0` en las anteriores; nunca se
  actualiza en sitio. Estados posibles: `calificada`, `revisar_a_mano`,
  `descartada`, `datos_insuficientes`, `sin_requisitos`,
  `baja_compatibilidad`, `fuera_de_area`.

**Regla mínima del veredicto** (precedencia completa en `matching.py`):
`descartada` = bloqueante universitario **confirmado** en el texto;
`revisar_a_mano` = requisito universitario obligatorio **no confirmado**, o hay
otros requisitos no cumplidos; `datos_insuficientes` = cobertura < **0.60**;
`calificada` = puntaje ≥ **0.80**; `baja_compatibilidad` = resto;
`fuera_de_area` = la oferta no pertenece a las áreas marcadas en el perfil.

El comando que encadena las siete etapas es `run_full_flow.py`. El botón
«Procesar» de la UI v2 ejecuta **seis** (`analisis → ia → reanalisis →
backfill → paso5 → evidencia`), **sin `scrape`**: el scraping se lanza aparte
con «Ejecutar grupo»/«Ejecutar seleccionados» (o por CLI). El comando de cada
etapa suelta:

| # | Etapa | Comando |
|---|---|---|
| 1 | Scrape | `run_full_flow.py --only-scrape` |
| 2 | Análisis por reglas | `analysis extract-pending` |
| 3 | Pase IA | `run_enriquecimiento.py` |
| 4 | Re-análisis con campos de la fuente | `enrich requirements-source --apply` |
| 5 | Backfill canónico | `enrich requirements-canonico --apply` |
| 6 | Matching (Paso 5) | `run_paso5.py` |
| 7 | Evidencia | `generar_evidencia_paso5.py` + `verificar_evidencia.py` |

Los scripts de raíz (1, 3, 6, 7) están en la tabla «Local Interface &
Invariants», los comandos `enrich` (4, 5) en «Subsistemas y comandos no
detallados aquí» y la extracción por reglas (2) en el manual (ver
`analysis extract-pending`, «Extractor de requisitos»).

> `run_enriquecimiento.py` es un **atajo**: hace la etapa 3 (IA) y al terminar
> re-analiza los avisos que aún no integraban `jobs.skills`/`jobs.languages` (el
> grupo «campos sin integrar» de la etapa 4). **No** hace el otro grupo de la
> etapa 4 —los avisos con texto cambiado—, que corre solo el orquestador.

## Terminología

Vocabulario canónico del proyecto. El manual funcional heredado (más abajo) usa
a veces otra palabra para el mismo concepto; manda esta tabla.

| Término canónico | Significado | Cómo lo llama el manual heredado |
|---|---|---|
| **Paso 5** | El motor de matching (`matching.py`). Escribe `job_match`. | «comparación con el perfil» (la «compatibilidad» informativa de `search` es otro cálculo) |
| **aviso** | Una vacante guardada en la BD: fila de `jobs` (con su origen en `job_source_records`). Es el término canónico; «oferta» y «vacante» son sinónimos del manual heredado. | «oferta», «vacante», «anuncio» |
| **corrida** | Una ejecución registrada: fila de `source_runs` o de `job_match` con su `corrida_id`. | «corrida», «historial» |
| **análisis** | Fila de `job_analysis` con sus `job_requirements` (versión `rules-2+fuente`; `analysis_flow.VERSION_ANALISIS`). | «análisis», «búsqueda/extracción» |
| **re-análisis** | Reejecutar el análisis porque cambió el texto del aviso o porque se integraron campos nuevos. | «reanalizar» |
| **backfill** | Rellenar `codigo_canonico` en requisitos ya guardados. | (no aparece) |
| **UI v2** | La única interfaz gráfica (`ui_v2/`). | «interfaz Tkinter», «aplicación», «ventana» |
| **áreas** | Clasificación de la vacante en `job_area` desde `seeds/areas.json`. «Las áreas marcadas en el perfil» = las que el perfil declara como objetivo. | «áreas» |
| **perfil** | Hechos del candidato en `candidate_profile_facts` (áreas, educación, idiomas, experiencia): es lo que el Paso 5 y la viabilidad comparan contra cada aviso. Se carga desde la pestaña «Perfil» de la UI v2 (edición manual o importación de CV) y se normaliza con `enrich profile-canonico`. | «perfil», «datos del candidato» |
| **viabilidad** | Banda de **ajuste técnico** perfil↔aviso (0-100). No es probabilidad de contratación. | (no aparece) |
| **Paso 7** | Numeración **histórica de los hitos del proyecto**, no de las etapas del pipeline: es la fase en que se firman las decisiones de segunda persona sobre la educación no confirmada (`job_match_decision`). | «firma de decisiones» |
| **educacion_no_confirmada** | Caso de revisión manual: el motor no pudo decidir si el aviso exige un título universitario (no lo descarta nunca por falta de información). Lo resuelve una **firma de segunda persona** (persona distinta del autor de la regla/motor, para no autoconfirmar veredictos), que solo aplica si el motor no pudo decidir. | «caso abierto», «revisar a mano» |
| **orquestador** | `pipeline.py`: el componente que encadena las etapas del pipeline y cronometra cada una. | «el flujo», «run_full_flow» |
| **fetcher / adaptador** | El módulo que obtiene ofertas crudas de **una** fuente (API, RSS o navegador). «Scraper» se usa como sinónimo de fetcher; la distinción real es por **transporte**, no por nombre. | «adaptador», «scraper» |
| **`codigo_canonico`** | Identificador normalizado de un concepto (`skills`, `languages`, `license`, …) en la tabla `concepto`. **Sin él, el motor ignora el requisito en silencio.** | «código», «taxonomía» |
| **evidencia / `evidence`** | Cita literal del aviso que justifica un requisito (`job_requirements.evidence`). Es lo que se audita: el veredicto del Paso 5 debe poder rastrearse a la frase del texto. | «evidencia» |
| **huella del texto** | `text_hash` de `job_analysis`: sha256 de descripción + requisitos. Si cambia, el análisis queda obsoleto y hay que re-analizar. | «huella», «hash» |
| **salud de sitios** | Dos campos distintos: `source_sites.health_status` guarda la salud **acumulada** del sitio (`unknown`, `healthy`, `zero_results`, `needs_review`, `error`, `unsupported`, `requiere_login`) y `source_run_sites.status` el resultado de **una corrida** (`running`, `ok`, `zero_results`, `error`, `skipped`, `unsupported`, `requires_login`). Los disparadores de `review_required` y el efecto de `site mark-reviewed` se detallan en la fila «Salud de sitios» de «Subsistemas y comandos no detallados aquí» y en el manual. | (no aparece) |
| **idempotente** | Una ingesta repetida no duplica: actualiza la oferta existente y la cuenta como **duplicada en la corrida**. | «idempotente» |

Glosario de siglas y términos externos usados en este documento:

- **ANE** — Agencia Nacional de Empleo (portal público de Costa Rica; exige sesión).
- **API pública** — endpoint HTTP/REST/GraphQL sin credenciales, consultado con `httpx` o `urllib`; no abre navegador.
- **ATS** — *Applicant Tracking System* (Workday, Greenhouse, Ashby, Lever, Recruitee, Workable, SuccessFactors). **No confundir con el «ranking ATS»**, que es una puntuación propia de 0-100 y no toca los umbrales del Paso 5.
- **CDP** — *Chrome DevTools Protocol*; el puerto por el que se controla un Brave ya abierto (`BRAVE_CDP_PORT`, 9222 por defecto).
- **CINDE** — Cámara de Industriales, Desarrollo Económico e Inversión de Costa Rica; su portal de empleo `cindejobs.com` se consulta por API GraphQL pública (plataforma `cinde`).
- **corpus** — los avisos guardados en la BD SQLite local `data/jobpulse_v15.db`.
- **CR** — Costa Rica.
- **EGM «Hay»** — la convención de contratos documentales por directorio del bundle EGM: cada carpeta declara su interfaz, invariantes y efectos.
- **Elempleo** — portal de empleo de Latinoamérica (edición CR, `elempleo.com/cr`); se raspa con navegador (CDP) y **no tiene subcomando `scrape`**.
- **IMAP** — protocolo de correo con el que `postulaciones correo` lee el buzón de candidaturas.
- **keyring** — el Administrador de Credenciales de Windows; aquí guarda las contraseñas de ANE y del buzón. `credenciales set` guarda la contraseña en el keyring y los metadatos en `data/empresas/credenciales.json`.
- **llama-server** — servidor local del modelo IA (llama.cpp) que sirve el modelo al pase de enriquecimiento; lo arranca y apaga el proceso que lo necesita (ver `start_ia_server.py`).
- **RSS** — *Really Simple Syndication*: feed XML público (lo usa SuccessFactors) que se lee como una lista de avisos.
- **Playwright** — librería de automatización de navegador. Aquí actúa **solo
  como cliente CDP** (`connect_over_cdp` a Brave ya abierto): **nunca lanza
  chromium propio** (no hay ningún `chromium.launch()` en el repo).
- **harvie** — tablero ATS HeyHarvie (`heyharvie.com`, API pública paginada); corre en `run_ats_scrapes.py`, sin subcomando `scrape` propio.
- **payload** — la respuesta cruda de la fuente, tal como llegó, guardada para trazabilidad (`job_source_records`).
- **Procomer** — Promotora de Comercio Exterior de Costa Rica; portal de empleo `talento.procomer.com` (plataforma `procomer-cr`, API pública).
- **taxonomía** — el registro `concepto` (variante de texto → `codigo_canonico`) que el motor necesita para entender un requisito.
- **tenant** — el espacio de una empresa en la URL de Workday (`<tenant>.wdN.myworkdayjobs.com`).
- **VACUUM** — compactación del archivo SQLite (reconstruye la BD y reduce tamaño).

## Local Interface & Invariants

Scripts de raíz = operaciones manuales del pipeline. Todos se ejecutan con el
python del **venv** y `-X utf8` cuando imprimen texto de la BD.

| Script | Contrato |
|---|---|
| `run_full_flow.py` | Envoltorio del orquestador: corre `scrape → … → evidencia`. Flags `sites…`, `--pages`, `--only-scrape`, `--evaluar-todo`, `--no-notify` (omite la notificación de escritorio al terminar). Sin `sites` usa los sitios activos. Imprime `pipeline.resumen_linea`. |
| `run_enriquecimiento.py` | Pase IA (rellena `jobs.skills`/`jobs.languages`): `--solo-criticos` (solo los huecos de campos críticos, `ia_estado.CRITICOS`), `--confirmar-externo` (confirma que el texto de los avisos salga de la máquina hacia un proveedor IA externo). Arranca el `llama-server` local solo si él lo abre y lo apaga al terminar; después re-analiza **solo** el grupo «campos sin integrar» de la etapa 4 (`reananalizar_con_campos_fuente`), no el de texto cambiado. |
| `run_paso5.py` | Matching: `--dry` (no escribe), `--corrida`, `--evaluar-todo`. **Corrida NUEVA siempre** en `job_match`; por defecto solo evalúa las áreas marcadas en el perfil. |
| `run_scrapes.py` | Barrido mixto: **incluye** plataformas de API pública (`cinde`, `procomer`: `port=None`, sin CDP) y de navegador (`ane`, `indeed`, `linkedin`: exigen el `port` CDP de `browser_manager.puerto_cdp_configurado()`). |
| `run_ats_scrapes.py` | Barrido de tableros ATS (`ashby`, `greenhouse`, `harvie`, `lever`, `recruitee`, `successfactors`, `workable`, `workday`); `--platform`, `--site`, `--dry-run`, `--continue-on-error`. |
| `generar_evidencia_paso5.py` | Escribe `docs/PASO5_EVIDENCIA_<fecha>.md` de la corrida vigente. |
| `verificar_evidencia.py` | Verifica citas literales y firmas; **exit 0 = TODO CUADRA**. |
| `generar_revision_pendientes.py` | Escribe `docs/PASO5_REVISION_PENDIENTES.md` (casos `educacion_no_confirmada`). |
| `clean_run.py` | **Destructivo**: exige el argumento literal `SI`. Borra scraping y derivados, conserva perfil/sitios/taxonomías (más `source_sites_review_log`, tabla que ninguna migración crea — ver «Problemas conocidos de los lanzadores»), reinicia la salud de sitios y hace `VACUUM`. |
| `login_ane.py` | Login de ANE (`--port`, `--mantener-abierto`). Cierra por CDP y de forma ordenada **solo el Brave que él abrió**; `--mantener-abierto` lo deja vivo y un Brave preexistente no se toca. |
| `start_ia_server.py` | Arranca/verifica el `llama-server` local (`--check`); no lo detiene (lo apaga quien lo usa). |
| `instalar_modelo_ia.py` | Instalador del modelo IA local (`--check`, `--solo-modelo`, `--solo-llama`). |
| `migrar_perfil.py` | Importa un `profile.json` legado a `candidate_profile_facts`. Ruta por defecto: `<repo-v1x>\data\usuario\profile.json`, donde `<repo-v1x>` = el repo v1.x **archivado** de solo lectura (`D:\Proyectos\jobpulse_cr`). |
| `evidencia_descartadas.py`, `resumen_bloqueo.py` | Informes de solo lectura **sobre la BD**; escriben su `.txt`. |
| `verificar_corridas.py` | Trazabilidad de corridas de `job_match` (solo lectura). |
| `auditoria_db.py` | **Apunta a la ruta vieja** del repo v1.x archivado (`<repo-v1x>/v1_5`, un nivel más abajo que `migrar_perfil.py`): **no lo uses**; para el estado usa `tools/estado_bd.py`. |

Los adaptadores de scraping combinan tres transportes: **API pública/REST**,
**RSS** y **navegador** (este último exige CDP).

**Launchers** (`*.bat`/`.ps1`, operación de escritorio): `jobpulse-v15.bat` crea
el venv si falta, instala deps, **verifica CDP 9222 y abre Brave si no
responde**, y lanza la UI v2;
`jobpulse-v15-v2.bat` exige el venv y lanza la UI v2; `jobpulse-v15.ps1` elige
Brave, arranca CDP 9222 y lanza la UI v2; `ia-server.bat` delega en
`start_ia_server.py` e `instalar-modelo-ia.bat` en `instalar_modelo_ia.py`.

## Subdirectories & System Boundaries

- [`src/`](src/README.md) — el paquete instalable `jobpulse_v15` (todo el
  dominio, los scrapers, la IA y la UI v2).
- [`tools/`](tools/README.md) — scripts manuales de estado y medición. Dos
  escriben **datos** en la BD (`corrida_medicion.py`, `limpiar_null.py`) y otros
  cuatro (`estado_bd.py`, `cobertura_campos.py`, `ver_sitio.py`,
  `comparar_ia.py`) llaman `Database.initialize()`, que **puede aplicar
  migraciones pendientes** y mover `PRAGMA user_version`.
- `docs/` — bitácora por sesión (`HANDOFF_SESION_*.md`), reglas de negocio y
  evidencia generada (`PASO5_EVIDENCIA_*.md`, **no editar**). Sin código.
- [`docs/2026-11-13_DRIFT_REPORT.md`](docs/2026-11-13_DRIFT_REPORT.md) — informe
  de deriva EGM (contratos EGM vs. código real).
- [`goldfish_review_report.md`](goldfish_review_report.md) — informe del loop de
  revisión Goldfish sobre este README (vive en la raíz).
- `data/` — corpus real `jobpulse_v15.db` y datos personales (no versionados).
- `tests/` — suite `pytest` sobre BD temporales (sin red ni credenciales).

## Global Invariants

- **Esquema solo con migraciones** (`src/jobpulse_v15/migrations/0NN_*.sql`),
  nunca `ALTER` a mano; cambio de esquema = archivo nuevo.
- **Secretos y datos personales nunca al repo**: `.env`, `data/usuario/`,
  `data/empresas/` y los CV (`*.pdf/docx/doc`) están gitignoreados a propósito.
- **General, no "para mí"**: el perfil son hechos en la BD, los filtros
  `site_config` declarativos y las credenciales el Administrador de
  Credenciales de Windows (keyring).
- **Cada fetcher nuevo** lleva test en `tests/test_<nombre>.py`.
- **Todo requisito vigente** lleva `evidence` literal (trazable al texto).
- **El Paso 5 es siempre corrida nueva** y la viabilidad ≠ contratación (un
  rechazo no etiqueta la aptitud del perfil ni reentrena pesos).

## Global Side Effects

- **BD SQLite** `data/jobpulse_v15.db` (no versionada). Los respaldos los elige
  el operador: `backup --output <RUTA>` exige una ruta explícita (la convención
  del repo es `data/backups/X.db`).
- **Archivos escritos**: `.env` (IA y navegador), `~/.jobpulse_v15/ui_config.json`
  (incluye la **política de retención**: la aplica la UI v2 en
  `ui_v2/data/retencion.py`, **oculta** avisos antiguos según esa política y
  **nunca los borra**) y `data/empresas/*.json` (metadatos de credenciales;
  la contraseña va al keyring, ver «keyring»). La **purga real** de vacantes
  solo ocurre con `clean_run.py` (borrado total) o con un borrado manual; las
  postulaciones sobreviven porque `postulacion.job_id` pasa a `NULL`.
- **Directorios y cachés**: `data/usuario/sesiones/` (sesiones de navegador
  guardadas aparte), `data/usuario/ia_cache/` (caché del pase IA, por
  proveedor+modelo) y `docs/` (evidencia y hojas de firma, algunas **generadas**).
- **Datos de perfil y seguimiento**: `candidate_profile_facts` +
  `candidate_profile_imports` (importación de CV, reversible) y
  `postulacion` + `postulacion_senal` (registro de candidaturas por correo y
  Workday). Las credenciales del buzón viven en keyring o `.env`, nunca en la BD.
- **Procesos**: `llama-server` y Brave (CDP) se arrancan **solo si el ejecutor
  los abrió**; se usa el keyring de Windows.
- **Red (peticiones salientes)**: scraping (HTTP/HTTPS y CDP), cliente IA
  OpenAI-compatible e IMAP (buzón de postulaciones: servidor, puerto SSL,
  carpeta y credencial del keyring se pasan por flags).

## System Verification

Sin CI/linter/formatter: la verificación es la suite de `pytest`, que corre en
el **python del sistema** (el `.venv` no trae pytest). Ejecuta estos comandos
**fuera** de `.venv`:

```powershell
python -m pytest tests/ -q          # suite completa
python -m pytest tests/test_matching.py -q
```

Un archivo o un patrón: `python -m pytest tests/ -k <patrón> -q`. La suite
completa tarda **~20-25 min** porque muchos tests crean una BD temporal y
aplican las 28 migraciones en `setUp`; un archivo o un patrón corre en segundos.

### Prerrequisitos

- **App, CLI y scripts**: `.venv` con Python 3.11 (`py -3.11 -m venv .venv`) y
  `.\.venv\Scripts\python.exe -m pip install -e .` (siempre por `python -m pip`,
  no con `pip.exe` a secas). Extras: `[dev]` (pytest) e `[ia]` (openai,
  huggingface_hub); las dependencias solo se declaran en `pyproject.toml`.
- **Tests**: intérprete del **sistema** con pytest instalado
  (`py -3.11 -m pip install pytest`); pytest no es dependencia de runtime. Si
  `python` resuelve a otro intérprete, usa `py -3.11 -m pytest`.
- **Navegador**: la vía de navegador exige **dos componentes distintos**:
  1. **Brave instalado y arrancado con un puerto CDP abierto** — es el
     navegador que se controla. El puerto sale de `BRAVE_CDP_PORT` (9222 por
     defecto); el CLI **no** abre Brave por su cuenta, así que hay que
     levantarlo antes:
     `python -c "from jobpulse_v15.browser_manager import asegurar_brave; asegurar_brave(9222)"`
     o usar un launcher: `jobpulse-v15.ps1` lo arranca, y `jobpulse-v15.bat`
     verifica el puerto y **lo abre si no responde**.
  2. **Playwright** (opcional) — solo el paquete Python, como **cliente CDP** de
     Brave; no lo necesitan los tableros ATS ni las API públicas, que van por
     HTTP (detalles en «Playwright», Terminología).

**Quién abre Brave.** `scrape <plataforma>` (CLI) y `run_scrapes.py` **no**
abren navegador: exigen CDP ya arriba (ANE, Indeed, LinkedIn). En cambio, la
etapa `scrape` del orquestador —`run_full_flow.py`, `pipeline.ejecutar` y los
botones «Ejecutar grupo»/«Ejecutar seleccionados» de la UI v2— abre Brave
**bajo demanda** y cierra **solo** el que esa corrida abrió. Los launchers
`jobpulse-v15.bat`/`.ps1` lo abren antes de la UI, y `login_ane.py` lo abre y lo
cierra de forma ordenada (o lo deja vivo con `--mantener-abierto`).

- **IA local**: opcional (`instalar-modelo-ia.bat`); la externa se configura en
  `.env` con `IA_PROVEEDOR`/`IA_BASE_URL`/`IA_MODEL`.

## Subsistemas y comandos no detallados aquí

El manual funcional de abajo cubre la ingesta y la búsqueda. El resto de la CLI
existe y está documentado en [`src/jobpulse_v15/README.md`](src/jobpulse_v15/README.md):

| Subsistema | Comando(s) | Qué hace / etapa | Tabla(s) que lee o escribe |
|---|---|---|---|
| Viabilidad (ajuste técnico) | `viabilidad list [--banda aplicar]`, `viabilidad top [--limit N]` | **No** lee `job_match`: recalcula al vuelo con `EvaluadorPaso5` sobre el análisis vigente (`job_analysis` + hechos del perfil) | `job_analysis`, `job_requirements`, `candidate_profile_facts` |
| Viabilidad — bandas | (mismos comandos) | `aplicar` ≥85 · `revisar` ≥80 y <85 · `no_prioritario` <80 · `veto` = fuera de área del perfil o requisito educativo bloqueante confirmado · `sin_datos` = sin requisitos evaluables (aviso sin requisitos o sin ninguno comparable con el perfil) | — |
| Viabilidad — filtro de áreas | (mismos comandos) | El filtro de áreas del perfil se aplica salvo `--evaluar-todo` | `candidate_profile_facts` |
| Decisiones firmadas | `decision list`, `decision sign --file <firma.json>` (`--dry-run`) | Firma de **segunda persona** (distinta del autor del motor, para no autoconfirmar) sobre `educacion_no_confirmada`. Solo aplica si el motor no pudo decidir: `bloqueo_real` → `bloqueante` (`descartada`), `no_bloqueo` → `faltante` (`revisar_a_mano` / `educacion_no_cumple`), `dudoso` → sin cambio. **Nunca pisa un veredicto del motor.** `bloqueante` y `faltante` son estados **por requisito** (escala `cumple`, `faltante`, `bloqueante`, `no_confirmado`, `no_verificable`, `no_cumple`), no estados de la vacante; `educacion_no_cumple` es el motivo de revisión que acompaña al requisito educativo faltante. Es el hito «Paso 7», fuera del flujo del pipeline | `job_match_decision` |
| Métricas por etapa | `pipeline etapas [--limite N] [--corrida ID] [--json]` | Cronometraje por etapa que deja el orquestador | `pipeline_etapa` |
| Áreas de empleo | `init-areas [--classify]`, `areas list`, `areas classify [--dry-run]` | Taxonomía de áreas y clasificación de cada vacante | `area`, `area_regla`, `job_area` |
| Normalización canónica | `enrich requirements-source --apply` | **Etapa 4** (re-análisis): integra como requisitos los campos estructurados del aviso | `job_analysis`, `job_requirements` |
| Normalización canónica | `enrich requirements-canonico --apply` | **Etapa 5** (backfill): rellena `codigo_canonico` de los requisitos ya guardados | `job_requirements.codigo_canonico`, `concepto` |
| Normalización canónica | `enrich posting-language [--apply]` | Rellena el idioma del aviso cuando la fuente no lo da (regla local, no IA) | `jobs.posting_language` |
| Normalización canónica | `enrich work-mode [--apply]` | Rellena la modalidad **solo si está vacía** (nunca pisa una conocida ni editada a mano). **Sin `--apply` es dry-run** | `jobs.work_mode` |
| Normalización canónica | `enrich profile-canonico [--apply]` | Fuera del flujo: normaliza los datos del perfil candidato, no de los avisos | `candidate_profile_facts.codigo_canonico` |
| Taxonomía | `taxonomy curate [--apply] [--limit N]` | Reconstruye la cola de variantes sin normalizar (migración de datos, no un `UPDATE` manual) | `concepto`, `concepto_no_normalizado` |
| Postulaciones | `postulaciones correo --dias 90 [--apply]` (IMAP: `--host`, `--puerto`, `--carpeta`, `--cred`), `postulaciones workday --apply`, `postulaciones list` | Registro de candidaturas y señales de respuesta; `list` lo muestra. Solo derivados mínimos (el cuerpo del correo nunca se guarda) | `postulacion`, `postulacion_senal` |
| Registro de fuentes | `init-sources`, `site seed-cr`, `platform add`, `site add`, `credenciales` (`list`, `set`, `del`, `auto`, `add-site`, `rm-site`), `login` | Alta de plataformas, sitios y credenciales | `source_platforms`, `source_sites` |
| Scraping por plataforma | `scrape <plataforma>` (`ane`, `cinde`, `procomer`, `linkedin`, `indeed`, …) con `--site <id>`/`--group <g>`; `scrape ane --revisitar [--limite N]` re-baja el detalle de los avisos ya guardados (no usa el listado ni filtra por versión de parser) | **Etapa 1**. ANE/Indeed/LinkedIn exigen el puerto CDP; cinde/procomer van por API pública | `jobs`, `job_source_records`, `source_run_sites` |
| Scraping — Elempleo | (sin subcomando propio) | Solo corre vía `ejecutar_barrido` —la etapa `scrape` del orquestador, lanzada por `run_full_flow.py` o por «Ejecutar grupo»/«Ejecutar seleccionados» de la UI v2— con un sitio registrado (`ElempleoFetcher`) | `jobs`, `job_source_records`, `source_run_sites` |
| Salud de sitios | `site list --needs-review`, `site mark-reviewed --id <id>` | Bandera `review_required` con **tres disparadores**: `error` y `requires_login` la activan de inmediato; `zero_results` al llegar a **3 corridas seguidas con `jobs_found = 0`** (una corrida correcta la limpia; `error` y `requires_login` no modifican la racha). Nunca desactiva el sitio. Un sitio que pide sesión queda `requiere_login` y no suma a la racha de ceros. `mark-reviewed` limpia la bandera y reinicia la racha, pero conserva el `health_status` observado | `source_sites.review_required`, `source_run_sites` |
| Operación de base | `init-db`, `schema-version`, `backup --output <RUTA>`, `db check` | Crear/migrar, versionar, respaldar y verificar integridad | esquema completo |

El comando `enrich` aplica **reglas locales**, nunca IA. La sección «Esquema:
tablas del núcleo (manual heredado)» de más abajo describe solo el núcleo; el
listado completo de tablas
está en [`src/jobpulse_v15/migrations/README.md`](src/jobpulse_v15/migrations/README.md).

### Problemas conocidos de los lanzadores

- `jobpulse-v15.bat:45` fija `--user-data-dir="C:\Users\giova\...\Brave\User Data"`
  (ruta de una máquina concreta) y `jobpulse-v15.bat:28-29` /
  `jobpulse-v15.ps1:72-73` invocan `.venv\Scripts\pip` y
  `.venv\Scripts\playwright`, rutas que quedan obsoletas al mover el repo (un
  venv no se recrea al mover: usa siempre `python.exe -m pip`).
- `jobpulse-v15.ps1:11-20` sí resuelve Brave con `%ProgramFiles%`/
  `%LOCALAPPDATA%`, así que los dos lanzadores se contradicen.
- `source_sites_review_log` la usa `clean_run.py`, pero **ninguna migración la
  crea**: en una base recién inicializada no existe.

---

> **Jerarquía de este documento.** Las secciones de arriba son el **contrato
> vigente** y mandan en caso de conflicto. Lo que sigue es el **manual funcional
> heredado** de la fase de arranque: se conserva por su detalle operativo y
> puede citar interfaces ya retiradas (por ejemplo, la UI clásica).
>
> **Sobre las referencias a «la UI» del manual:** cuando una capacidad **existe
> hoy**, se dice **UI v2**; cuando pertenece a la **UI clásica retirada**, se
> marca como tal. La UI v2 es la única interfaz gráfica y tiene seis pestañas
> (Datos crudos, Perfil, Vacantes, Scraping, Cuentas, Configuración): puede
> agregar sitios **con inicio de sesión**, activar o pausar sitios existentes,
> exportar CSV y lanzar el pipeline, pero **no** ofrece el «Calidad de datos»,
> los estados manuales por vacante, los filtros de motivo de revisión ni la
> edición de datos de fuente. **El alta de plataformas y tableros** (incluidos
> los ATS) es **solo por CLI** (`platform add`, `site add`); el **scrape de
> sitios ya registrados** sí se lanza desde la pestaña «Scraping» de la UI v2
> («Ejecutar grupo»/«Ejecutar seleccionados») o por CLI
> (`scrape <plataforma>`).
>
> **Regla de lectura:** en el resto del manual, «UI clásica (retirada)» marca
> un control que **ya no existe**; la vía vigente se indica en cada caso (CLI
> o botón de la UI v2). Los listados de controles ausentes no se repiten: solo
> se mencionan aquí los que tienen equivalente actual.

## Manual funcional heredado

JobPulse CR v1.5 usa una base independiente en `data/jobpulse_v15.db`. No
modifica ni migra las bases de versiones anteriores (v1.x, `data/jobs.db`), que
viven en un repositorio aparte, archivado y de solo lectura.

## Alcance de esta fase

- Paquete Python independiente en `src/jobpulse_v15`.
- Persistencia SQLite independiente en `data/jobpulse_v15.db`.
- Migraciones SQL versionadas.
- Pruebas con bases temporales; no requieren red, perfil ni credenciales.

La base de v1.5 se crea al inicializar `Database` por primera vez. Las
migraciones se aplican únicamente al archivo de BD configurado para esa
instancia (por defecto `data/jobpulse_v15.db`); nunca tocan las bases de v1.x.

## Preparar y ejecutar

Crear un entorno virtual independiente e instalar el paquete (los prerrequisitos
completos están en «Prerrequisitos»):

```powershell
cd D:\Proyectos\v1_5
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Alternativa de un clic: `.\jobpulse-v15.bat` crea el venv si falta (con
`pip install -e .` y `playwright install chromium`, aunque el código no llega a
usar ese chromium), verifica CDP 9222 y **abre Brave si no responde**, y lanza
la UI. El servidor IA ya no se arranca aquí: lo levanta bajo demanda cualquier
ejecución que incluya la etapa `ia` con proveedor local («Enriquecer IA» o
«Procesar») y lo apaga al terminar; con proveedor externo no arranca nada. El
«pase IA de CV»
(`cv_ia.py`) era de la UI clásica: hoy solo queda como módulo (lo usan sus
tests), sin botón en la UI v2.

Inicializar la DB exclusiva de v1.5:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 init-db
```

La DB se crea en `data/jobpulse_v15.db` (relativa a la raíz del repo). Para
probar otro archivo, se puede indicar `--db C:\ruta\de\prueba.db` antes del
comando.

Para respaldar la base activa sin detener la aplicación:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 backup `
  --output .\data\backups\jobpulse-v15-2026-10-23.db
```

El respaldo usa la API de copia de SQLite, se valida con `integrity_check` y
no sobrescribe archivos existentes ni la base activa. La UI clásica (retirada)
ofrecía la misma acción con `Respaldar DB`; hoy el respaldo es **solo por
CLI**. Restaurar consiste en cerrar JobPulse, conservar una copia de la base
actual y reemplazar el archivo configurado por un respaldo verificado.

Para diagnosticar una base después de una restauración o copia manual:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 db check
```

El comando es de solo lectura, ejecuta `integrity_check` y `foreign_key_check`,
devuelve JSON y usa código de salida distinto de cero ante problemas.

## Interfaz de escritorio

> **Histórico.** Esta sección describe la **UI clásica** (`ui.py` con pestañas
> como «Calidad de datos», «Revisar duplicados», «Editar datos» o «Seguimiento»),
> retirada el 2026-11-11. La interfaz vigente es la **UI v2**
> ([`src/jobpulse_v15/ui_v2/README.md`](src/jobpulse_v15/ui_v2/README.md)), cuyas
> seis pestañas se listan arriba. Los controles citados abajo (estados manuales,
> filtros de revisión y edición de fuente) **ya no existen** en la interfaz.

**Filtros y resultados.** La interfaz Tkinter mostraba las vacantes guardadas,
permitía filtrarlas por texto, ubicación, modalidad e idioma, y revisar la
evidencia del análisis. Controles:

- `Calidad de datos`: mostraba un resumen global de vacantes que requieren
  revisión, faltantes de empresa/país/ubicación, estado de análisis y campos
  desconocidos o ambiguos, además de grupos candidatos a duplicados. El conteo
  cubría toda la base, no solo la página visible de resultados.
- `Revisar duplicados`: mostraba los primeros grupos candidatos e identificadores
  para validación manual.

**Análisis y estado manual.** También permitía ejecutar el extractor local
sobre la vacante seleccionada o, con `Analizar pendientes`, procesar tras
confirmación las vacantes visibles que aún no tienen análisis.

- El procesamiento era local, no volvía a analizar registros ya analizados y
  mostraba los errores por vacante.
- Permitía abrir el enlace de origen y registrar el estado manual de la vacante
  (`reviewed`, `applied`, `archived` o `dismissed`), guardar notas y excluir
  vacantes de la búsqueda normal; estas se podían volver a mostrar con el filtro
  correspondiente.
- Esa información manual se conservaba al actualizar la oferta.
- La lista podía ordenarse por actividad reciente o por fecha de publicación;
  en este último caso las ofertas sin fecha aparecían al final.
**Filtros de fecha, empleo, horario y salario.**

| Control | Comportamiento | Excepción |
|---|---|---|
| `Publicada desde` / `Publicada hasta` | Filtraba por fechas inclusivas en formato `AAAA-MM-DD` | Se podían dejar vacíos para no limitar el rango |
| `Tipo de empleo` / `Horario` | Aceptaban texto tal como aparece en los datos guardados (p. ej. `Full-time`, `Night shift`) y filtraban por coincidencia exacta | Vacíos = el filtro no se aplicaba |
| Rango salarial | Comparaba ofertas **solo con la misma moneda y periodo**; coincidía cuando el rango conocido se superponía con el solicitado | Exigía ambos valores de unidad; un extremo ausente se interpretaba como abierto, pero se exigía al menos un extremo conocido. No se convertían monedas ni periodos |
| `Moneda` / `Periodo salarial` | Filtros por coincidencia exacta, usables por separado | — |

**Exportación.** `Exportar CSV` guardaba los resultados de la última búsqueda
con sus filtros actuales, incluidos los códigos de motivos de revisión.
Exportaba los campos normalizados básicos, fechas, campos salariales
estructurados cuando estaban disponibles, compatibilidad del perfil y un enlace
a una fuente; no incluía descripción, requisitos originales ni payloads de la
fuente. Neutralizaba celdas cuyo contenido podría interpretarse como fórmula al
abrirlo en una hoja de cálculo. Se limitaba a los resultados cargados (según
`Max. resultados`) y visibles después del filtro de compatibilidad.

**Edición de datos.** `Editar datos` permitía corregir título, empresa, país,
provincia/región, ciudad y modalidad normalizados.

- Las correcciones prevalecen sobre futuras actualizaciones de la fuente;
  `Restaurar datos de fuente` las elimina y recupera los valores fuente más
  recientes.
- El campo `location_raw` y el payload original no se editaban.
- Los cambios se guardaban en la base v1.5 y no alteraban la aplicación ni la
  base legacy.

**Postulaciones.** El botón `Seguimiento` abría el historial opcional de
postulación: permitía anotar cambios de estado, fecha de aplicación, próxima
acción y notas. Cada registro era un evento separado; el seguimiento vigente
(`postulacion`) sobrevive a la purga de la vacante con `job_id` a `NULL`.

**Perfil e importación de CV.** El botón `Mi perfil` permitía registrar
manualmente datos estructurados tomados del CV o importar un PDF, DOCX o TXT
local; `Comparar perfil` contrastaba los datos guardados en el perfil con los requisitos
explícitos del análisis vigente.

- La importación probaba primero reglas locales y, si sugerían pocos datos,
  ofrecía un pase IA opcional (`cv_ia.py`, motor del `.env`: local o externo,
  con aviso de privacidad si es externo); todo pasaba por revisión antes de
  guardarse.
- Solo leía el archivo seleccionado, trabajaba localmente y no conservaba el
  texto extraído. Mostraba sugerencias y fragmentos detectados para revisión;
  solo las filas seleccionadas se guardaban.
- Reemplazar un dato existente requería confirmación.
- **Límites de importación**: PDF hasta **15 MB y 100 páginas**; DOCX y TXT
  hasta **15 MB**; TXT codificado en UTF-8. No se ejecutaba OCR en PDF
  escaneados y los documentos protegidos con contraseña no se admitían.

**Origen de los datos y comparación.**

- Los datos mostraban su origen (manual o archivo importado).
- `Revertir ultima importacion` deshacía la importación más reciente: eliminaba
  datos nuevos y restauraba valores previos que fueron reemplazados. Si un dato
  importado se editó manualmente después, ese cambio manual se conservaba.
- El historial guardaba solo el nombre del archivo y fecha, nunca la ruta ni el
  contenido del CV.
- La comparación usaba categoría y código exactos (o texto exacto si el
  requisito no traía código), validaba el nivel cuando ambos datos lo
  especificaban, el estado de estudios concluidos y el mínimo numérico de
  experiencia. Los requisitos inferidos o ambiguos requerían revisión.
- Un dato ausente del perfil se mostraba como `No registrado`; no significa que
  la persona no tenga esa competencia ni descarta automáticamente la vacante.
- Los códigos del perfil deben coincidir con los del requisito (por ejemplo
  `en`, `bachelor`, `years_experience`, `python` o `sql`).
- El extractor local identificaba idioma, educación, licencia, experiencia y un
  conjunto inicial de competencias técnicas comunes (Python, SQL, Excel, Power
  BI, Tableau, AWS, Azure, Google Cloud, Java, JavaScript, TypeScript, C++,
  C#, Linux, Git, AutoCAD, SolidWorks, MATLAB, SAP, PLC y Six Sigma) solo cuando
  aparecían en contexto de habilidades, herramientas, experiencia o con una
  señal explícita de requisito/preferencia.
- La importación de CV reutilizaba esas reglas como sugerencias, no como
  afirmaciones verificadas: había que revisar y, si era necesario, corregir
  categoría, código y dato usando `Editar sugerencia`; el fragmento original se
  mantenía como referencia antes de guardar. Las competencias fuera de ese
  vocabulario se marcaban como `unknown` si el texto indicaba una
  sección/contexto de habilidades, y requerían revisión manual; una mención
  casual por sí sola no se trataba como requisito.

**Filtro de compatibilidad.** La tabla de resultados mostraba el estado del
perfil y el filtro `Compatibilidad` permitía ver coincidencias de requisitos
obligatorios, datos no registrados, brechas conocidas, revisión manual, vacantes
sin análisis o sin requisitos obligatorios. Un análisis parcial se clasificaba
para revisión, no como incompatibilidad. El filtro se aplicaba a los resultados
cargados hasta el máximo indicado; aumentar `Max. resultados` permitía revisar
un conjunto mayor.

**Análisis bajo demanda.** La versión actual del extractor no reanaliza
históricos automáticamente: para actualizar el análisis de una vacante ya
guardada hoy se usa `analysis extract --job <id>` (CLI; ver «Extractor de
requisitos»).
`Analizar seleccionada` era el control de la UI clásica (retirada), que solo
consultaba la DB v1.5 y no iniciaba scraping automáticamente.

**Administración de fuentes (UI clásica, retirada).** La administración de
fuentes **permitía** agregar tableros Workday, Greenhouse, Ashby, Lever,
Recruitee, Workable y SuccessFactors, y consultar manualmente un tablero tras
confirmación (activar o pausar sitios **sigue disponible en la UI v2**). **Hoy
el alta es por CLI** (`site add`) y la ejecución corresponde a la pestaña
«Scraping» de la UI v2.
Las últimas corridas se consultan con
`run list --limit N` y el detalle de una corrida (sitios, conteos y errores)
con `run show --id <RUN_ID>`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 run list --limit 10
.\.venv\Scripts\python.exe -m jobpulse_v15 run show --id <RUN_ID>
```

La UI v2 (`jobpulse_v15.ui_v2`) también se abre con `jobpulse-v15-v2.bat`.

## Ingesta controlada de ofertas

> **Contrato común de todos los proveedores.** Cada fetcher (API pública, RSS o
> navegador) solo obtiene ofertas crudas: el registro, la validación y la
> escritura pasan siempre por `IngestionService`, que abre la corrida del sitio,
> guarda `job_source_records` y `source_job_memory`, es idempotente por
> `(site_id, source_job_id)` y actualiza la salud en `source_run_sites`. Desde
> ahí el pipeline es el mismo para todas las fuentes: `scrape → análisis → IA →
> re-análisis → backfill → Paso 5 → evidencia`. Ningún adaptador escribe en la
> base de versiones anteriores ni abre un navegador por su cuenta.

El comando `ingest import-json` importa resultados ya obtenidos desde un
archivo JSON local, sin hacer solicitudes web. Cada importación crea una
corrida acotada al sitio elegido, guarda la oferta y su identidad de origen,
detecta reimportaciones y registra los contadores de salud del sitio. El sitio
debe estar habilitado.

Formato: una lista de objetos, o un objeto con la propiedad `offers`. Cada
registro requiere `source_job_id` y `job.title`; se puede indicar un `job_id`
global opcional. Si se omite, se genera como `<site_id>:<source_job_id>`.
`job` acepta los campos normalizados del esquema, como `country`, `region`,
`city`, `work_mode`, `posting_language`, `description_raw` y
`requirements_raw`.

```json
{
  "offers": [
    {
      "source_job_id": "REQ-1001",
      "source_url": "https://careers.example.test/jobs/REQ-1001",
      "job": {
        "title": "Software Engineer",
        "company": "Example",
        "country": "CR",
        "city": "San Jose",
        "work_mode": "hybrid",
        "posting_language": "en",
        "description_raw": "Fluent English required."
      },
      "raw_payload": {
        "source_id": "REQ-1001"
      }
    }
  ]
}
```

Importar y luego analizar una oferta:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 ingest import-json `
  --site intel-cr --input .\offers.json
.\.venv\Scripts\python.exe -m jobpulse_v15 analysis extract --job intel-cr:REQ-1001
```

La importación es idempotente (ver el contrato comun de arriba): una oferta ya
conocida actualiza sus datos, pero se cuenta como duplicada en la corrida.
Una lista inválida se rechaza antes de crearla; si falla la escritura durante
la corrida, el error queda registrado para revisión y la CLI informa el fallo.

### Consulta explícita de tableros ATS

En todos los adaptadores de tableros, **el alta es de la CLI** (`site add`): la
UI v2 solo lanza el scrape y muestra los resultados de los tableros ya
registrados (pestaña «Scraping»).
Las **pruebas usan respuestas simuladas** y no consultan tableros ni portales
reales. El filtro de país usa `country_query` (se configura en el
`site_config_json` del sitio), que vale `Costa Rica` por defecto.

**Contrato común de los tableros ATS** (lo comparten los 7 adaptadores con
subcomando `scrape` propio; las diferencias están en las subsecciones de cada
proveedor):

| Elemento | Comportamiento común |
|---|---|
| Consulta | **Solo bajo demanda**: `scrape <plataforma> --site <id>` o `--group <g>` (nunca ambos). No se consulta al abrir la UI ni al importar el paquete |
| Alta | `platform add --id <p> --name <nombre> --provider-type api` (o `rss`) y luego `site add --id <s> --platform <p> --url <url> --company <empresa> --country CR` (opcional `--group`) |
| Filtrado | Por `country_query` (por defecto `Costa Rica`): cada adaptador decide en qué campos busca (título, ubicación principal o secundarias, oficinas, slug o descripción) y **omite** la oferta que no lo menciona en ninguno |
| Persistencia | El payload original se conserva; los registros se normalizan y pasan por `IngestionService` (el proveedor no accede a la base antigua) |
| Corridas | Cada sitio tiene su propia corrida; un fallo se registra y no impide los siguientes; la CLI devuelve código distinto de cero si hubo fallos |
| Modalidad | Solo se mapea si la fuente la expone; si no, queda `unknown` |

> **El marcador `<country_query> (multi-loc)` NO es común y no es un lugar.** En
> los tres adaptadores que lo emiten, `location_raw` guarda el texto literal
> `<country_query> (multi-loc)` (p. ej. `Costa Rica (multi-loc)`): significa
> «el país está en una ubicación secundaria o en el título» y ningún consumidor
> lo interpreta como ciudad; la normalización geográfica posterior tampoco lo
> convierte en una. Solo **Ashby, Lever y Recruitee**, cuando la ubicación
> principal no menciona el país y la oferta se aceptó porque aparecía en el
> título, en otra ubicación o en una lista, lo emiten. Los otros cuatro guardan
> lo que trae la fuente, sin marcador: **Greenhouse** busca solo en
> `location.name` y en los nombres de oficinas —si el país no está ahí la oferta
> se omite, aunque aparezca en el título—; **SuccessFactors** busca en título y
> slug (con la cola de la descripción como último recurso) y guarda
> `location_raw = country_query` tal cual; **Workday** normaliza ciudad/provincia
> con el catálogo `ubicaciones_cr` a partir de la jerarquía país → provincia →
> cantón → distrito; y **Workable** conserva la ubicación de la tabla sin
> marcador. **harvie** (HeyHarvie) es un 8.º adaptador de ATS: filtra por
> `country_query`, pero no tiene subcomando `scrape` (solo corre en un barrido
> con sitio registrado) y tampoco fabrica el marcador.

### Consulta explícita de tableros Workday

El paquete incluye un adaptador independiente para consultar tableros Workday. Usa
la URL del sitio para identificar tenant y tablero; por ejemplo:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add `
  --id workday --name Workday --provider-type api --default-language en
.\.venv\Scripts\python.exe -m jobpulse_v15 site add `
  --id intel-cr --platform workday --name "Intel Careers CR" `
  --url https://intel.wd1.myworkdayjobs.com/External `
  --company Intel --country CR
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape workday `
  --site intel-cr --pages 1
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape workday `
  --group directos --pages 1
```

Comportamiento: el comando admite de 1 a 10 páginas (20 anuncios por página), utiliza
`Costa Rica` como búsqueda por defecto, consulta detalles con una pausa entre
vacantes y registra resultados/error en una corrida del sitio. Un fallo HTTP o
una respuesta inesperada se informa como error y no se registra como 0 avisos. No
hay reintentos automáticos. El grupo procesa en secuencia sus sitios Workday
habilitados. El resultado JSON separa importaciones y fallos.

En la ventana `Administrar fuentes` de la **UI clásica (retirada)** se
seleccionaban uno o varios tableros activos y se usaba `Consultar seleccionadas`
para ejecutar la misma consulta secuencial con confirmación y resumen de
resultados/errores.

### Consulta explícita de tableros Greenhouse

Greenhouse expone una API pública por tablero. Registra la plataforma y un
tablero con URL `https://job-boards.greenhouse.io/<token>` o
`https://boards.greenhouse.io/<token>`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add `
  --id greenhouse --name Greenhouse --provider-type api
.\.venv\Scripts\python.exe -m jobpulse_v15 site add `
  --id acme-cr --platform greenhouse --name "Acme Careers CR" `
  --url https://job-boards.greenhouse.io/acme --company Acme `
  --country CR --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape greenhouse --site acme-cr
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape greenhouse --group directos
```

Comportamiento: cada tablero usa una petición al endpoint público de Greenhouse **con
descripciones**; solo se importan vacantes cuya ubicación o alguna oficina
contiene el texto `country_query`. La URL del tablero se valida contra los
dominios oficiales antes de construir la URL fija de API.

### Consulta explícita de tableros Ashby

Ashby ofrece una API pública por tablero. Registra la plataforma y el tablero
con una URL HTTPS de `jobs.ashbyhq.com`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add `
  --id ashby --name Ashby --provider-type api
.\.venv\Scripts\python.exe -m jobpulse_v15 site add `
  --id acme-cr --platform ashby --name "Acme Careers CR" `
  --url https://jobs.ashbyhq.com/acme --company Acme `
  --country CR --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape ashby --site acme-cr
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape ashby --group directos
```

Comportamiento: filtra por `country_query` en el título, la ubicación principal o las
ubicaciones secundarias. Si la ubicación principal no menciona el país, guarda
`<country_query> (multi-loc)` sin inferir ciudad ni provincia. La modalidad se
mapea solo si Ashby especifica modalidad remota, híbrida o presencial; de lo
contrario queda `unknown`.

### Consulta explícita de tableros Lever

Lever expone una API pública por tablero. Registra la plataforma y el tablero
con una URL HTTPS de `jobs.lever.co`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add `
  --id lever --name Lever --provider-type api
.\.venv\Scripts\python.exe -m jobpulse_v15 site add `
  --id acme-cr --platform lever --name "Acme Careers CR" `
  --url https://jobs.lever.co/acme --company Acme `
  --country CR --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape lever --site acme-cr
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape lever --group directos
```

Comportamiento: consulta primero el endpoint europeo de Lever y, si falla, reintenta
con el global. Filtra por `country_query` en el título, el país o las listas del
anuncio y completa la descripción con las secciones adicionales del anuncio. Si
la ubicación principal no menciona el país, guarda `<country_query> (multi-loc)`
sin inferir ciudad ni provincia. La modalidad no se deduce y queda `unknown`
porque Lever no la expone.

### Consulta explícita de tableros Recruitee

Recruitee expone una API pública por tablero. Registra la plataforma y el
tablero con una URL HTTPS cuyo subdominio identifica la empresa:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add `
  --id recruitee --name Recruitee --provider-type api
.\.venv\Scripts\python.exe -m jobpulse_v15 site add `
  --id acme-cr --platform recruitee --name "Acme Careers CR" `
  --url https://acme.recruitee.com --company Acme `
  --country CR --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape recruitee --site acme-cr
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape recruitee --group directos
```

Comportamiento: consulta `https://<token>.recruitee.com/api/offers/` y completa la
descripción con la sección de requisitos del anuncio. Filtra por `country_query`
en el título y en las ubicaciones; si la ubicación principal no menciona el país,
guarda `<country_query> (multi-loc)` sin inferir ciudad ni provincia. La
modalidad no se deduce y queda `unknown`.

### Consulta explícita de tableros Workable

Workable expone una API pública por cuenta. Registra la plataforma y el
tablero con una URL `https://apply.workable.com/<token>`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add `
  --id workable --name Workable --provider-type api
.\.venv\Scripts\python.exe -m jobpulse_v15 site add `
  --id acme-cr --platform workable --name "Acme Careers CR" `
  --url https://apply.workable.com/acme --company Acme `
  --country CR --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape workable --site acme-cr
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape workable --group directos
```

Comportamiento: descarga la lista del tablero como **markdown**
(`https://apply.workable.com/<token>/jobs.md`) y después la ficha de cada aviso
(`.../jobs/view/<id>.md`), con `urllib` y sin abrir navegador. Filtra por
`country_query` sobre el título y la ubicación de la tabla. Conserva la
ubicación tal como llega en `location_raw` y toma `country` del sitio: **no
infiere** ciudad ni provincia y **no fabrica** valores `<country_query> (multi-loc)`
(la normalización geográfica la hace después el pipeline de ubicaciones). La
modalidad se mapea desde la línea `**Workplace:**` del detalle (`remote`,
`hybrid`, `on-site`); si no aparece queda `unknown`. También extrae el tipo de
empleo del encabezado, la fecha de publicación y el salario como texto
(`salary_raw`), y guarda en `description_raw` la descripción con la sección de
requisitos.

### Consulta explícita de portales SuccessFactors

Los portales SAP SuccessFactors "Career Section" exponen un feed RSS público
sin credenciales. Registra la plataforma y el portal con su URL base HTTPS:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add `
  --id successfactors --name SuccessFactors --provider-type rss
.\.venv\Scripts\python.exe -m jobpulse_v15 site add `
  --id kn-cr --platform successfactors --name "Kuehne+Nagel CR" `
  --url https://careers.kuehne-nagel.com --company "Kuehne+Nagel" `
  --country CR --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape successfactors --site kn-cr
.\.venv\Scripts\python.exe -m jobpulse_v15 scrape successfactors --group directos
```

Comportamiento: consulta
`https://<portal>/services/rss/job/?locale=en_US&keywords=<country_query>`. El
filtro de la API no es estricto y puede traer vacantes de países vecinos, por
lo que v1.5 valida `country_query` **del lado cliente** sobre el título, el
enlace decodificado o el pie de la descripción (SAP suele indicar ahí la
ubicación). La descripción ya viene incluida en el RSS y no se consulta detalle
adicional. La fecha `pubDate` RFC 2822 se convierte a fecha ISO. Los portales
confirmados como compatibles son dominios por empresa como
`careers.kuehne-nagel.com`, `jobs.foundever.com` y `careers.ey.com`.

## Normalización de ubicaciones

Workday devuelve una ubicación original que v1.5 siempre conserva en
`location_raw` y en el payload de origen. Para Costa Rica, el adaptador separa
ciudad y provincia cuando recibe `Ciudad, Provincia, Costa Rica`, o reconoce
una provincia cuando recibe `Provincia, Costa Rica`. Una ubicación con una
estructura no reconocida permanece sin ciudad/provincia; no se adivina.
El adaptador usa solo la biblioteca estándar. Sus pruebas simulan las respuestas
y no hacen peticiones al portal.

`location normalize-workday` completa y corrige ciudad/provincia de los
registros **Workday** ya guardados. Lee el payload Workday persistido
(`job_source_records.raw_payload`), omite las ubicaciones no reconocidas y los
registros con fuentes conflictivas (`skipped_conflicting_sources`), y cuenta las
ciudades corregidas en `corrected_cities`. `--site` limita la operación a un
tablero y sin `--apply` solo muestra la simulación. **No es solo aditivo**:
rellena ciudad y provincia vacías y además **corrige** las ciudades que
`ciudad_es_basura` marca como inválidas —contienen «Costa Rica», un `_`,
dígitos, un nombre de país, el nombre de la empresa, o una provincia+zona que no
es una ciudad—; en ese caso no se respeta el valor existente:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 location normalize-workday `
  --site intel-cr
.\.venv\Scripts\python.exe -m jobpulse_v15 location normalize-workday `
  --site intel-cr --apply
```

`location normalize --platform <p> [--apply]` es el **backfill general**: cubre
**todas** las plataformas (Workday incluido) y trabaja sobre
`jobs.location_raw` y la descripción ya guardadas, **no** sobre el payload
Workday. Usa el mismo catálogo geográfico país → provincia → cantón → distrito
(módulo `ubicaciones_cr`, con la tabla de lugares como último recurso) y cuenta
`filled_city`, `filled_region`, `corrected_city` y `corrected_region`. No hace
consultas web. Respalda la base (`backup --output …`) antes de usar `--apply`.

## Ejecutar las pruebas

El contrato está en «System Verification»: pytest corre en el python del
**sistema** (el `.venv` no lo trae), nunca dentro del venv.

## Gestionar fuentes y vacantes

Las operaciones de persistencia viven en `jobpulse_v15.repository.Repository`.
Desde la CLI se pueden dar de alta plataformas y sitios, filtrar los sitios
habilitados que una corrida futura debe seleccionar y activar/pausar fuentes:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 platform add `
  --id workday --name Workday --provider-type api --default-language en
.\.venv\Scripts\python.exe -m jobpulse_v15 site add `
  --id intel-cr --platform workday --name "Intel Careers CR" `
  --url https://intel.wd1.myworkdayjobs.com/External --company Intel `
  --country CR --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 site list --enabled-only --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 site set-enabled --id intel-cr --disabled
```

Los sitios deben apuntar a una plataforma registrada. La configuración del
sitio es declarativa y se rechazan claves comunes de credenciales.
`select_sites` selecciona sitios activos, y el comando Workday puede recorrer
secuencialmente los tableros del grupo elegido.
`Repository.save_job` guarda la oferta, su registro de fuente y su memoria de
deduplicación en una sola transacción.

El registro de corridas distingue resultados vacíos de errores. Un `error` o una
petición de inicio de sesión marcan el sitio para revisión manual **de
inmediato**; tres corridas seguidas con `jobs_found = 0` (no con 0 avisos
nuevos) también lo marcan, sin desactivarlo. Solo `zero_results` incrementa la
racha; una corrida `ok` la reinicia, y `error`/`requires_login` no la modifican.
El ejemplo siguiente registra una corrida **a mano**
(p. ej. para pruebas o para un barrido hecho fuera del orquestador); el
scraping normal la registra solo:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 run start --kind full --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 run site-result `
  --id 1 --site intel-cr --found 0 --valid 0 --new 0 --duplicates 0
.\.venv\Scripts\python.exe -m jobpulse_v15 run finish --id 1
.\.venv\Scripts\python.exe -m jobpulse_v15 run show --id 1
.\.venv\Scripts\python.exe -m jobpulse_v15 run list --limit 10
.\.venv\Scripts\python.exe -m jobpulse_v15 site mark-reviewed --id intel-cr
```

En la UI clásica (retirada), una fuente que requiere revisión habilitaba
`Marcar revisada`; la vía vigente es la CLI `site mark-reviewed`: elimina la
bandera de revisión y reinicia la racha, pero conserva el último
`health_status` observado (incluidos `error` y `requiere_login`); no activa la
fuente ni ejecuta una consulta.

`jobs_found` cuenta ofertas recibidas del portal; si todas ya existían, se
registra un resultado exitoso con `--found` mayor que cero y `--new 0`, no
como un sitio sin resultados. Un error se registra con `--error "mensaje"`
y no incrementa la racha de ceros.

## Esquema: tablas del núcleo (manual heredado)

- `jobs`: identidad y campos comunes normalizados; conserva los textos
  originales cuando los proporciona la fuente.
- `source_platforms` y `source_sites`: plataformas, tableros y configuración
  declarativa.
- `job_source_records` y `source_job_memory`: datos originales por fuente y
  memoria mínima independiente de la retención de la oferta.
- `source_runs` y `source_run_sites`: resultados y salud por corrida y sitio.
- `job_analysis`, `job_requirements` y `job_field_status`: extracción
  versionada, requisitos con evidencia y estado de campos ausentes.
- `user_job_state` y `applications`: tablas **legado** de la UI clásica
  (estados manuales y seguimiento de entonces); siguen en el esquema, pero la
  UI v2 no las expone. Sus filas se borran en cascada con la vacante.
- `postulacion` y `postulacion_senal`: el seguimiento **vigente** (comandos
  `postulaciones`); el evento conserva `job_id` a `NULL` si la vacante se purga
  (`ON DELETE SET NULL`), de modo que la postulación sobrevive.

> Este listado es solo el **núcleo** del esquema, tal como lo describe el manual
> heredado: **no** delimita el alcance actual del sistema. Las tablas que quedan
> fuera se reparten en dos inventarios: el **listado completo** por migración,
> en
> [`src/jobpulse_v15/migrations/README.md`](src/jobpulse_v15/migrations/README.md),
> y la **tabla de subsistemas** de arriba, que dice qué comando toca qué tabla
> (`job_match`, `job_area`, `concepto`, `pipeline_etapa`, `job_match_decision`,
> `postulacion*`).

Los requisitos son filas relacionadas y repetibles, no columnas específicas
por portal. `posting_language` describe el idioma del anuncio y no implica
que ese idioma sea requisito del puesto. Hay dos vocabularios **ortogonales**:
el **nivel del requisito** (`required`, `preferred`, `inferred`, `ambiguous`) y
el **estado del campo** (`found`, `not_mentioned`, `unknown`, `ambiguous`).
`ambiguous` existe en ambos; `inferred` solo es nivel. Un `not_mentioned` o un
`unknown` no es un hecho equivalente a un requisito confirmado.

## Análisis estructurado y búsqueda

`Repository.save_analysis` guarda una revisión de análisis con requisitos
repetibles, evidencia, nivel (`required`, `preferred`, `inferred` o `ambiguous`),
origen, confianza y estados de campos (`found`, `not_mentioned`, `unknown` o
`ambiguous`). Cada revisión se asocia a la huella del texto y versión del
extractor; una nueva revisión pasa a ser la actual sin borrar el historial.
Si se marca una categoría como `found`, debe incluir al menos un requisito con
evidencia. `complete` no puede ocultar campos ambiguos o desconocidos.

```python
repository.save_analysis(
    "job-123",
    text_hash="sha256-of-description",
    extractor_version="rules-2+fuente",
    analysis_status="complete",
    source_site_id="intel-cr",
    source_config_hash="sha256-of-site-config",
    field_statuses={
        "language": "found",
        "education": "found",
        "license": "not_mentioned",
    },
    requirements=[
        {
            "category": "language",
            "value_code": "en",
            "value_text": "English",
            "requirement_level": "required",
            "evidence": "Advanced English required.",
            "origin": "rule",
            "confidence": 0.95,
        },
        {
            "category": "education",
            "value_code": "bachelor",
            "value_text": "Bachelor's degree",
            "education_status": "completed",
            "requirement_level": "required",
            "evidence": "Bachelor's degree required.",
            "origin": "rule",
            "confidence": 0.98,
        },
    ],
)

matches = repository.search_jobs(
    requirements=[
        {"category": "language", "value_code": "en"},
        {
            "category": "education",
            "value_code": "bachelor",
            "education_status": "completed",
        },
    ],
    filters={"country": "CR", "work_mode": "hybrid"},
)
```

Cada criterio solicitado debe coincidir (AND), pero una vacante aparece una
sola vez aunque coincida con varios requisitos. Por defecto la búsqueda exige
requisitos `required`; se pueden incluir preferencias/inferencias pasando
`requirement_levels`. Los filtros y criterios se validan y parametrizan en SQL.
`get_current_analysis` permite recuperar el análisis vigente con sus estados y
evidencias. El esquema migra automáticamente a la versión actual (28).

La búsqueda también está disponible desde la CLI; `--text` busca en título,
empresa, ubicación, descripción y `requirements_raw`, y se pueden repetir
criterios de requisitos:
```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 search `
  --text "quality engineer" --country CR --work-mode hybrid `
  --employment-type "Full-time" --schedule "Night shift" `
  --salary-currency USD --salary-period annual `
  --salary-at-least 5000 --salary-at-most 8000 `
  --requirement language=en `
  --requirement education=bachelor `
  --include-preferred --limit 25
```

La CLI devuelve JSON. Sin `--include-preferred`, `--include-inferred` o
`--include-ambiguous`, los criterios solo coinciden con requisitos marcados
como `required`. `--solo-requisitos-obligatorios` acota el resultado a los
avisos cuyo análisis vigente declara **al menos un requisito obligatorio**
(los `preferred` no cuentan). La búsqueda de texto trata `%`, `_` y `!` como
caracteres literales, no como comodines SQL.
La salida JSON se mantiene por defecto. `--format csv` produce el **export
controlado de la CLI** (`exports.write_job_search_csv`): mismas garantías del
export retirado —incluida la neutralización de celdas que podrían leerse como
fórmula (`=`, `+`, `-`, `@`)—, con identidad y ubicación normalizada, modalidad,
idioma, fecha, salario, `compatibilidad_perfil`, `motivos_revision`,
`url_fuente` y `requisitos_obligatorios`; **sin** descripción ni payload. La UI
v2 **no** genera ese mismo CSV: sus dos exportaciones propias son distintas
(datos crudos por un lado y ranking ATS por otro) y ninguna incluye
compatibilidad ni motivos de revisión. Ejemplo de export por CSV:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 search `
  --needs-review --format csv --sort-by date_published
```
El orden predeterminado `last_seen` ordena por `last_seen` descendente (el aviso
visto más recientemente primero).
`--sort-by date_published` ordena por fecha de publicación descendente y deja al
final las ofertas sin fecha conocida. `--published-from` y `--published-to`
aceptan fechas inclusivas en formato `AAAA-MM-DD`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 search `
  --published-from 2026-10-01 --published-to 2026-10-31
```
La revisión de datos se consulta con `--needs-review` en la CLI (en la UI v2 no
hay casilla equivalente: la UI clásica tenía el botón «Calidad de datos»).
Muestra
vacantes sin empresa o país, con ubicación original pero sin ciudad/provincia
normalizada, sin análisis registrado, con análisis pendiente/parcial/con error
o con campos `unknown` o `ambiguous`. No se marca por si sola como error una
modalidad desconocida, un idioma no determinado o un campo `not_mentioned`:
estos estados pueden significar que la fuente no los proporciona o que las
reglas no encontraron una mención. Esta vista prioriza la revisión, pero no
modifica los datos ni convierte incertidumbre en un hecho.

Los resultados incluyen `review_reasons` en el JSON de búsqueda, con códigos
estables como `missing_company`, `location_not_normalized`,
`analysis_partial` o `unknown_field:license`. Son la **forma actual y estable**
del resumen que la UI clásica (retirada) mostraba como «Calidad de datos»: los
calcula el motor de búsqueda (`repository.search_jobs`) y los expone el CLI. La
interfaz antigua ponía el conteo en la columna `Datos` y detallaba los motivos al
seleccionar la vacante; la UI v2 no expone esa columna. Cuando no hay motivos
detectados, el JSON trae la lista `review_reasons` **vacía** (`[]`) y el CSV una
celda vacía (el `OK` era el texto que pintaba la UI clásica); esto no garantiza
que todos los datos sean correctos, solo que las reglas actuales no detectaron
faltantes.

El filtro `Motivo de revision` de la UI clásica limitaba los resultados a un
código; por
ejemplo, `missing_country`, `analysis_partial` o `unknown_field:license`.
La CLI acepta el mismo filtro con `--review-reason`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 search `
  --review-reason location_not_normalized
```
La CLI también permite usar `--profile-compatibility` con los estados
`matched`, `not_registered`, `below_requirement`, `needs_review`,
`not_analyzed` o `no_required`. Por ejemplo:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 search `
  --profile-compatibility matched
```
Cuando se solicita este filtro, la salida JSON incluye la etiqueta
`profile_compatibility`; el CSV expone la columna `compatibilidad_perfil` con
**los mismos valores** y aplica el filtro antes de exportar. **Esta comparación
es informativa del motor de búsqueda** (`compare_jobs_to_candidate_profile`): no
es el veredicto del Paso 5 ni usa sus estados. La comparación usa solo los
hechos guardados del perfil (la importación ya pasó por revisión antes de
guardarse, así que no hay un estado «aprobado» aparte): no significa que un
requisito no registrado sea una carencia real.

Las vacantes con `skip_automatic = 1` se excluyen por defecto de la búsqueda;
usa `--include-manually-skipped` para volver a incluirlas. Ese estado lo fijaba
la UI clásica (botón «Excluir de la búsqueda»); la UI v2 no lo expone, de modo
que en la práctica solo se activa por SQL o por una edición puntual de la base.
Por otro lado, **el adaptador Workday** evita descargar el detalle de un aviso
cuyo ID de origen reconoce en el listado resumido y lo cuenta como omitido, no
como cero resultados; si no puede reconocer un ID estable, Workday puede requerir
descargar el detalle para identificarlo. El filtro `skip_automatic` no interviene
en esa decisión del adaptador.

## Extractor de requisitos

La versión del extractor por reglas es `rules-2` (`analysis.py`), pero lo que
se **guarda** en `job_analysis` hoy es `rules-2+fuente`
(`analysis_flow.VERSION_ANALISIS = f"{EXTRACTOR_VERSION}+fuente"`), que
además integra los campos estructurados de la fuente. Reconoce frases
explícitas en inglés y español para idiomas, estudios
universitarios/secundarios, licencia de
conducir **con su clase** (`B1`, `D3`...) y años de experiencia, y extrae
competencias técnicas con un vocabulario cerrado (Python, SQL, Excel, Power BI,
AWS, Java, Linux, SAP...). No usa red ni IA. Los hallazgos guardan como
evidencia la frase que activó la regla; los indicadores de preferencia y
obligatoriedad se clasifican por separado. Cuando el texto alude a un requisito
que las reglas no pueden interpretar, el campo queda `unknown`, no se presenta
como ausente.
Un campo `not_mentioned` significa que no se detectaron menciones de esa
categoría en las reglas actuales, por lo que los resultados deben revisarse
antes de utilizarlos para excluir candidatos u ofertas.

Para extraer y persistir el análisis de una oferta ya guardada:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 analysis extract --job job-123
```

El comando analiza `description_raw` y `requirements_raw`, registra la huella
del texto y la configuración de la fuente, y conserva las revisiones anteriores.
`get_current_analysis` permite revisar los requisitos y la evidencia devueltos.
Para procesar en lote solo vacantes que no tengan análisis vigente, usa:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 analysis extract-pending `
  --limit 25 --dry-run
.\.venv\Scripts\python.exe -m jobpulse_v15 analysis extract-pending `
  --limit 25
```

El limite permitido es de 1 a 500 (predeterminado 25). El modo normal es local y
no consulta sitios web; no reanaliza vacantes que ya tienen análisis, devuelve
resumen y errores por vacante, y retorna código de salida distinto de cero si
algun registro fallo. Las vacantes sin texto quedan reportadas como error. Para
incluir
vacantes excluidas manualmente de las búsquedas normales, agrega
`--include-manually-skipped`.
El informe global de calidad también está disponible como JSON:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 quality report
.\.venv\Scripts\python.exe -m jobpulse_v15 quality duplicates --limit 100
```

La detección de posibles duplicados agrupa por título, empresa, país y ciudad
normalizados (sin distinguir mayúsculas, acentos ni puntuación). Solo incluye
registros con esos cuatro campos disponibles. Son candidatos para revisión
manual, no confirmaciones: el sistema nunca fusiona ni elimina vacantes
automáticamente. La salida lista los identificadores de cada grupo.
Los totales incluyen todas las vacantes de la base y no están limitados por
los filtros de búsqueda ni por el `Max. resultados` de la UI clásica (retirada).

No se guardan credenciales en la configuración de sitios. El JSON de
configuración es declarativo y no se ejecuta como código.
