# AGENTS.md — JobPulse CR v1.5

Orientación para agentes IA en este repo (`giovar24/jobpulse-cr-v15`; hasta el
2026-10-26 fue `v1_5/` dentro del repo `jobpulse_cr`). Solo lo **verificable y
caro de descubrir**; lo puntual vive en los handoffs.

## Al iniciar sesión

1. Lee el **handoff más reciente**: `docs/HANDOFF_SESION_*.md` (estado exacto,
   objetivos O1–O10, pendiente inmediato). Arquitectura: `DESARROLLO_v15.md`.
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

## Dos Pythons (regla que más se rompe)

- **App/CLI/scripts** → venv: `.\.venv\Scripts\python.exe -X utf8 …`
- **Tests** → python del **sistema**: `python -m pytest tests/ -q`
  (pytest **no** está en el venv; ~11 min la suite completa; baseline verificado
  2026-11-05: **922 passed + 241 subtests**).
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
- **El CLI migra el esquema al abrir la BD** (avisa `[esquema] Se aplicaron las
  migraciones N-M`). `init-db`, `backup` y `db check` **no** migran.
- Esquema por migraciones: `src/jobpulse_v15/migrations/0NN_*.sql`. Cambio de
  esquema = **archivo nuevo**; nunca `ALTER` manual ni editar una migración ya
  aplicada. Versionado con `PRAGMA user_version` (actual: **21**).
- `clean_run.py SI` = borrado total de lo scrapeado (jobs, análisis, runs,
  `job_match`); conserva perfil, sitios, taxonomías y reinicia la salud de los
  sitios. **Destructivo**: solo con pedido explícito del usuario.
- `… -m jobpulse_v15 db check` = integridad + FK (exit≠0 si falla).

## Pipeline completo (el orden NO es negociable)

```powershell
$py = ".\.venv\Scripts\python.exe"
# 1. Scrape (solo con red; los tableros API no necesitan browser)
& $py -X utf8 run_full_flow.py --only-scrape --pages 1     # o: -m jobpulse_v15 scrape <plataforma> --site <id>
# 2. Análisis por reglas (idempotente: solo lo que falta)
& $py -X utf8 -m jobpulse_v15 analysis extract-pending --limit 500
# 3. ENRIQUECIMIENTO IA  ← rellena jobs.skills / jobs.languages
& $py -X utf8 run_enriquecimiento.py
# 4. Re-análisis integrando los CAMPOS ESTRUCTURADOS del aviso
& $py -X utf8 -m jobpulse_v15 enrich requirements-source --apply
# 5. Backfill del código canónico de los requisitos ya guardados
& $py -X utf8 -m jobpulse_v15 enrich requirements-canonico --apply
# 6. Matching: CORRIDA NUEVA (nunca UPDATE de la anterior)
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
- la UI clásica: mantiene su flujo (intacta por regla) pero usa las mismas
  implementaciones por etapa, incluido el re-análisis (paso 3.5).

```python
from jobpulse_v15 import pipeline
resultado = pipeline.ejecutar(repository, etapas=("analisis", "reanalisis", "paso5"))
print(pipeline.resumen_linea(resultado))
```

Reglas: una etapa desconocida es `ValueError`; el Paso 5 es siempre **corrida
nueva**; la etapa `ia` con proveedor externo **no** arranca nada local y la
confirmación de privacidad la hace el caller (UI) antes de invocar.

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

- **La CLI NO abre Brave**: los scrapers de navegador (ANE, Indeed, LinkedIn,
  Elempleo) reciben el `port` CDP del caller y el fetcher **nunca** crea un
  navegador. Antes de `scrape ane|linkedin|indeed` levanta CDP:
  `python -c "from jobpulse_v15.browser_manager import asegurar_brave; asegurar_brave(9222)"`
  (o usa `run_full_flow.py`, que sí lo abre y lo cierra).
- Brave debe usar el **perfil real**: `--user-data-dir` = raíz `User Data`
  (NUNCA `User Data\Default`) + `--profile-directory={perfil}`. Si el Brave
  diario corre sin CDP, Chromium **delega** el puerto y nada abre: ciérralo
  del todo. Puerto configurable: `BRAVE_CDP_PORT` es la única fuente
  (`browser_manager.puerto_cdp_configurado()`).
- **ANE**: sesión obligatoria. Credencial: keyring de Windows → `data/empresas/
  credenciales.json` → `.env` (`ANE_USER`/`ANE_PASSWORD`); nunca en el repo.
  ANE republica vacantes con IDs nuevos → `quality duplicates`, dedupe manual,
  **nunca** automerge.
  **Trampa (verificada 2026-11-05, RESUELTA en O12 · Ola 1.5)**: antes
  `login_ane.py` cerraba el Brave que abrió con `terminate()`/`kill()` → la
  cookie de sesión **no quedaba persistida** y el barrido siguiente decía
  "ANE: sin sesión de detalle" con 0 avisos. Ahora cierra **ordenado**
  (`Browser.close` por CDP) y `--mantener-abierto` deja el navegador vivo para
  raspar de inmediato. Flujo recomendado: `login_ane.py --mantener-abierto` y
  acto seguido `scrape ane --site ane-cr` (sin cerrar el navegador).
- **LinkedIn**: sesión primero, login **manual** (el auto-login dispara
  CAPTCHA/2FA). Rate-limit 429 en `jobs-guest` → bajar `pages`.
- **Indeed**: SSO Google; el popup de alertas intercepta clics (ya resuelto en
  `_cerrar_popups`; si aparece uno nuevo, añadir su selector).
- **Selectores desactualizados (verificado 2026-11-05, ambos dan 0 avisos)**:
  - **LinkedIn** sirve ahora `/jobs/search-results/` con clases ofuscadas
    (`fa4afe…`), sin `div.base-card` ni `li[data-occludable-job-id]` y sin
    enlaces `/jobs/view/` → hay que actualizar `linkedin.py` (no es login-wall:
    no hay authwall).
  - **Elempleo** ahora usa `.ee_list-item` en vez de `.result-item` /
    `.js-area-bind.area-bind` → actualizar `elempleo.py`.
  Al tocar un scraper: actualizar también su test en `tests/test_<nombre>.py`.
- **Salud de sitios**: 3 corridas seguidas con 0 avisos → `review_required=1`
  (NO se desactiva solo). `site list --needs-review` y
  `site mark-reviewed --id <id>` (reinicia el racho). `clean_run.py` también
  reinicia la salud (si se borran las corridas, se borra su veredicto).
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
- **`educacion_no_confirmada`**: solo la firma una **segunda persona** en
  `docs/PASO5_REVISION_PENDIENTES.md` (el veredicto del autor de la regla se
  descarta por sesgo). **NO** actualizar estados antes de la firma.
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
2. **Nunca insertar requisitos por SQL directo**: `job_requirements` tiene
   `analysis_id` (FK a `job_analysis`), no `job_id`. Usa `Repository.save_analysis`.
3. `jobs.posting_language` es NOT NULL (tests: `undetermined`); `mixed` es
   válido. `concepto` no tiene `nombre`: es `codigo_canonico` + `variante`.
4. `jobs.requirements_raw` es NULL en casi todos los Workday: el texto real
   está en `description_raw` (~4–5k chars) → buscar en ambos.
5. **El score sin imputación es degenerado**: una vacante con 1 solo requisito
   cubierto saca 100. Viabilidad y ranking ATS hacen **dos pasadas** (pesos
   fijos + imputación del promedio del corpus).
6. `Database.connection()` es un context manager y `EvaluadorPaso5` carga los
   datos **al construirse** → conexión viva durante toda la evaluación y
   evaluador **nuevo** por evaluación. En Windows, cerrar la conexión **antes**
   de borrar el temporal (`PermissionError` si no).
7. **Caché IA en disco** (`data/usuario/ia_cache/`): falsea benchmarks →
   aísla con `JOBPULSE_IA_CACHE`. `failed` en el pase IA **no** es error de
   red (cuenta "no mencionado"); los errores reales avisan
   "IA extract {campo} fallo tras 3 intentos".
8. **Caché de embeddings**: el temporal debe terminar en `.npy`
   (`embeddings_cache.npy.tmp.npy`) o `np.save` añade otra extensión y el
   `replace()` falla → se re-vectoriza todo el corpus en cada arranque.
9. `job_field_status` **no** tiene categoría `salary` (el estado del salario se
   mira en `jobs.salary_min`; la regla de "declara salario" vive en `salario.py`).
10. El **TÍTULO** de un aviso no es fuente de ubicación; el catálogo Workday
    devuelve el título entero como ciudad (no hacerlo).
11. Tk: fuentes con espacio van **entre llaves** (`{Segoe UI} 10`); nunca
    mezcles `pack` y `grid` en el mismo padre; un widget sin gestor queda
    invisible (1x1); el callback de `yscrollcommand` solo actualiza el
    scrollbar (tocar el canvas ahí = reentrada infinita).
12. En tests: `with patch(...) as m` deja `m` **sin definir** fuera del bloque
    → guarda el mock en otra variable. Los tests del cliente IA deben parchear
    `jobpulse_v15.ui_perfil.asegurar_servidor` (si no, arranca el llama-server
    real en plena suite → saturación de RAM).
13. `with ... as X` borra el nombre al salir del bloque (comportamiento de
    Python, no de Tk).
14. Retención: la política vive en `ui_config.json` y la comparten UI clásica y
    v2 (merge en `ui_v2/data/retencion.py`); la retención **oculta, nunca borra**.

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
  aviso + confirmación obligatoria (UI) / `--confirmar-externo` (CLI).
- Límites **opt-in y ajustables**: `IA_MAX_LLAMADAS`/`IA_RPM`/`IA_MAX_VACANTES`
  (avisos por corrida; vacío = **sin tope**, no hay valores fijos).

## UI

- **UI clásica** (`ui.py`): completa e intacta — no la toques sin pedirlo.
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
& $py -X utf8 -m jobpulse_v15 site mark-reviewed --id <site_id>
& $py -X utf8 -m jobpulse_v15 init-areas [--classify]
& $py -X utf8 -m jobpulse_v15 areas list | areas classify [--dry-run]
& $py -X utf8 -m jobpulse_v15 enrich posting-language [--apply]
& $py -X utf8 -m jobpulse_v15 enrich profile-canonico [--apply]
& $py -X utf8 -m jobpulse_v15 viabilidad list [--banda aplicar] | top --limit 20
& $py -X utf8 -m jobpulse_v15 postulaciones correo --dias 90 [--apply]
& $py -X utf8 -m jobpulse_v15 postulaciones workday --apply
& $py -X utf8 -m jobpulse_v15 db check
& $py -X utf8 tools\estado_bd.py | tools\progreso_enriquecimiento.py | tools\huecos_restantes.py
```
