# AGENTS.md — JobPulse CR v1.5

Orientación para agentes IA en este repo (`giovar24/jobpulse-cr-v15`; hasta el
2026-10-26 fue `v1_5/` dentro del repo `jobpulse_cr`). Solo lo **verificable y
caro de descubrir**; lo puntual vive en los handoffs.

## Al iniciar sesión

1. Lee el **handoff más reciente**: `docs/HANDOFF_SESION_*.md` (estado exacto,
   tabla de objetivos O1–O14 + Ola 6, pendiente inmediato). Arquitectura:
   `DESARROLLO_v15.md` (comparación histórica; sus conteos de tests/esquema
   están viejos — manda el handoff).
2. Repo **propio e independiente**: el v1.x en `D:\Proyectos\jobpulse_cr` está
   **congelado** (solo lectura) y sus comandos (`main.py`, `unittest`,
   `tools/auditar.py`) NO aplican aquí. La rama `fork-v15` del repo viejo
   conserva una password de ANE: jamás la pushees.
3. **No pushear sin confirmación del usuario.**
4. Al cerrar sesión ("vamos a otra sesión"): escribir
   `docs/HANDOFF_SESION_YYYY-MM-DD[_turno].md` (TL;DR, lo hecho, decisiones,
   tabla de objetivos, cómo retomar, archivos clave, contexto, pendiente
   inmediato) y **commitear**.

### Mapa de docs

| Documento | Qué es |
|---|---|
| `docs/HANDOFF_SESION_*.md` | Bitácora por sesión (empieza por el más nuevo) |
| `docs/SITIOS_PROBLEMATICOS.md` | ANE / Indeed / LinkedIn / Elempleo: login-wall, CDP |
| `docs/IA_ENRIQUECIMIENTO.md` | Pase IA: modelo local, caché, depuración |
| `docs/MOTOR_VIABILIDAD.md` | Viabilidad = **ajuste técnico**, no probabilidad |
| `docs/UI_V2_ARQUITECTURA.md` | UI v2 (capas, pestañas, patrones Tk) |
| `docs/FLUJO_CLI_VS_UI.md` | Qué comparten CLI y UI y qué hace cada uno |
| `docs/PASO5_EVIDENCIA_*.md` | Evidencia literal del matching (GENERADO, no editar) |
| `docs/PASO5_REVISION_PENDIENTES.md` | Hoja de firma de `educacion_no_confirmada` |
| `docs/REGLAS_NEGOCIO_EDUCACION.md` | Regla de negocio del nivel educativo + **todas las fuentes** |
| `docs/PASO5_FIRMA_EDUCACION.json` | Hoja de firma **aplicada** (29 decisiones, Paso 7) |
| `docs/PLAN_MEJORAS.md` | Backlog por olas (§5 hechos, §6 Ola 6 diferida) |

## Estructura (dónde está cada cosa)

- Paquete `src/jobpulse_v15/` (instalado con `pip install -e .`). Entrypoints en
  `pyproject.toml`: `jobpulse-v15` → `cli:main`, `jobpulse-v15-ui` → `ui:main`.
  La UI v2 se lanza con `python -m jobpulse_v15.ui_v2` o
  `jobpulse-v15-v2.bat` (no tiene entrypoint en `pyproject.toml`).
- Núcleo: `pipeline.py` (orquestador), `matching.py` (Paso 5), `repository.py`
  (persistencia), `db.py` + `migrations/` (esquema), `analysis_flow.py`
  (análisis por reglas, implementación única).
- Scripts de raíz = operaciones manuales del pipeline: `run_full_flow.py`,
  `run_enriquecimiento.py`, `run_paso5.py`, `generar_evidencia_paso5.py`,
  `verificar_evidencia.py`, `clean_run.py`.
- `tools/` = estado y medición (`corrida_medicion.py` **escribe** en la BD; los
  `estado_*`/`comparar_*` son de lectura). `tests/` usa BD temporales, sin red
  ni credenciales.
- Dependencias solo en `pyproject.toml` (no hay `requirements.txt`); extras
  `[dev]` (pytest) y `[ia]` (openai, huggingface_hub).

## Dos Pythons (regla que más se rompe)

- **App/CLI/scripts** → venv: `.\.venv\Scripts\python.exe -X utf8 …`
- **Tests** → python del **sistema**: `python -m pytest tests/ -q`
  (pytest **no** está en el venv; suite completa ~13–28 min; baseline verificado
  2026-11-10: **1251 passed + 2650 subtests** — 1636,67 s). Un archivo o un test:
  `python -m pytest tests/test_matching.py -q` /
  `python -m pytest tests/ -k <patrón> -q`.
- **No hay CI, linter, formatter ni typecheck configurados**: la verificación
  es la suite de pytest. Muchos tests crean una **BD temporal y aplican las 28
  migraciones** en `setUp` → la suite tarda minutos, no segundos; no la cortes
  pensando que se colgó.
- **`-X utf8` en todo comando que imprima datos de la BD**: sin él, un `\uf0b7`
  o un `\x85` en una descripción rompe la salida (los saves sí se completan).
  Para CSV por consola: `[Console]::OutputEncoding = UTF8` antes.
- El venv **no** se recrea al mover el repo: `activate`/`pip.exe` apuntan a la
  ruta vieja → usa siempre `python.exe -m pip`.
- Tras tocar `pyproject.toml`: `.\.venv\Scripts\python.exe -m pip install -e .`
  (los launchers no reinstalan deps).

## La base de datos

- `data/jobpulse_v15.db` = **corpus real del usuario**. Antes de cualquier
  operación destructiva: `… -m jobpulse_v15 backup --output data\backups\X.db`
  (usa la API de copia de SQLite, valida `integrity_check`, no sobrescribe).
- La BD **no está en git** (`data/*.db` ignorado): en un clon nuevo no hay
  corpus; `init-db` crea una base vacía, `init-sources` (o `site seed-cr`)
  registra plataformas/sitios de CR y los scrapers la llenan.
- **El CLI migra el esquema al abrir la BD** (avisa `[esquema] Se aplicaron las
  migraciones N-M`). `init-db`, `backup` y `db check` **no** migran.
- Esquema por migraciones: `src/jobpulse_v15/migrations/0NN_*.sql`. Cambio de
  esquema = **archivo nuevo**; nunca `ALTER` manual ni editar una migración ya
  aplicada. Versionado con `PRAGMA user_version` (actual: **28**).
  Al añadir una migración hay que actualizar las aserciones de versión
  hardcodeadas en `tests/test_migraciones.py` y `tests/test_pipeline_metricas.py`
  (busca `28`), o la suite falla.
- Si una migración tiene que **recrear una tabla** (cambiar un `CHECK`), SQLite
  no lo permite con `ALTER` y `PRAGMA foreign_keys` no se puede cambiar dentro
  de una transacción: la migración gestiona su propia transacción y lo marca
  con el comentario `-- jobpulse:transaccion-propia` (ver `db.py` y la 022).
- `clean_run.py SI` = borrado total de lo scrapeado (jobs, análisis, runs,
  `job_match`); conserva perfil, sitios, taxonomías y reinicia la salud de los
  sitios. **Destructivo**: solo con pedido explícito del usuario.
- `… -m jobpulse_v15 db check` = integridad + FK (exit≠0 si falla).
- **`auditoria_db.py` quedó apuntando a la ruta vieja**
  (`D:\Proyectos\jobpulse_cr\v1_5\data\...`, repo congelado): no lo uses. Para
  el estado usa `tools/estado_bd.py` (o `db check`).

## Pipeline completo (el orden NO es negociable)

```powershell
$py = ".\.venv\Scripts\python.exe"
# 1. Scrape (solo con red; los tableros API no necesitan browser)
& $py -X utf8 run_full_flow.py --only-scrape --pages 1     # o: -m jobpulse_v15 scrape <plataforma> --site <id>
# 2. Análisis por reglas (idempotente: solo lo que falta)
& $py -X utf8 -m jobpulse_v15 analysis extract-pending --limit 500
# 3. ENRIQUECIMIENTO IA  ← rellena jobs.skills / jobs.languages
& $py -X utf8 run_enriquecimiento.py          # con IA externa: --confirmar-externo
# 4. Re-análisis integrando los CAMPOS ESTRUCTURADOS del aviso
& $py -X utf8 -m jobpulse_v15 enrich requirements-source --apply
# 5. Backfill del código canónico de los requisitos ya guardados
& $py -X utf8 -m jobpulse_v15 enrich requirements-canonico --apply
# 6. Matching: CORRIDA NUEVA (nunca UPDATE de la anterior)
#    OJO: por defecto solo evalúa las áreas marcadas en el perfil;
#    --evaluar-todo ignora ese filtro. --dry no escribe.
& $py -X utf8 run_paso5.py [--dry] [--evaluar-todo]
# 7. Evidencia (exit 0 = TODO CUADRA) + hoja de firma
& $py -X utf8 generar_evidencia_paso5.py
& $py -X utf8 verificar_evidencia.py
& $py -X utf8 generar_revision_pendientes.py
```

**Por qué el orden**: los scrapers **no** rellenan `jobs.skills`/`jobs.languages`;
los produce el pase **IA** (paso 3). Sin el paso 3, el paso 4 no integra nada y
la taxonomía queda sin cubrir. `analysis_flow.extract_job_analysis` es la
**implementación única** del análisis (la usan CLI, UI clásica, UI v2 y
`run_full_flow`): no dupliques la lógica.

### Orquestador único (O12 · Ola 2)

`src/jobpulse_v15/pipeline.py` encadena las etapas con **una sola
implementación** cada una (`scrape` → `analisis` → `ia` → `reanalisis` →
`backfill` → `paso5` → `evidencia`). Lo usan:

- la CLI: `run_full_flow.py` (ya es un envoltorio del orquestador);
- la UI v2: botones **"Procesar"** y **"Enriquecer IA"** (pestaña "Scraping");
- la UI clásica: **desde 2026-11-08 (punto 5 del backlog, con permiso
  explícito del usuario) también delega**: su flujo completo llama a
  `pipeline.ejecutar` con `("analisis","ia","reanalisis","backfill","paso5",
  "evidencia")` y la ventana "Enriquecer IA" con `("ia","reanalisis")`. Ya no
  tiene pase de IA ni re-análisis propios (se borró
  `_reananalizar_con_campos_fuente`). Su **comparación con el perfil** (paso 4)
  sigue siendo propia e informativa (`compare_jobs_to_candidate_profile`): el
  veredicto auditable es el del Paso 5.

```python
from jobpulse_v15 import pipeline
resultado = pipeline.ejecutar(repository, etapas=("analisis", "reanalisis", "paso5"))
print(pipeline.resumen_linea(resultado))
```

Reglas: una etapa desconocida es `ValueError`; el Paso 5 es siempre **corrida
nueva**; la etapa `ia` con proveedor externo **no** arranca nada local y la
confirmación de privacidad la hace el caller (UI) antes de invocar.
`pipeline.ejecutar(repository)` **sin `etapas`** usa
`("analisis","ia","reanalisis","paso5","evidencia")`: **no scrapea ni hace
backfill**; pásalos explícitos si los necesitas (`scrape` exige `sites=`).

### Métricas por etapa (Ola 4.3)

`pipeline.ejecutar` cronometra **cada** etapa y deja una fila en
`pipeline_etapa` (migración 024): `corrida_id` (`pipe_<timestamp>`, **distinto**
del `corrida_id` de `job_match`), `etapa`, `ok`, `duracion_ms`, `avisos`,
`requisitos`, `errores`, `detalle_json`, `iniciado_en`, `terminado_en`.

- La instrumentación vive **solo** en `pipeline.py` (punto único) + el módulo
  `pipeline_metricas.py` (traduce cada etapa a los contadores comparables
  `avisos`/`requisitos`/`errores`).
- Es **puramente aditiva**: si falla, la corrida sigue (una métrica nunca
  rompe un pipeline). No toca `job_match`, `job_analysis` ni los umbrales.
- Consulta: `… -m jobpulse_v15 pipeline etapas [--limite N] [--corrida ID]
  [--json]`.

### Comprobar que el scrape llegó bien

| Comprobación | Dónde | Señal de problema |
|---|---|---|
| La vacante existe | `jobs` + `job_source_records` + `source_job_memory` | `jobs_new>0` pero no aparece |
| Tiene área | `job_area` (se clasifica **al guardar**) | sin fila → clasificación rota |
| Tiene análisis | `job_analysis` (`is_current=1`) + `job_requirements` | sigue en `extract-pending` |
| El matching la ve | `job_match` de la corrida vigente: `total_req>0` | `total_req=0` → requisitos **sin `codigo_canonico`** |
| El estado cuadra | `GROUP BY estado` = nº de jobs | no cuadra → corrida a medias |
| BD sana | `db check` | `integrity_check != ok` o FK violadas |

Un requisito sin concepto queda `codigo_canonico = NULL` **a propósito** y se
encola en `concepto_no_normalizado`: esa vacante se evalúa con menos
requisitos de los que tiene. Mira la cola para decidir si es bug o taxonomía
incompleta.

## Scraping y sitios

- **Los subcomandos `scrape <plataforma>` NO abren Brave**: los scrapers de
  navegador (ANE, Indeed, LinkedIn, Elempleo) reciben el `port` CDP del caller
  y el fetcher **nunca** crea un navegador. Antes de `scrape ane|linkedin|indeed`
  levanta CDP:
  `python -c "from jobpulse_v15.browser_manager import asegurar_brave; asegurar_brave(9222)"`.
  **En cambio** `scraper.ejecutar_barrido` (la etapa `scrape` del pipeline, o
  sea `run_full_flow.py`, la UI v2 y `pipeline.ejecutar`) **sí abre Brave bajo
  demanda** y lo cierra **solo si esta corrida lo abrió** (O7.2).
- **`scrape cinde` y `scrape procomer` son API pública** (GraphQL/REST): no
  necesitan Brave ni CDP. Los tableros ATS (Workday, Greenhouse, Ashby, Lever,
  Recruitee, Workable, SuccessFactors) tampoco.
- **No hay subcomando `scrape elempleo` ni `scrape harvie`**: esos fetchers
  existen en `scraper.FETCHERS` pero solo corren vía `ejecutar_barrido` (sitio
  registrado con esa plataforma), no por CLI directa.
- Brave debe usar el **perfil real**: `--user-data-dir` = raíz `User Data`
  (NUNCA `User Data\Default`) + `--profile-directory={perfil}`. Si el Brave
  diario corre sin CDP, Chromium **delega** el puerto y nada abre: ciérralo
  del todo. Puerto configurable: `BRAVE_CDP_PORT` es la única fuente
  (`browser_manager.puerto_cdp_configurado()`).
- **ANE**: sesión obligatoria. Credencial: keyring de Windows → `data/empresas/
  credenciales.json` → `.env` (`ANE_USER`/`ANE_PASSWORD`); nunca en el repo.
  ANE republica vacantes con IDs nuevos → `quality duplicates`, dedupe manual,
  **nunca** automerge.
  **Trampa 1 (verificada 2026-11-05, RESUELTA en O12 · Ola 1.5)**: antes
  `login_ane.py` cerraba el Brave que abrió con `terminate()`/`kill()` → la
  cookie de sesión **no quedaba persistida** y el barrido siguiente decía
  "ANE: sin sesión de detalle" con 0 avisos. Ahora cierra **ordenado**
  (`Browser.close` por CDP) y `--mantener-abierto` deja el navegador vivo para
  raspar de inmediato. Flujo recomendado: `login_ane.py --mantener-abierto` y
  acto seguido `scrape ane --site ane-cr` (sin cerrar el navegador).
  **Trampa 2 (verificada 2026-11-06, RESUELTA en O13 · Ola 3.4)**: la cookie de
  ANE (`ASP.NET_SessionId`) es de **sesión** (`expires = -1`): Chromium **no**
  la escribe en disco, así que al reabrir Brave se pierde (el cierre ordenado
  NO la salva). `jobpulse_v15.sesion_navegador` la guarda aparte en
  `data/usuario/sesiones/ane.json` (fuera del repo: es un secret) tras el
  login y la restaura cuando falta la sesión. Si el servidor la caducó, el
  archivo se borra.
  **Trampa 3 (verificada 2026-11-06, Ola 4.1)**: el listado de ANE solo
  muestra las vacantas **recientes** → un aviso viejo guardado con un parser
  viejo **nunca** vuelve a pasar por el listado y su texto se queda para
  siempre con los campos que el parser no leía ("Nivel académico",
  "Experiencia laboral"). Para corregirlo: `scrape ane --site ane-cr
  --revisitar` (re-baja el detalle de los avisos YA guardados por su URL; lo
  que ya no exista en la web se **omite**, no se borra). El parser de la
  ficha vive en `AneFetcher._parse_detalle` y la oferta se construye en
  `AneFetcher._oferta` (**una sola implementación** para el barrido y el
  re-barrido: si construyeran el dict por separado, el texto guardado
  diferiría y el re-análisis no detectaría el cambio).
- **Re-análisis por texto nuevo (Ola 4.1)**: `job_analysis.text_hash` es el
  sha256 de descripción + requisitos. Si el scraper trae más texto, el hash
  ya no cuadra → el aviso está obsoleto →
  `analysis_flow.avisos_con_texto_cambiado` /
  `reananalizar_texto_cambiado` (enganchado en la etapa `reanalisis` de
  `pipeline.py`). **Si cambias un parser, re-barrida y re-analiza**: si no,
  el motor evalúa el texto viejo.
- **LinkedIn**: el listado público se pide por **HTTP simple**
  (`/jobs/search/?keywords=…&location=…` → `div.base-card` + JSON-LD
  `ItemList`); `/jobs/search-results/` responde **999** y el navegador sin
  sesión recibe authwall. El navegador (CDP) queda como refuerzo que fusiona
  resultados. **Rate-limit (medido 2026-11-05)**: `jobs-guest` aguanta ~10
  peticiones seguidas y luego da **429**; con **1,5 s** entre peticiones: 19 OK
  / 0 429 → `request_delay` = 1,5 s por defecto y ante 429 se espera y se
  reintenta (sin probar la URL alternativa). Sesión: login **manual**
  (el auto-login dispara CAPTCHA/2FA).
- **Indeed**: SSO Google; el popup de alertas intercepta clics (ya resuelto en
  `_cerrar_popups`; si aparece uno nuevo, añadir su selector).
- **Selectores verificados en vivo (2026-11-05/06) —LinkedIn 60 avisos,
  Elempleo 3 avisos (antes 0 en ambos)**:
  - **LinkedIn**: `div.base-card` + `data-entity-urn="urn:li:jobPosting:<id>"`,
    `h3.base-search-card__title`, `h4.base-search-card__subtitle`,
    `span.job-search-card__location`, `time.job-search-card__listdate`,
    `a.base-card__full-link`.
  - **Elempleo**: las ofertas siguen en **`.result-item`** +
    `.js-area-bind.area-bind` (`.ee_list-item` es el MENÚ LATERAL, no el
    listado); la empresa está en `.js-offer-company` (ya no en
    `datalayertag`); el filtro de país mira **país + cantón** (la ubicación es
    el cantón: "San José"); el botón "Inicia sesión" del encabezado **NO** es
    un muro de login (solo lo es un formulario de acceso); descripción en
    `.description-block` y requisitos en las etiquetas
    `.requirements-content li .info-tag-not-select`.
    `site_config["max_ofertas"]` acota el barrido (cada oferta abre su ficha).
  Al tocar un scraper: actualizar también su test en `tests/test_<nombre>.py`.
- **Salud de sitios**: 3 corridas seguidas con 0 avisos → `review_required=1`
  (NO se desactiva solo). `site list --needs-review` y
  `site mark-reviewed --id <id>` (reinicia el racho). `clean_run.py` también
  reinicia la salud (si se borran las corridas, se borra su veredicto).
- **`requires_login` (O13 · Ola 3.3)**: un sitio que pide iniciar sesión NO
  está roto: salud `requiere_login` (esquema 22), corrida `requires_login`,
  **no** suma a la racha de ceros, sí queda `review_required=1` y la UI v2
  muestra 🔑. Lo lanza `jobpulse_v15.requiere_login.RequiereLoginError`.
- **Dedupe conservador**: duplicado EXACTO → `dup_of` automático; lo dudoso →
  `quality duplicates` para revisión manual. **Nunca se borra ni se funde.**
- Config declarativa en BD (`source_sites.site_config_json`), no en código.

## Matching / Paso 5 — reglas de negocio duras

Módulo: `src/jobpulse_v15/matching.py` (tests `tests/test_matching.py`).
Cada cambio de regla = **corrida NUEVA** en `job_match` (`corrida_id`, las
anteriores `valida=0`); nunca `UPDATE` in-place.

- **Umbrales congelados**: cobertura 0.60 / puntaje 0.80. No tocar sin acuerdo.
- **`preferred` NO bloquea** (no entra al denominador). Igual en el texto:
  "Preferred" no es requisito.
- **`codigo_canonico` es obligatorio** en requisitos Y en hechos del perfil: sin
  él el motor **lo ignora en silencio** (perfil invisible → todo `sin_requisitos`).
  Se resuelve **al guardar** (`conceptos.resolver`); el backfill solo rellena
  `NULL`.
- **Idioma del aviso**: el requisito de idioma es el idioma en que está escrito
  el aviso, salvo que el aviso **pida** idiomas (mandan los que pide).
  `mixed`/`undetermined` no generan requisito; el idioma del aviso solo cuenta
  si hay otros requisitos; perfil sin idiomas → `no_verificable` (nunca
  faltante). Implementación: `matching.requisitos_efectivos` + `idiomas.py`.
  `jobs.posting_language` de la fuente no se pisa (solo se rellena `undetermined`).
- **Educación**: `descartada` solo si el **texto** confirma título universitario
  obligatorio, sin negación ni alternativa; ante la duda → `revisar_a_mano`.
  **Nunca descartar por falta de información.** "bachiller" a secas = secundaria
  (CR); "bachillerato universitario"/"licenciatura" = universitario; "bachelor"
  sin "degree" cerca es el título del puesto, no un requisito; estudiante en
  curso = criterio aparte (`titulo_universitario_en_curso_requerido`).
- **`educacion_no_confirmada`**: solo la firma una **segunda persona** (el
  veredicto del autor de la regla se descarta por sesgo). La firma vive en la
  tabla **`job_match_decision`** (migración **027**, módulo canónico
  `decisiones.py`): `veredicto` ∈ `bloqueo_real` | `no_bloqueo` | `dudoso`,
  con `criterio`, `revisor`, `fecha` y **`text_hash`** (sha256 de
  `requirements_raw` + `description_raw`).
  - El motor aplica la firma **SOLO** cuando NO pudo decidir (`no_confirmado`):
    `bloqueo_real` → `bloqueante` (`descartada`), `no_bloqueo` → `faltante`
    (`revisar_a_mano / educacion_no_cumple`), `dudoso` → sin cambio (el caso
    sigue abierto). **Una firma NUNCA pisa un veredicto del motor.**
  - La firma está **anclada al texto**: si el aviso se re-raspa y su texto
    cambia, la firma deja de aplicar y el caso vuelve a
    `educacion_no_confirmada` (hay que volver a firmarlo).
  - CLI: `jobpulse-v15 decision list` / `decision sign --file <firma.json>`
    (`--dry-run` para comprobar sin escribir). La hoja firmada vive en
    `docs/PASO5_FIRMA_EDUCACION.json`.
  - Los estados solo cambian con una **corrida nueva** de Paso 5 (nunca
    `UPDATE` de la anterior). **NO** actualizar estados antes de la firma.
- **Regla de negocio del nivel educativo** (decidida y firmada 2026-11-08;
  reglas y **todas las fuentes** en `docs/REGLAS_NEGOCIO_EDUCACION.md`):
  - **Escalera** (de mayor a menor): posgrado > título universitario >
    estudiante sin graduar con **80 %+ de los créditos** > diploma técnico >
    bachillerato de secundaria.
  - **Referencia**: el sistema educativo de **EE. UU.** (U.S. Dept. of State /
    InfoUSA, *Structure of U.S. Education*) → "associate" = superior de ciclo
    corto, "bachelor" = universitario. Es la que usan los avisos y casi todo
    el mercado de CR (y las multinacionales). El CONESUP queda como **criterio
    de curación** del perfil (qué título cuenta como académico superior), sin
    fuente documental aportada.
  - **El estudiante avanzado NO es un titulado**: un aviso que exige título
    universitario no lo cumple quien está "en curso" (aunque tenga el 99 % de
    los créditos). Un aviso que acepta explícitamente el avance parcial ("X %
    of completeness of a bachelor's degree program") sí lo cumple ese escalón,
    y solo ese (un diploma técnico está por debajo).
  - **El motor no modela el campo del título**: si el nivel se cumple pero el
    campo no (p. ej. el aviso pide business/Finance y el perfil tiene un
    diplomado en Electrónica), lo cierra la **firma** de la segunda persona.
  - **El escalón "estudiante avanzado" YA EXISTE** (migración **028**,
    2026-11-10): la escalera es 1 secundaria < 2 ciclo corto < 3 estudiante
    avanzado < 4 universitario < 5 posgrado. Un hecho `pursuing` **no**
    confiere el título que estudia; su nivel efectivo lo dice la **tabla de
    EE. UU.** (§1.1 de `docs/REGLAS_NEGOCIO_EDUCACION.md`), no una resta:
    bachelor en curso → escalón 3 (**solo con el 80 %+ documentado**),
    associate en curso → escalón 1 (no confiere el associate), master en
    curso → escalón 4 (el bachelor es prerrequisito). Un aviso con "X % de
    completitud" declara el escalón 3, no el 4. **El 80 % es un umbral
    EXIGIDO** (§4.1): un `pursuing` solo alcanza el escalón 3 si documenta
    el avance (`matching.porcentaje_avance_fact` lee
    `qualifier`/`notes`/`value_text` o `numeric_value` + `unit='%'`), y un
    aviso que pida menos del 80 % queda en el escalón 2. Mediciones en
    copia: 0 cambios de estado en el Paso 5; el único aviso afectado es el
    caso abierto de Abbott (su requisito del 80 % pasa de `no_confirmado` a
    `faltante` y su banda se topa en `revisar`). Ver
    `docs/PLAN_MEJORAS.md` §6.2.
- **Viabilidad ≠ contratación**: `viabilidad.py` dice si el perfil **cumple lo
  que pide el aviso** (ajuste técnico 0-100 + banda). **Ser rechazado NO
  significa que el perfil no califique**: el reclutador decide por presupuesto,
  timing, competencia, sesgos y azar → los rechazos **nunca** son etiqueta de
  aptitud ni reentrenan pesos. Bandas: `aplicar ≥85`, `revisar 80-85`,
  `no_prioritario <80`, `sin_datos`, `veto`. Tope duro: ≥1 requisito
  `required` faltante ⇒ banda máxima `revisar`.
- El **ranking ATS** (score 0-100) es un ranking, no una calificación: no toca
  los umbrales del Paso 5.
- **Privacidad**: del correo/portal solo derivados mínimos (estado, fecha,
  remitente, asunto, referencia). **El cuerpo del mensaje nunca se guarda**.

## Gotchas de código (los que cuestan horas)

1. **Requirements sin `codigo_canonico` se ignoran en silencio** → la vacante
   cae en `sin_requisitos` sin avisar. Antes de culpar al motor: mira la cola
   `concepto_no_normalizado`.
2. **La cola de la taxonomía se filtra y se reconstruye** (Ola 4.2): solo
   entran variantes ENCOLABLES (`conceptos.es_variante_encolable`: ni
   actividad, ni palabra vacía, ni sector, ni frase de más de 3 palabras) y
   `jobpulse-v15 taxonomy curate --apply` la reconstruye desde
   `jobs.skills`/`jobs.languages` (`veces` = nº de **avisos** que la piden).
   Curar la taxonomía = **migración de datos** nueva (`02x_taxonomia_*`),
   nunca `UPDATE` a mano. **Para medir la demanda usa
   `taxonomia.demanda_corpus`**, no el `veces` de la cola (se reescribe en
   cada curación). Estado verificado 2026-11-09 (sin cambios desde el cierre
   del 2026-11-08): cola **1150** (tanda 3 = migración `026`), conceptos
   **775** (336 códigos), 2956 requisitos (0 sin código), 29 decisiones
   firmadas, corrida vigente `20261108_214123`.
3. **Nunca insertar requisitos por SQL directo**: `job_requirements` tiene
   `analysis_id` (FK a `job_analysis`), no `job_id`. Usa `Repository.save_analysis`.
4. `jobs.posting_language` es NOT NULL (tests: `undetermined`); `mixed` es
   válido. `concepto` no tiene `nombre`: es `codigo_canonico` + `variante`.
5. `jobs.requirements_raw` es NULL en casi todos los Workday: el texto real
   está en `description_raw` (~4–5k chars) → buscar en ambos.
6. **El score sin imputación es degenerado**: una vacante con 1 solo requisito
   cubierto saca 100. Viabilidad y ranking ATS hacen **dos pasadas** (pesos
   fijos + imputación del promedio del corpus).
7. `Database.connection()` es un context manager y `EvaluadorPaso5` carga los
   datos **al construirse** → conexión viva durante toda la evaluación y
   evaluador **nuevo** por evaluación. En Windows, cerrar la conexión **antes**
   de borrar el temporal (`PermissionError` si no).
8. **Caché IA en disco** (`data/usuario/ia_cache/`): falsea benchmarks →
   aísla con `JOBPULSE_IA_CACHE`. `failed` en el pase IA **no** es error de
   red (cuenta "no mencionado"); los errores reales avisan
   "IA extract {campo} fallo tras 3 intentos".
   **Avisos estancados (2026-11-08)**: el modelo es determinista a temp 0.1 →
   un aviso al que no le puede extraer el campo **no se reintenta** en el
   siguiente ciclo ni en el pase completo (`run_ia_enrichment(exclude_ids=…)`
   y `ids_estancados`). El consumo real (llamadas + tokens) queda en
   `pipeline_etapa.detalle_json` → clave `uso` (`jobpulse-v15 pipeline etapas
   --json`): `pase_completo` usa un único cliente y lo cierra al terminar.
9. **Caché de embeddings**: el temporal debe terminar en `.npy`
   (`embeddings_cache.npy.tmp.npy`) o `np.save` añade otra extensión y el
   `replace()` falla → se re-vectoriza todo el corpus en cada arranque.
10. `job_field_status` **no** tiene categoría `salary` (el estado del salario se
    mira en `jobs.salary_min`; la regla de "declara salario" vive en `salario.py`).
11. El **TÍTULO** de un aviso no es fuente de ubicación; el catálogo Workday
    devuelve el título entero como ciudad (no hacerlo).
12. Tk: fuentes con espacio van **entre llaves** (`{Segoe UI} 10`); nunca
    mezcles `pack` y `grid` en el mismo padre; un widget sin gestor queda
    invisible (1x1); el callback de `yscrollcommand` solo actualiza el
    scrollbar (tocar el canvas ahí = reentrada infinita).
13. En tests: `with patch(...) as m` deja `m` **sin definir** fuera del bloque
    → guarda el mock en otra variable. Los tests del cliente IA deben parchear
    `jobpulse_v15.ui_perfil.asegurar_servidor` (si no, arranca el llama-server
    real en plena suite → saturación de RAM).
14. `with ... as X` borra el nombre al salir del bloque (comportamiento de
    Python, no de Tk).
15. Retención: la política vive en `ui_config.json` y la comparten UI clásica y
    v2 (merge en `ui_v2/data/retencion.py`); la retención **oculta, nunca borra**.
16. La etapa `reanalisis` del pipeline rehace **dos** grupos: los avisos que
    **nunca** integraron `jobs.skills`/idiomas (`avisos_con_campos_sin_integrar`)
    y los que cambiaron de TEXTO (`avisos_con_texto_cambiado`). Tras cambiar
    la **taxonomía** (una migración `02x_taxonomia_*`), los avisos que ya la
    integraron tienen un análisis **obsoleto** (les faltan requisitos): hay que
    re-analizarlos TODOS con `enrich requirements-source --apply` antes del
    backfill y del Paso 5.
17. **Los tests NO deben depender del `.env` real**: `jobpulse_v15.cli` hace
    `load_dotenv()` **al importarse**, así que cualquier test que importe el
    CLI carga el `.env` del desarrollador en `os.environ` de toda la sesión de
    pytest (p. ej. `IA_BASE_URL=https://ollama.com/v1` → la tarjeta "IA local"
    de la UI v2 se pinta como "IA externa" y fallan 2 tests). Por eso
    `tests/test_ui_v2.py::TestConfiguracionTab` fija la IA local en `setUp`
    (y restaura al final). Regla: si un test depende del entorno, que lo
    **fije** en `setUp`; no confiar en el `.env` del usuario.

## IA: local o externa (Ollama, LM Studio, cloud gratis)

- Modelo local canónico: **Gemma 4 E2B QAT** (GGUF en `D:\Models\…`, llama.cpp
  en `D:\llama-…\llama-server.exe`, puerto 8081). Instalador idempotente:
  `.\instalar-modelo-ia.bat` (`--check` solo verifica).
- La IA **no se pre-arranca**: la UI y `run_enriquecimiento.py` la levantan bajo
  demanda y la apagan al terminar (solo el proceso que ellos abrieron).
- **La IA externa es una alternativa de primera clase** (mismo cliente
  OpenAI-compatible, mismo enriquecimiento, mismas tareas futuras):
  `IA_PROVEEDOR`/`IA_BASE_URL`/`IA_MODEL` viven en `.env` (nunca en el repo).
  Presets (`ia_api.PRESETS`, fuente única; las dos UIs los muestran):
  `ollama` = **Ollama Cloud** (`https://ollama.com/v1`, acceso gratis),
  `ollama-local` = Ollama en esta máquina (`http://localhost:11434/v1`),
  `lmstudio` = LM Studio (`http://localhost:1234/v1`), más `openrouter`,
  `nvidia`, `google` y `custom` (cualquier OpenAI-compatible).
- Con endpoint externo **no se arranca nada local** (`ia_servidor.asegurar_servidor`
  devuelve `None`) y el cliente degrada `json_schema` → `json_object` → sin
  `response_format` cuando el proveedor rechaza el modo estricto.
- **Privacidad**: con IA no local el TEXTO de los avisos sale de la máquina →
  aviso + confirmación obligatoria (UI v2) / `--confirmar-externo` — flag de
  `run_enriquecimiento.py`, **no** del CLI `jobpulse_v15`.
- Límites **opt-in y ajustables**: `IA_MAX_LLAMADAS`/`IA_RPM`/`IA_MAX_VACANTES`
  (avisos por corrida; vacío = **sin tope**, no hay valores fijos).
- **Elegir modelo en la UI v2**: el campo "Modelo:" es un **combobox editable**
  y el botón **"Listar modelos" lo RELLENA** (lista la del endpoint
  configurado; vale para todos los proveedores). `IA_MODEL=auto` coge el
  **primer** modelo de la lista → casi siempre `gpt-oss:120b`: usa el
  desplegable y escribe el modelo explícito.
- **Nube vs local (medido 2026-11-07/08, mismo corpus de 736 avisos)**:
  Ollama Cloud `gemma4:31b` = **8,2 min**, **6,7% del free usage**, 1335
  campos, 1948 reqs, 132 calificadas, **121 sin_requisitos**; local
  `gemma4-e2b-qat` = **81,3 min**, **$0**, **2288 campos**, 2879 reqs,
  **220 calificadas**, **11 sin_requisitos**. La local gana en datos, la nube
  en velocidad. La caché de IA separa por **proveedor+modelo**
  (`ia_api._cache_key`) → comparar es seguro.
- **Ollama Cloud NO da tokens gratis**: "pay as you go" es $0 de cuota pero se
  paga por token (créditos); Pro $20/mes = $60 de créditos, Max $100 = $300.
  Los tokens se miden en $ a la tasa del modelo (ollama.com/pricing).

## UI

- **UI clásica** (`ui.py`): completa — no la toques sin pedirlo. **Excepción
  ya autorizada (2026-11-08, punto 5 del backlog)**: delegar sus etapas al
  orquestador `pipeline.ejecutar` y eliminar implementaciones duplicadas.
- **UI v2** (`ui_v2/`, plana y modular): capas `theme`/`widgets`/`dialogs`/
  `i18n`/`configuracion` + `data/` (stores sin Tk) + `tabs/`.
  **Agregar una pestaña = módulo nuevo + 1 línea en `PESTANIAS`** (`ui_v2/app.py`).
  Humo sin ventana:
  `python -X utf8 -c "from jobpulse_v15.ui_v2.app import crear_app; r,s=crear_app(); [r.update() for _ in range(20)]; t=s.pestana_activa(); t.refresh(); print(t.key, len(t._widgets['tabla'].get_children())); r.destroy()"`

## Reglas del proyecto (no negociables)

- **General, no "para mí"**: nada del usuario hardcodeado; perfil = facts en BD,
  filtros = `site_config` declarativo, credenciales = Credential Manager.
- **Esquema solo con migraciones**; **secretos y datos personales nunca al
  repo** (`.env`, `data/usuario/`, `data/empresas/`, CVs `*.pdf/docx/doc` están
  gitignoreados **a propósito** — no "arreglar" el `.gitignore`).
- **Cada fetcher nuevo** lleva test en `tests/test_<nombre>.py`.
- Todo requisito vigente debe llevar `evidence` literal (trazable al texto).
- La ausencia de salario NO es un error del extractor (~1–2 % de avisos lo
  declara): es falta de dato real.

## Comandos de consulta

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py -X utf8 -m jobpulse_v15 --help
& $py -X utf8 -m jobpulse_v15 site list --needs-review
& $py -X utf8 -m jobpulse_v15 site mark-reviewed --id <site_id> | --all-needs-review
& $py -X utf8 -m jobpulse_v15 init-areas [--classify]
& $py -X utf8 -m jobpulse_v15 areas list | areas classify [--dry-run]
& $py -X utf8 -m jobpulse_v15 enrich posting-language [--apply]
& $py -X utf8 -m jobpulse_v15 enrich profile-canonico [--apply]
& $py -X utf8 -m jobpulse_v15 taxonomy curate [--apply] [--limit N]
& $py -X utf8 -m jobpulse_v15 pipeline etapas [--limite N] [--corrida ID] [--json]
& $py -X utf8 -m jobpulse_v15 viabilidad list [--banda aplicar] | top [--limit N]  # --limit por defecto: 50
# El componente SEMANTICO (embeddings) es el PREDETERMINADO, pero solo si no cuesta
# trabajo extra (modelo en la cache local de HF Y cache de embeddings que cubra el
# corpus); si no, avisa por stderr y sigue sin el. --semantica lo FUERZA,
# --sin-semantica lo quita (los dos a la vez = error de uso).
& $py -X utf8 -m jobpulse_v15 postulaciones correo --dias 90 [--apply]
& $py -X utf8 -m jobpulse_v15 postulaciones workday --apply
& $py -X utf8 -m jobpulse_v15 db check
& $py -X utf8 tools\estado_bd.py | tools\progreso_enriquecimiento.py | tools\huecos_restantes.py
& $py -X utf8 tools\corrida_medicion.py [--sin-ia]  # corre el pipeline SOBRE el corpus actual (sin scrape) para medir una etapa; ESCRIBE en la BD → respalda antes
# Medir el efecto de una corrida (ANTES -> corrida -> DESPUES -> comparar)
& $py -X utf8 tools\estado_extraccion.py antes antes.json
& $py -X utf8 tools\comparar_extraccion.py antes.json despues.json
```
