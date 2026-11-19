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

El orquestador (`pipeline.py`) ejecuta siete etapas, siempre en este orden:

`1 scrape → 2 análisis → 3 IA → 4 re-análisis → 5 backfill → 6 Paso 5 → 7 evidencia`

(La lista canónica es `pipeline_metricas.ETAPAS`; el **Paso 5 es la etapa 6**,
porque la numeración del «Paso 5» es histórica y no coincide con la posición
dentro del flujo.)

- **Etapa 2 antes que la 3**: los scrapers no rellenan `jobs.skills` ni
  `jobs.languages`; los produce el pase IA. Sin la etapa 3, la etapa 4 no tiene
  nada que integrar y la taxonomía queda sin cubrir.
- **Etapa 4 antes que la 5**: hasta que los campos estructurados del aviso no
  se integran como requisitos, no existen filas que normalizar. La etapa 4 la
  implementa `enrich requirements-source --apply`.
- **Etapa 5 antes que la 6**: `enrich requirements-canonico --apply` rellena
  `job_requirements.codigo_canonico` solo donde falta; **un requisito sin
  `codigo_canonico` se ignora en silencio**, así que la vacante se evalúa con
  menos requisitos de los que realmente pide.
- **Etapa 6 = corrida nueva**: cada ejecución escribe filas nuevas en
  `job_match` con su `corrida_id` y marca `valida=0` en las anteriores; nunca se
  actualiza en sitio. Estados posibles: `calificada`, `revisar_a_mano`,
  `descartada`, `datos_insuficientes`, `sin_requisitos`,
  `baja_compatibilidad`, `fuera_de_area`.

El comando que encadena las siete etapas es `run_full_flow.py` (o el botón
«Procesar» de la UI v2). Las etapas sueltas se ejecutan por CLI; cada una tiene
su comando en la tabla «Subsistemas y comandos no detallados aquí».

> `run_enriquecimiento.py` es un **atajo**: hace la etapa 3 (IA) y encadena la
> etapa 4 al terminar, porque un pase IA que no re-analiza deja el texto
> desactualizado. No es una etapa aparte ni un segundo re-análisis.

## Terminología

Vocabulario canónico del proyecto. El manual funcional heredado (más abajo) usa
a veces otra palabra para el mismo concepto; manda esta tabla.

| Término canónico | Significado | Cómo lo llama el manual heredado |
|---|---|---|
| **Paso 5** | El motor de matching (`matching.py`). Escribe `job_match`. | «comparación con el perfil», «compatibilidad» |
| **corrida** | Una ejecución registrada: fila de `source_runs` o de `job_match` con su `corrida_id`. | «corrida», «historial» |
| **análisis** | Fila de `job_analysis` con sus `job_requirements` (versión `rules-2`). | «análisis», «busqueda/extracción» |
| **re-análisis** | Reejecutar el análisis porque cambió el texto del aviso o porque se integraron campos nuevos. | «reanalizar» |
| **backfill** | Rellenar `codigo_canonico` en requisitos ya guardados. | (no aparece) |
| **UI v2** | La única interfaz gráfica (`ui_v2/`). | «interfaz Tkinter», «aplicación», «ventana» |
| **áreas** | Clasificación de la vacante en `job_area` desde `seeds/areas.json`. «Las áreas marcadas en el perfil» = las que el perfil declara como objetivo. | «áreas» |
| **viabilidad** | Banda de **ajuste técnico** perfil↔aviso (0-100). No es probabilidad de contratación. | (no aparece) |
| **Paso 7** | Numeração **histórica de los hitos del proyecto**, no de las etapas del pipeline: es la fase en que se firman las decisiones de segunda persona sobre la educación no confirmada (`job_match_decision`). | «firma de decisiones» |
| **educacion_no_confirmada** | Caso de revisión manual: el motor no pudo decidir si el aviso exige un título universitario (no lo descarta nunca por falta de información). Lo resuelve una **firma de segunda persona**, que solo aplica si el motor no pudo decidir. | «caso abierto», «revisar a mano» |
| **orquestador** | `pipeline.py`: el componente que encadena las etapas del pipeline y cronometra cada una. | «el flujo», «run_full_flow» |
| **fetcher / adaptador** | El módulo que obtiene ofertas crudas de **una** fuente (API, RSS o navegador). «Scraper» se usa como sinónimo de fetcher; la distinción real es por **transporte**, no por nombre. | «adaptador», «scraper» |
| **`codigo_canonico`** | Identificador normalizado de un concepto (`skills`, `languages`, `license`, …) en la tabla `concepto`. **Sin él, el motor ignora el requisito en silencio.** | «código», «taxonomía» |
| **evidencia / `evidence`** | Cita literal del aviso que justifica un requisito (`job_requirements.evidence`). Es lo que se audita: el veredicto del Paso 5 debe poder rastrearse a la frase del texto. | «evidencia» |
| **huella del texto** | `text_hash` de `job_analysis`: sha256 de descripción + requisitos. Si cambia, el análisis queda obsoleto y hay que re-analizar. | «huella», «hash» |
| **salud de sitios** | Estado de un sitio en `source_run_sites`: `ok`, `zero_results`, `error`, `requires_login` (pide sesión) y la bandera `review_required` en `source_sites`, que se activa tras **3 corridas seguidas con 0 avisos** y no desactiva el sitio. `site mark-reviewed` la limpia. | (no aparece) |
| **idempotente** | Una ingesta repetida no duplica: actualiza la oferta existente y la cuenta como **duplicada en la corrida**. | «idempotente» |

Glosario de siglas y términos externos usados en este documento:

- **ANE** — Agencia Nacional de Empleo (portal público de Costa Rica; exige sesión).
- **API pública** — endpoint HTTP/REST/GraphQL sin credenciales, consultado con `httpx` o `urllib`; no abre navegador.
- **ATS** — *Applicant Tracking System* (Workday, Greenhouse, Ashby, Lever, Recruitee, Workable, SuccessFactors). **No confundir con el «ranking ATS»**, que es una puntuación propia de 0-100 y no toca los umbrales del Paso 5.
- **CDP** — *Chrome DevTools Protocol*; el puerto por el que se controla un Brave ya abierto (`BRAVE_CDP_PORT`, 9222 por defecto).
- **corpus** — los avisos guardados en la BD SQLite local `data/jobpulse_v15.db`.
- **CR** — Costa Rica.
- **EGM «Hay»** — la convención de contratos documentales por directorio del bundle EGM: cada carpeta declara su interfaz, invariantes y efectos.
- **IMAP** — protocolo de correo con el que `postulaciones correo` lee el buzón de candidaturas.
- **keyring** — el Administrador de Credenciales de Windows; aquí guarda las contraseñas de ANE y del buzón.
- **RSS** — *Really Simple Syndication*: feed XML público (lo usa SuccessFactors) que se lee como una lista de avisos.
- **Playwright** — librería de automatización de navegador; su chromium solo hace falta en los scrapers de navegador.
- **httpx** — cliente HTTP asíncrono con soporte HTTP/2; es la dependencia de red declarada en `pyproject.toml` y la usa el grueso de los adaptadores.
- **urllib** — módulo de la biblioteca estándar de Python para HTTP; algunos adaptadores lo usan sin dependencias externas.
- **payload** — la respuesta cruda de la fuente, tal como llegó, guardada para trazabilidad (`job_source_records`).
- **taxonomía** — el registro `concepto` (variante de texto → `codigo_canonico`) que el motor necesita para entender un requisito.
- **tenant** — el espacio de una empresa en la URL de Workday (`<tenant>.wdN.myworkdayjobs.com`).
- **VACUUM** — compactación del archivo SQLite (reconstruye la BD y reduce tamaño).

## Local Interface & Invariants

Scripts de raíz = operaciones manuales del pipeline. Todos se ejecutan con el
python del **venv** y `-X utf8` cuando imprimen texto de la BD.

| Script | Contrato |
|---|---|
| `run_full_flow.py` | Envoltorio del orquestador: corre `scrape → … → evidencia`. Flags `sites…`, `--pages`, `--only-scrape`, `--evaluar-todo`, `--no-notify`. Sin `sites` toma los activos. Imprime `pipeline.resumen_linea`. |
| `run_enriquecimiento.py` | Pase IA (rellena `jobs.skills`/`jobs.languages`): `--solo-criticos`, `--confirmar-externo`. Arranca el `llama-server` local solo si él lo abre y lo apaga al terminar; re-analiza después. |
| `run_paso5.py` | Matching: `--dry` (no escribe), `--corrida`, `--evaluar-todo`. **Corrida NUEVA siempre** en `job_match`; por defecto solo evalúa las áreas marcadas en el perfil. |
| `run_scrapes.py` | Barrido mixto: **incluye** plataformas de API pública (`cinde`, `procomer`: `port=None`, sin CDP) y de navegador (`ane`, `indeed`, `linkedin`: exigen el `port` CDP de `browser_manager.puerto_cdp_configurado()`). |
| `run_ats_scrapes.py` | Barrido de tableros ATS (`ashby`, `greenhouse`, `harvie`, `lever`, `recruitee`, `successfactors`, `workable`, `workday`); `--platform`, `--site`, `--dry-run`, `--continue-on-error`. |
| `generar_evidencia_paso5.py` | Escribe `docs/PASO5_EVIDENCIA_<fecha>.md` de la corrida vigente. |
| `verificar_evidencia.py` | Verifica citas literales y firmas; **exit 0 = TODO CUADRA**. |
| `generar_revision_pendientes.py` | Escribe `docs/PASO5_REVISION_PENDIENTES.md` (casos `educacion_no_confirmada`). |
| `clean_run.py` | **Destructivo**: exige el argumento literal `SI`. Borra scraping y derivados, conserva perfil/sitios/taxonomías (más `source_sites_review_log`, tabla que ninguna migración crea), reinicia la salud de sitios y hace `VACUUM`. |
| `login_ane.py` | Login de ANE (`--port`, `--mantener-abierto`). Cierra por CDP y de forma ordenada **solo el Brave que él abrió**; `--mantener-abierto` lo deja vivo y un Brave preexistente no se toca. |
| `start_ia_server.py` | Arranca/verifica el `llama-server` local (`--check`); no lo detiene (lo apaga quien lo usa). |
| `instalar_modelo_ia.py` | Instalador del modelo IA local (`--check`, `--solo-modelo`, `--solo-llama`). |
| `migrar_perfil.py` | Importa un `profile.json` legado a `candidate_profile_facts`. Ruta por defecto: `<repo-v1x>\data\usuario\profile.json` (el repo v1.x **archivado**, de solo lectura; `auditoria_db.py` apunta a otro nivel, `<repo-v1x>\v1_5\…`). |
| `evidencia_descartadas.py`, `resumen_bloqueo.py` | Informes de **solo lectura** (escriben su `.txt`). |
| `verificar_corridas.py` | Trazabilidad de corridas de `job_match` (solo lectura). |
| `auditoria_db.py` | **Apunta a la ruta vieja** del repo v1.x archivado (`<repo-v1x>/v1_5`): **no lo uses**; para el estado usa `tools/estado_bd.py`. |

Los adaptadores de scraping combinan tres transportes: **API pública/REST**,
**RSS** y **navegador** (este último exige CDP).

**Launchers** (`*.bat`/`.ps1`, operación de escritorio): `jobpulse-v15.bat` crea
el venv si falta, instala deps, verifica CDP 9222 y lanza la UI v2;
`jobpulse-v15-v2.bat` exige el venv y lanza la UI v2; `jobpulse-v15.ps1` elige
Brave, arranca CDP 9222 y lanza la UI v2; `ia-server.bat` e
`instalar-modelo-ia.bat` delegan en los scripts Python homónimos.

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
  rechazo nunca etiqueta aptitud ni reentrena pesos).

## Global Side Effects

- **BD SQLite** `data/jobpulse_v15.db` (no versionada). Los respaldos los elige
  el operador: `backup --output <RUTA>` exige una ruta explícita (la convención
  del repo es `data/backups\X.db`).
- **Archivos escritos**: `.env` (IA y navegador), `~/.jobpulse_v15/ui_config.json`
  (incluye la política de retención) y `data/empresas/*.json`.
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
python -m pytest tests/ -q          # suite completa (~20-25 min)
python -m pytest tests/test_matching.py -q
```

Un archivo o un patrón: `python -m pytest tests/ -k <patrón> -q`. Muchos tests
crean una BD temporal y aplican las 28 migraciones en `setUp`: la suite tarda
minutos, no segundos.

### Prerrequisitos

- **App, CLI y scripts**: `.venv` con Python 3.11 (`py -3.11 -m venv .venv`) y
  `pip install -e .`. Extras: `[dev]` (pytest) e `[ia]` (openai,
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
     o usar el launcher `jobpulse-v15.ps1`, que ya lo hace.
  2. **chromium de Playwright** (opcional) — solo para la capa de automatización;
     no lo necesitan los tableros ATS ni las API públicas, que van por HTTP.
- **IA local**: opcional (`instalar-modelo-ia.bat`); la externa se configura en
  `.env` con `IA_PROVEEDOR`/`IA_BASE_URL`/`IA_MODEL`.

## Subsistemas y comandos no detallados aquí

El manual funcional de abajo cubre la ingesta y la búsqueda. El resto de la CLI
existe y está documentado en [`src/jobpulse_v15/README.md`](src/jobpulse_v15/README.md):

| Subsistema | Comando(s) | Qué hace / etapa | Tabla(s) que lee o escribe |
|---|---|---|---|
| Viabilidad (ajuste técnico) | `viabilidad list [--banda aplicar]`, `viabilidad top [--limit N]` | Lee `job_match`; bandas `aplicar` ≥85, `revisar` 80-85, `no_prioritario` <80, `sin_datos`, `veto` | `job_match` |
| Decisiones firmadas | `decision list`, `decision sign --file <firma.json>` (`--dry-run`) | Firma de **segunda persona** sobre `educacion_no_confirmada`. Solo aplica si el motor no pudo decidir: `bloqueo_real` → descarta, `no_bloqueo` → falta, `dudoso` → sin cambio. **Nunca pisa un veredicto del motor.** Es el hito «Paso 7», fuera del flujo del pipeline | `job_match_decision` |
| Métricas por etapa | `pipeline etapas [--limite N] [--corrida ID] [--json]` | Cronometraje por etapa que deja el orquestador | `pipeline_etapa` |
| Áreas de empleo | `init-areas [--classify]`, `areas list`, `areas classify [--dry-run]` | Taxonomía de áreas y clasificación de cada vacante | `area`, `area_regla`, `job_area` |
| Normalización canónica | `enrich requirements-source --apply` | **Etapa 4** (re-análisis): integra como requisitos los campos estructurados del aviso | `job_analysis`, `job_requirements` |
| Normalización canónica | `enrich requirements-canonico --apply` | **Etapa 5** (backfill): rellena `codigo_canonico` de los requisitos ya guardados | `job_requirements.codigo_canonico`, `concepto` |
| Normalización canónica | `enrich posting-language [--apply]` | Rellena el idioma del aviso cuando la fuente no lo da (regla local, no IA) | `jobs.posting_language` |
| Normalización canónica | `enrich work-mode` | Rellena la modalidad **solo si está vacía** (nunca pisa una conocida ni editada a mano) | `jobs.work_mode` |
| Normalización canónica | `enrich profile-canonico [--apply]` | Fuera del flujo: normaliza los datos del perfil candidato, no de los avisos | `candidate_profile_facts.codigo_canonico` |
| Taxonomía | `taxonomy curate [--apply] [--limit N]` | Reconstruye la cola de variantes sin normalizar (migración de datos, no un `UPDATE` manual) | `concepto`, `concepto_no_normalizado` |
| Postulaciones | `postulaciones correo --dias 90 [--apply]` (IMAP: `--host`, `--puerto`, `--carpeta`, `--cred`), `postulaciones workday --apply` | Registro de candidaturas y señales de respuesta; solo derivados mínimos (el cuerpo del correo nunca se guarda) | `postulacion`, `postulacion_senal` |
| Registro de fuentes | `init-sources`, `site seed-cr`, `platform add`, `site add`, `credenciales` (`list`, `set`, `del`, `auto`, `add-site`, `rm-site`), `login` | Alta de plataformas, sitios y credenciales | `source_platforms`, `source_sites` |
| Salud de sitios | `site list --needs-review`, `site mark-reviewed --id <id>` | Bandera `review_required`: se activa tras **3 corridas seguidas con 0 avisos** y **no desactiva el sitio**. Un sitio que pide sesión tiene estado `requires_login` (no cuenta para la racha de ceros) | `source_sites.review_required`, `source_run_sites` |
| Operación de base | `init-db`, `schema-version`, `backup --output <RUTA>`, `db check` | Crear/migrar, versionar, respaldar y verificar integridad | esquema completo |

El comando `enrich` aplica **reglas locales**, nunca IA. La sección «Esquema
inicial» de más abajo describe solo el núcleo; el listado completo de tablas
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
> marca como tal. La UI v2 tiene seis pestañas (Datos crudos, Perfil, Vacantes,
> Scraping, Cuentas, Configuración): puede agregar sitios, consultar tableros,
> exportar CSV y lanzar el pipeline, pero **no** ofrece el «Calidad de datos»,
> los estados manuales por vacante, los filtros de motivo de revisión ni la
> edición de datos de fuente.

## Documentación funcional

JobPulse CR v1.5 usa una base independiente en `data/jobpulse_v15.db`. No
modifica ni migra las bases de versiones anteriores (v1.x, `data/jobs.db`), que
viven en un repositorio aparte, archivado y de solo lectura.

## Alcance de esta fase

- Paquete Python independiente en `src/jobpulse_v15`.
- Persistencia SQLite independiente en `data/jobpulse_v15.db`.
- Migraciones SQL versionadas.
- Pruebas con bases temporales; no requieren red, perfil ni credenciales.

La base de v1.5 se crea al inicializar `Database` por primera vez. Las
migraciones solo modifican la ruta de base configurada para esa instancia.

## Preparar y ejecutar

Crear un entorno virtual independiente e instalar el paquete:

```powershell
cd D:\Proyectos\v1_5
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Alternativa de un clic: `.\jobpulse-v15.bat` crea el venv si falta (con
`pip install -e .` y chromium de playwright), abre Brave con CDP 9222 y lanza
la UI. El servidor IA ya no se arranca aquí: la UI lo levanta bajo demanda
(botón "Enriquecer" o pase IA de CV) y lo apaga al terminar.

Inicializar la DB exclusiva de v1.5:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 init-db
```

La DB se crea en `v1_5/data/jobpulse_v15.db`. Para probar otro archivo, se
puede indicar `--db C:\ruta\de\prueba.db` antes del comando.

Para respaldar la base activa sin detener la aplicación:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 backup `
  --output .\backups\jobpulse-v15-2026-10-23.db
```

El respaldo usa la API de copia de SQLite, se valida con `integrity_check` y
no sobrescribe archivos existentes ni la base activa. La UI ofrece la misma
accion con `Respaldar DB`; restaurar consiste en cerrar JobPulse, conservar
una copia de la base actual y reemplazar el archivo configurado por un respaldo
verificado.
Para diagnosticar una base despues de una restauracion o copia manual:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 db check
```

El comando es de solo lectura, ejecuta `integrity_check` y `foreign_key_check`,
devuelve JSON y usa codigo de salida distinto de cero ante problemas.

## Interfaz de escritorio

> **Histórico.** Esta sección describe la **UI clásica** (`ui.py` con pestañas
> como «Calidad de datos», «Revisar duplicados», «Editar datos» o «Seguimiento»),
> retirada el 2026-11-11. La única interfaz vigente es la **UI v2**
> ([`src/jobpulse_v15/ui_v2/README.md`](src/jobpulse_v15/ui_v2/README.md)), con
> seis pestañas: Datos crudos, Perfil, Vacantes, Scraping, Cuentas y
> Configuración. Los controles citados abajo (estados manuales, filtros de
> revisión y edición de fuente) **ya no existen** en la interfaz.

La interfaz Tkinter muestra las vacantes guardadas, permite filtrarlas por
texto, ubicacion, modalidad e idioma, y revisar la evidencia del analisis.
El boton `Calidad de datos` muestra un resumen global de vacantes que requieren
revision, faltantes de empresa/pais/ubicacion, estado de analisis y campos
desconocidos o ambiguos, ademas de grupos candidatos a duplicados. El conteo
cubre toda la base, no solo la pagina visible de resultados. `Revisar
duplicados` muestra los primeros grupos candidatos e identificadores para
validacion manual.
Tambien permite ejecutar el extractor local sobre la vacante seleccionada o,
con `Analizar pendientes`, procesar tras confirmacion las vacantes visibles que
aun no tienen analisis. El procesamiento es local, no vuelve a analizar
registros ya analizados y muestra los errores por vacante. Permite abrir el
enlace de origen y registrar el estado manual de la vacante
(`reviewed`, `applied`, `archived` o `dismissed`), guardar notas y excluir
vacantes de la busqueda normal; se pueden volver a mostrar con el filtro
correspondiente. Esta informacion manual se conserva al actualizar la oferta.
La lista puede ordenarse por actividad reciente o por fecha de publicacion;
en este ultimo caso las ofertas sin fecha aparecen al final.
Los campos `Publicada desde` y `Publicada hasta` filtran por fechas inclusivas
en formato `AAAA-MM-DD`; se pueden dejar vacios para no limitar el rango.
Los campos `Tipo de empleo` y `Horario` aceptan texto tal como aparece en los
datos guardados (por ejemplo, `Full-time` o `Night shift`) y filtran por
coincidencia exacta; dejarlos vacios no aplica esos filtros.
El rango salarial compara ofertas solo con la misma moneda y periodo. Para
usar `Salario desde` o `Salario hasta` se requieren ambos valores de unidad;
una oferta coincide cuando su rango conocido se superpone con el solicitado.
Un extremo salarial ausente se interpreta como abierto, pero se exige al menos
un extremo conocido. No se convierten monedas ni periodos. `Moneda` y `Periodo
salarial` tambien se pueden usar por separado para filtrar por coincidencia
exacta.
`Exportar CSV` guarda los resultados de la ultima busqueda con sus filtros
actuales, incluidos los codigos de motivos de revision. Exporta los campos
normalizados basicos, fechas, campos salariales estructurados cuando estan
disponibles, compatibilidad del perfil y un enlace a una fuente; no incluye
descripcion, requisitos originales ni payloads de la fuente.
Neutraliza celdas cuyo contenido podria interpretarse como formula al abrirlo
en una hoja de calculo. Se limita a los resultados cargados (segun `Max.
resultados`) y visibles despues del filtro de compatibilidad.
`Editar datos` permite corregir titulo, empresa, pais, provincia/region, ciudad
y modalidad normalizados. Las correcciones prevalecen sobre futuras
actualizaciones de la fuente; `Restaurar datos de fuente` las elimina y recupera
los valores fuente mas recientes. El campo `location_raw` y el payload original
no se editan. Los cambios se guardan en la base v1.5 y no alteran la aplicacion
ni la base legacy.
El boton `Seguimiento` abre el historial opcional de postulacion: permite
anotar cambios de estado, fecha de aplicacion, proxima accion y notas. Cada
registro es un evento separado y sobrevive a la purga del contenido de la
vacante.
El boton `Mi perfil` permite registrar manualmente datos estructurados tomados
del CV o importar un PDF, DOCX o TXT local; `Comparar perfil` contrasta los
datos aprobados con los requisitos explicitos del analisis vigente. La
importacion prueba primero reglas locales y, si sugieren pocos datos, ofrece un
pase IA opcional (`cv_ia.py`, motor del `.env`: local o externo, con aviso de
privacidad si es externo); todo pasa por revision antes de guardarse.
La importacion solo lee el archivo seleccionado, trabaja localmente y no
conserva el texto extraido. Muestra sugerencias y fragmentos detectados para
revision; solo las filas seleccionadas se guardan. Reemplazar un dato existente
requiere confirmacion.

**Limites de importacion del CV:** PDF hasta **15 MB y 100 paginas**; DOCX y
TXT hasta **15 MB**; TXT codificado en UTF-8. No se ejecuta OCR en PDF
escaneados y los documentos protegidos con contrasena no se admiten.

Los datos muestran su origen (manual o archivo importado). `Revertir ultima
importacion` deshace la importacion mas reciente: elimina datos nuevos y
restaura valores previos que fueron reemplazados. Si un dato importado se
edito manualmente despues, ese cambio manual se conserva. El historial guarda
solo el nombre del archivo y fecha, nunca la ruta ni el contenido del CV.
La comparacion usa categoria y codigo exactos (o texto exacto si el requisito
no trae codigo), valida el nivel cuando ambos datos lo especifican, el estado
de estudios concluidos y el minimo numerico de experiencia. Los requisitos
inferidos o ambiguos requieren revision. Un dato
ausente del perfil se muestra como `No registrado`; no significa que la persona
no tenga esa competencia ni descarta automaticamente la vacante. Los codigos
del perfil deben coincidir con los del requisito (por ejemplo `en`, `bachelor`,
`years_experience`, `python` o `sql`). El extractor local identifica idioma,
educacion, licencia, experiencia y un conjunto inicial de competencias
tecnicas comunes (Python, SQL, Excel, Power BI, Tableau, AWS, Azure, Google
Cloud, Java, JavaScript, TypeScript, C++, C#, Linux, Git, AutoCAD, SolidWorks,
MATLAB, SAP, PLC y Six Sigma) solo cuando aparecen en contexto de habilidades,
herramientas, experiencia o con una señal explicita de requisito/preferencia.
La importacion de CV reutiliza esas reglas como sugerencias, no como afirmaciones
verificadas: revisa y, si es necesario, corrige categoria, codigo y dato usando
`Editar sugerencia`; el fragmento original se mantiene como referencia antes de
guardar.
Las competencias fuera de ese vocabulario se marcan como `unknown` si el texto
indica una seccion/contexto de habilidades, y requieren revision manual; una
mencion casual por si sola no se trata como requisito. La tabla de resultados
muestra el estado del perfil y el filtro
`Compatibilidad` permite ver coincidencias de requisitos obligatorios, datos
no registrados, brechas conocidas, revision manual, vacantes sin analisis o
sin requisitos obligatorios. Un analisis parcial se clasifica para revision,
no como incompatibilidad. El filtro se aplica a los resultados cargados hasta
el maximo indicado; aumenta `Max. resultados` para revisar un conjunto mayor.
La nueva version del extractor no reanaliza historicos automaticamente; usa
`Analizar seleccionada` para actualizar el analisis de una vacante ya guardada.
La interfaz solo consulta la DB v1.5 y no inicia scraping automaticamente.
La administracion de fuentes permite activar o
pausar sitios, agregar tableros Workday, Greenhouse, Ashby, Lever, Recruitee,
Workable y SuccessFactors, y consultar manualmente un tablero tras
confirmacion. Las ultimas corridas se consultan con
`run list --limit N` y el detalle de una corrida (sitios, conteos y errores)
con `run show --id <RUN_ID>`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 run list --limit 10
.\.venv\Scripts\python.exe -m jobpulse_v15 run show --id <RUN_ID>
```

La UI v2 (`jobpulse_v15.ui_v2`) es la unica interfaz grafica; tambien se abre
con `jobpulse-v15-v2.bat`.

## Ingesta controlada de ofertas

> **Contrato común de todos los proveedores.** Cada fetcher (API pública, RSS o
> navegador) solo obtiene ofertas crudas: el registro, la validación y la
> escritura pasan siempre por `IngestionService`, que abre la corrida del sitio,
> guarda `job_source_records` y `source_job_memory`, es idempotente por
> `(site_id, source_job_id)` y actualiza la salud en `source_run_sites`. Desde
> ahí el pipeline es el mismo para todas las fuentes: `scrape → análisis → IA →
> re-análisis → backfill → Paso 5`. Ningún adaptador escribe en la base de
> versiones anteriores ni abre un navegador por su cuenta.

El comando `ingest import-json` importa resultados ya obtenidos desde un
archivo JSON local, sin hacer solicitudes web. Cada importacion crea una
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

La importacion es idempotente por `(site_id, source_job_id)`: una oferta ya
conocida actualiza sus datos, pero se cuenta como duplicada en la corrida.
Una lista invalida se rechaza antes de crearla; si falla la escritura durante
la corrida, el error queda registrado para revision y la CLI informa el fallo.

### Consulta explicita de tableros Workday

v1.5 incluye un adaptador independiente para consultar tableros Workday. Usa
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

La consulta web solo ocurre al ejecutar `scrape workday`; no se inicia al
abrir la UI ni al importar el paquete. Se puede indicar un sitio (`--site`)
o un grupo (`--group`), nunca ambos. El grupo procesa en secuencia sus sitios
Workday habilitados; cada sitio mantiene su propia corrida y un fallo se
registra sin impedir los siguientes. El resultado JSON separa importaciones y
fallos, y la CLI retorna codigo distinto de cero si hubo fallos. El comando
admite de 1 a 10 paginas
(20 anuncios por pagina), utiliza `Costa Rica` como busqueda por defecto,
consulta detalles con una pausa entre vacantes y registra resultados/error
en una corrida del sitio. Un fallo HTTP o una respuesta inesperada se informa
como error y no se registra como cero ofertas. No hay reintentos automaticos.
Los registros se normalizan y pasan por `IngestionService`; el proveedor no
accede a la DB antigua. En la ventana `Administrar fuentes`, selecciona uno o
varios tableros activos y usa `Consultar seleccionadas` para ejecutar la misma
consulta secuencial con confirmacion y resumen de resultados/errores.

### Consulta explicita de tableros Greenhouse

Greenhouse expone un API publico por tablero. Registra la plataforma y un
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

La consulta es siempre explicita. Cada tablero usa una peticion al endpoint
publico de Greenhouse con descripciones; solo se importan vacantes cuya
ubicacion o alguna oficina contiene el texto `country_query` (por defecto
`Costa Rica`). La URL del tablero se valida contra los dominios oficiales antes
de construir la URL fija de API. Cada fuente tiene su propia corrida; un fallo
se registra y no detiene las demas. La UI v2 permite agregar tableros Greenhouse
y consultarlos individualmente o en seleccion multiple, siempre tras confirmar.

### Consulta explicita de tableros Ashby

Ashby ofrece una API publica por tablero. Registra la plataforma y el tablero
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

El adaptador consulta el endpoint publico del tablero solo bajo demanda,
conserva el payload original y filtra por `country_query` (por defecto
`Costa Rica`) en el titulo, ubicacion principal o ubicaciones secundarias.
Cuando una oferta coincidente solo indica el pais en una ubicacion secundaria
o en el titulo, guarda `<country_query> (multi-loc)` como ubicacion sin inferir
ciudad o provincia. La modalidad se mapea solo si Ashby especifica modalidad
remota, hibrida o presencial; de lo contrario queda `unknown`. La UI v2 permite
agregar tableros Ashby y consultarlos individualmente o en seleccion multiple,
siempre tras confirmar. Las pruebas usan respuestas simuladas y no consultan
tableros reales.

### Consulta explicita de tableros Lever

Lever expone un API publico por tablero. Registra la plataforma y el tablero
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

El adaptador consulta primero el endpoint europeo de Lever y, si falla,
reintenta con el global. Conserva el payload original, filtra por
`country_query` (por defecto `Costa Rica`) en el titulo, pais o listas del
anuncio y completa la descripcion con las secciones adicionales del anuncio.
Cuando una oferta coincidente no indica el pais en su ubicacion principal,
guarda `<country_query> (multi-loc)` sin inferir ciudad o provincia; la
modalidad no se deduce y queda `unknown` porque Lever no la expone. La UI
permite agregar tableros Lever y consultarlos individualmente o en seleccion
multiple, siempre tras confirmar. Las pruebas usan respuestas simuladas y no
consultan tableros reales.

### Consulta explicita de tableros Recruitee

Recruitee expone un API publico por tablero. Registra la plataforma y el
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

El adaptador consulta `https://<token>.recruitee.com/api/offers/` solo bajo
demanda, conserva el payload original y filtra por `country_query` (por
defecto `Costa Rica`) en el titulo, la ubicacion principal o las ubicaciones
secundarias. Completa la descripcion con la seccion de requisitos del anuncio.
Cuando una oferta coincidente no indica el pais en su ubicacion principal,
guarda `<country_query> (multi-loc)` sin inferir ciudad o provincia; la
modalidad no se deduce y queda `unknown`. La UI v2 permite agregar tableros
Recruitee y consultarlos individualmente o en seleccion multiple, siempre tras
confirmar. Las pruebas usan respuestas simuladas y no consultan tableros
reales.

### Consulta explicita de tableros Workable

Workable expone un API publico por cuenta. Registra la plataforma y el
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

El adaptador descarga la lista del tablero como **markdown**
(`https://apply.workable.com/<token>/jobs.md`) y despues la ficha de cada aviso
(`.../jobs/view/<id>.md`), con `urllib` y sin abrir navegador. Filtra por
`country_query` (por defecto `Costa Rica`) sobre el titulo y la ubicacion de la
tabla. Conserva la ubicacion tal como llega en `location_raw` y toma `country`
del sitio: **no infiere** ciudad ni provincia y no fabrica valores
`<country_query> (multi-loc)` (la normalizacion geografica la hace despues el
pipeline de ubicaciones). La modalidad se mapea desde la linea
`**Workplace:**` del detalle (`remote`, `hybrid`, `on-site`); si no aparece
queda `unknown`. Tambien extrae el tipo de empleo del encabezado, la fecha de
publicacion y el salario como texto (`salary_raw`), y guarda en
`description_raw` la descripcion con la seccion de requisitos. La UI v2 permite
agregar tableros Workable y consultarlos individualmente o en seleccion
multiple, siempre tras confirmar. Las pruebas usan respuestas simuladas y no
consultan tableros reales.

### Consulta explicita de portales SuccessFactors

Los portales SAP SuccessFactors "Career Section" exponen un feed RSS publico
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

El adaptador consulta `https://<portal>/services/rss/job/?locale=en_US&keywords=<country_query>`
solo bajo demanda. El filtro de la API no es estricto y puede traer vacantes
de paises vecinos, por lo que v1.5 valida `country_query` del lado cliente
sobre el titulo, el enlace decodificado o el pie de la descripcion (SAP suele
indicar ahi la ubicacion). La descripcion ya viene incluida en el RSS y no se
consulta detalle adicional. La fecha `pubDate` RFC 2822 se convierte a fecha
ISO. Los portales confirmados como compatibles son dominios por empresa como
`careers.kuehne-nagel.com`, `jobs.foundever.com` y `careers.ey.com`. La UI
permite agregar portales SuccessFactors y consultarlos individualmente o en
seleccion multiple, siempre tras confirmar. Las pruebas usan feeds simulados
y no consultan portales reales.

## Normalizacion de ubicaciones (Workday y catalogo CR)

Workday devuelve una ubicacion original que v1.5 siempre conserva en
`location_raw` y en el payload de origen. Para Costa Rica, el adaptador separa
ciudad y provincia cuando recibe `Ciudad, Provincia, Costa Rica`, o reconoce
una provincia cuando recibe `Provincia, Costa Rica`. Una ubicacion con una
estructura no reconocida permanece sin ciudad/provincia; no se adivina. La
modalidad no se deduce y queda `unknown` hasta que la fuente la especifique.
El adaptador usa solo la biblioteca estandar de Python y sus pruebas simulan
las respuestas; no hacen peticiones al portal.

Para normalizar registros Workday que ya estan guardados, se puede revisar
primero el reporte de simulacion. `--site` limita la operacion a un tablero y
`--apply` escribe los cambios, pero **no es solo aditivo**: rellena ciudad y
provincia vacias y ademas **corrige** las ciudades que `ciudad_es_basura`
delata como basura del parser viejo (no podrian ser un lugar); en ese caso el
reporte expone `corrected_cities` y no se respeta el valor existente:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 location normalize-workday `
  --site intel-cr
.\.venv\Scripts\python.exe -m jobpulse_v15 location normalize-workday `
  --site intel-cr --apply
```

Ademas existe `location normalize --platform <p> [--apply]`, que rellena y
corrige ciudad/provincia de **todas** las plataformas con el catalogo
geografico pais -> provincia -> canton -> distrito
(`src/jobpulse_v15/cli.py:3207-3286`). Tambien **muta** filas existentes:
cuenta `filled_city`, `filled_region`, `corrected_city` y `corrected_region`.

La operacion usa exclusivamente el payload original persistido y no hace
consultas web. Las ubicaciones no reconocidas y registros con fuentes
conflictivas se omiten y aparecen contados en el reporte. Respalda la base
antes de cualquier `--apply`.

## Ejecutar las pruebas

Desde `v1_5/` (pytest vive en el python del sistema; el venv no lo trae):

```powershell
python -m pytest tests/ -q
```

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

Los sitios deben apuntar a una plataforma registrada. La configuracion del
sitio es declarativa y se rechazan claves comunes de credenciales.
`select_sites` selecciona sitios activos, y el comando Workday puede recorrer
secuencialmente los tableros del grupo elegido.
`Repository.save_job` guarda la oferta, su registro de fuente y su memoria de
deduplicacion en una sola transaccion.

El registro de corridas distingue resultados vacios de errores. Tres
corridas exitosas seguidas con cero ofertas marcan el sitio para revision
manual, sin desactivarlo:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 run start --kind full --group directos
.\.venv\Scripts\python.exe -m jobpulse_v15 run site-result `
  --id 1 --site intel-cr --found 0 --valid 0 --new 0 --duplicates 0
.\.venv\Scripts\python.exe -m jobpulse_v15 run finish --id 1
.\.venv\Scripts\python.exe -m jobpulse_v15 run show --id 1
.\.venv\Scripts\python.exe -m jobpulse_v15 run list --limit 10
.\.venv\Scripts\python.exe -m jobpulse_v15 site mark-reviewed --id intel-cr
```

En la interfaz, una fuente que requiere revision habilita `Marcar revisada`.
La accion elimina la bandera de revision y conserva el ultimo estado observado
(`zero_results` o `error`); no activa la fuente ni ejecuta una consulta.

`jobs_found` cuenta ofertas recibidas del portal; si todas ya existian, se
registra un resultado exitoso con `--found` mayor que cero y `--new 0`, no
como un sitio sin resultados. Un error se registra con `--error "mensaje"`
y no incrementa la racha de ceros.

## Esquema: tablas del núcleo (manual heredado)

- `jobs`: identidad y campos comunes normalizados; conserva los textos
  originales cuando los proporciona la fuente.
- `source_platforms` y `source_sites`: plataformas, tableros y configuracion
  declarativa.
- `job_source_records` y `source_job_memory`: datos originales por fuente y
  memoria minima independiente de la retencion de la oferta.
- `source_runs` y `source_run_sites`: resultados y salud por corrida y sitio.
- `job_analysis`, `job_requirements` y `job_field_status`: extraccion
  versionada, requisitos con evidencia y estado de campos ausentes.
- `user_job_state` y `applications`: decisiones manuales y seguimiento que
  sobreviven a la purga del contenido de una oferta.

> Este listado es solo el **nucleo** del esquema, tal como lo.describe el manual
> heredado: **no** delimita el alcance actual del sistema. Las tablas que quedan
> fuera se reparten en dos inventarios: el **listado completo** por migración,
> en
> [`src/jobpulse_v15/migrations/README.md`](src/jobpulse_v15/migrations/README.md),
> y la **tabla de subsistemas** de arriba, que dice qué comando toca qué tabla
> (`job_match`, `job_area`, `concepto`, `pipeline_etapa`, `job_match_decision`,
> `postulacion*`).
> `user_job_state` y `applications` siguen en el esquema, pero la UI v2 ya no
> expone el flujo de estados manuales que describe el capitulo de interfaz.

Los requisitos son filas relacionadas y repetibles, no columnas especificas
por portal. `posting_language` describe el idioma del anuncio y no implica
que ese idioma sea requisito del puesto. Los estados `not_mentioned`,
`unknown`, `ambiguous` e `inferred` son distintos y no deben tratarse como
hechos equivalentes.

## Analisis estructurado y busqueda

`Repository.save_analysis` guarda una revision de analisis con requisitos
repetibles, evidencia, nivel (`required`, `preferred`, `inferred` o `ambiguous`),
origen, confianza y estados de campos (`found`, `not_mentioned`, `unknown` o
`ambiguous`). Cada revision se asocia a la huella del texto y version del
extractor; una nueva revision pasa a ser la actual sin borrar el historial.
Si se marca una categoria como `found`, debe incluir al menos un requisito con
evidencia. `complete` no puede ocultar campos ambiguos o desconocidos.

```python
repository.save_analysis(
    "job-123",
    text_hash="sha256-of-description",
    extractor_version="rules-2",
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
sola vez aunque coincida con varios requisitos. Por defecto la busqueda exige
requisitos `required`; se pueden incluir preferencias/inferencias pasando
`requirement_levels`. Los filtros y criterios se validan y parametrizan en SQL.
`get_current_analysis` permite recuperar el analisis vigente con sus estados y
evidencias. El esquema migra automaticamente a la version actual (28).

La busqueda tambien esta disponible desde la CLI; `--text` busca en titulo,
empresa, ubicacion, descripcion y `requirements_raw`, y se pueden repetir
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
como `required`. La busqueda de texto trata `%`, `_` y `!` como caracteres
literales, no como comodines SQL.
La salida JSON se mantiene por defecto. Para producir el mismo CSV controlado
que ofrece la UI v2 (incluidos compatibilidad, motivos de revision y enlace,
sin descripcion ni payload), usa `--format csv`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 search `
  --needs-review --format csv --sort-by date_published
```
El orden predeterminado `last_seen` conserva la actividad reciente de la fuente.
`--sort-by date_published` ordena por fecha de publicacion descendente y deja al
final las ofertas sin fecha conocida. `--published-from` y `--published-to`
aceptan fechas inclusivas en formato `AAAA-MM-DD`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 search `
  --published-from 2026-10-01 --published-to 2026-10-31
```
La revision de datos se consulta con `--needs-review` en la CLI (en la UI v2 no
hay casilla equivalente: la UI clásica tenía el botón «Calidad de datos»).
Muestra
vacantes sin empresa o pais, con ubicacion original pero sin ciudad/provincia
normalizada, sin analisis registrado, con analisis pendiente/parcial/con error
o con campos `unknown` o `ambiguous`. No se marca por si sola como error una
modalidad desconocida, un idioma no determinado o un campo `not_mentioned`:
estos estados pueden significar que la fuente no los proporciona o que las
reglas no encontraron una mencion. Esta vista prioriza la revision, pero no
modifica los datos ni convierte incertidumbre en un hecho.
Los resultados incluyen `review_reasons` en el JSON de busqueda, con codigos
estables como `missing_company`, `location_not_normalized`,
`analysis_partial` o `unknown_field:license`. Son la **forma actual y estable**
del resumen que la UI clásica mostraba como «Calidad de datos»: los calcula el
motor de busqueda (`repository.search_jobs`) y los expone el CLI. La UI clásica
mostraba el conteo en la columna `Datos` y detallaba los motivos al seleccionar
la vacante; la UI v2 no expone esa columna. Cuando no hay
motivos detectados se muestra `OK`; esto no garantiza que todos los datos sean
correctos, solo que las reglas actuales no detectaron faltantes.
El filtro `Motivo de revision` de la UI clásica limitaba los resultados a un
codigo; por
ejemplo, `missing_country`, `analysis_partial` o `unknown_field:license`.
La CLI acepta el mismo filtro con `--review-reason`:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 search `
  --review-reason location_not_normalized
```
La CLI tambien permite usar `--profile-compatibility` con los estados
`matched`, `not_registered`, `below_requirement`, `needs_review`,
`not_analyzed` o `no_required`. Por ejemplo:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 search `
  --profile-compatibility matched
```
Cuando se solicita este filtro, la salida JSON incluye la etiqueta
`profile_compatibility`; el CSV conserva la misma etiqueta y aplica el filtro
antes de exportar. La comparacion usa solo datos guardados y aprobados del
perfil; no significa que un requisito no registrado sea una carencia real.
Las vacantes con `skip_automatic = 1` se excluyen por defecto de la busqueda;
usa `--include-manually-skipped` para volver a incluirlas. Ese estado lo fijaba
la UI clásica (botón «Excluir de la búsqueda»); la UI v2 no lo expone, de modo
que en la práctica solo se activa por SQL o por una edición puntual de la base. Este filtro de
busqueda no elimina los anuncios del listado resumido solicitado a Workday;
cuando el ID de origen es reconocible, el adaptador evita descargar su detalle
y cuenta el anuncio como omitido, no como cero resultados. Si no se puede
reconocer un ID estable en el listado, Workday puede requerir descargar el
detalle para identificarlo.

## Extractor de requisitos

La version vigente del analisis por reglas es `rules-2` (`analysis.py`); el
analisis que integra ademas los campos estructurados de la fuente se registra
como `rules-2+fuente` (`analysis_flow.py`). Reconoce frases explicitas en ingles
y espanol para idiomas, estudios universitarios/secundarios, licencia de
conducir **con su clase** (`B1`, `D3`...) y años de experiencia, y extrae
competencias tecnicas con un vocabulario cerrado (Python, SQL, Excel, Power BI,
AWS, Java, Linux, SAP...). No usa red ni IA. Los hallazgos guardan como
evidencia la frase que activó la regla; los indicadores de preferencia y
obligatoriedad se clasifican por separado. Cuando el texto alude a un requisito
que las reglas no pueden interpretar, el campo queda `unknown`, no se presenta
como ausente.
Un campo `not_mentioned` significa que no se detectaron menciones de esa
categoria en las reglas actuales, por lo que los resultados deben revisarse
antes de utilizarlos para excluir candidatos u ofertas.

Para extraer y persistir el analisis de una oferta ya guardada:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 analysis extract --job job-123
```

El comando analiza `description_raw` y `requirements_raw`, registra la huella
del texto y la configuracion de la fuente, y conserva las revisiones anteriores.
`get_current_analysis` permite revisar los requisitos y la evidencia devueltos.
Para procesar en lote solo vacantes que no tengan analisis vigente, usa:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 analysis extract-pending `
  --limit 25 --dry-run
.\.venv\Scripts\python.exe -m jobpulse_v15 analysis extract-pending `
  --limit 25
```
El limite permitido es de 1 a 500 (predeterminado 25). El modo normal es local y
no consulta sitios web; no reanaliza vacantes que ya tienen analisis, devuelve
resumen y errores
por vacante, y retorna codigo de salida distinto de cero si algun registro
fallo. Las vacantes sin texto quedan reportadas como error. Para incluir
vacantes excluidas manualmente de las busquedas normales, agrega
`--include-manually-skipped`.
El informe global de calidad tambien esta disponible como JSON:

```powershell
.\.venv\Scripts\python.exe -m jobpulse_v15 quality report
.\.venv\Scripts\python.exe -m jobpulse_v15 quality duplicates --limit 100
```

La deteccion de posibles duplicados agrupa por titulo, empresa, pais y ciudad
normalizados (sin distinguir mayusculas, acentos ni puntuacion). Solo incluye
registros con esos cuatro campos disponibles. Son candidatos para revision
manual, no confirmaciones: el sistema nunca fusiona ni elimina vacantes
automaticamente. La salida lista los identificadores de cada grupo.
Los totales incluyen todas las vacantes de la base y no estan limitados por
los filtros de busqueda ni por el maximo de resultados de la UI.

No se guardan credenciales en la configuracion de sitios. El JSON de
configuracion es declarativo y no se ejecuta como codigo.
