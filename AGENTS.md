# AGENTS.md — JobPulse CR v1.5

Instrucciones para agentes IA que trabajan en este repo
(`giovar24/jobpulse-cr-v15` — hasta 2026-10-26 fue la carpeta `v1_5` dentro
del repo `jobpulse_cr`).
Objetivo: orientación instantánea sin re-explorar el proyecto.

## Al iniciar sesión

1. **Lee el handoff más reciente**: `docs/HANDOFF_SESION_*.md` — estado exacto,
   objetivos (O1–O9), decisiones y pendiente inmediato.
2. Referencia de arquitectura y comparación con el proyecto principal:
   `DESARROLLO_v15.md` (§6 = notas técnicas importantes).
3. Este es un repo PROPIO e independiente (desde 2026-10-26). El proyecto
   principal v1.x sigue en `D:\Proyectos\jobpulse_cr`, **congelado** (su
   `AGENTS.md` lo advierte): no modificarlo. Sus comandos (`main.py`,
   `unittest`, `tools/auditar.py`) NO aplican aquí. Ojo: la rama `fork-v15`
   del repo viejo conserva la password de ANE previa a la purga — jamás
   pushearla a GitHub.

## Al cerrar sesión (OBLIGATORIO)

Cuando el usuario dice "vamos a otra sesión":
- Escribir `docs/HANDOFF_SESION_YYYY-MM-DD[_turno].md` (varias sesiones el mismo
  día → sufijo `_tarde`/`_noche`, como los existentes) con la estructura estándar:
  TL;DR, lo que se hizo, decisiones de diseño, estado de objetivos (tabla),
  cómo retomar (comandos), archivos clave, datos de contexto, pendiente inmediato.
- Commitear los cambios de la sesión.

## Mapa de documentación

| Documento | Qué es |
|---|---|
| `docs/HANDOFF_SESION_*.md` | Bitácora por sesión (empezar siempre por el más nuevo) |
| `docs/IA_ENRIQUECIMIENTO.md` | Operación del pase IA: modelo local, caché, depuración |
| `docs/SITIOS_PROBLEMATICOS.md` | Guía ANE / Indeed / LinkedIn (login-wall, Cloudflare) |
| `DESARROLLO_v15.md` | Arquitectura vs proyecto principal, objetivos O1–O9 (lista canónica en §3), comandos |
| `README.md` | Setup equipo nuevo: venv, `pip install -e .`, `init-db`, backup |

## Scrapers de navegador: ANE, Indeed, LinkedIn

**Guía completa: `docs/SITIOS_PROBLEMATICOS.md`** (leer ANTES de depurar
cualquiera de estos 3 — tiene errores exactos con su solución y procedimientos
de recuperación). Reglas de oro que resumen todo el documento:

1. **Brave corre con CDP 9222 y el perfil real**: `--user-data-dir` apunta
   a la raíz `User Data`, **NUNCA** a `User Data\Default` (crea perfil vacío y
   todos los logins "fallan"). Verificar: `curl http://127.0.0.1:9222/json/version`.
   **Desde O7.2 (2026-10-27) el barrido de la UI abre Brave solo** (si hay
   sitios de navegador) y lo cierra al terminar — solo si ella lo abrió.
   Si tu Brave diario corre SIN CDP, la app no puede abrir el puerto (Chromium
   delega en la instancia viva): ciérralo del todo y reintenta.
   Launcher: `.\jobpulse-v15.bat` (venv + Brave CDP + UI; la IA ya no se
   pre-arranca).
2. **ANE (ane.cr)**: sesión obligatoria. Sin sesión el barrido se omite limpio
   (no es error). Re-login **desde la UI**: botón **"Re-login ANE"** en el
   diálogo de Corrida (O7.4; abre/cierra Brave solo si hace falta). Vía CLI:
   `.\.venv\Scripts\python.exe login_ane.py` (wrapper; lee la credencial del
   almacén `credencial("ANE")` — keyring de Windows; nada en código ni `.env`)
   → re-barrido
   `.\.venv\Scripts\python.exe run_scrapes.py ane` (scripts de la raíz del fork:
   siempre el python del venv). Ojo: ANE **republica vacantes con IDs
   nuevos**, pero es minoría — el 26-10 solo 4/120 eran republicaciones
   (desc. idéntica + fecha movida). Revisar con `quality duplicates` +
   comparar descripciones; dedupe manual, nunca automerge.
3. **Indeed (cr.indeed.com)**: SSO Google. El popup de alertas de empleo
   intercepta clics — ya resuelto con `_cerrar_popups`; si aparece un popup
   nuevo, agregar su selector en `_POPUP_SELECTORES`.
4. **LinkedIn**: REGLA DE ORO sesión primero — login MANUAL una vez en tu
   Brave (el auto-login dispara CAPTCHA/2FA). Rate-limit 429 en `jobs-guest`:
   esperar y reducir `pages`.

## Reglas del proyecto (no negociables, acordadas con el usuario)

- **Pensar en general, no "para mí"**: nada del usuario hardcodeado. Perfil =
  facts en BD; filtros de sitios = `site_config` declarativo; credenciales =
  Credential Manager (`credenciales.py`).
- **Límites IA solo opt-in**: `IA_MAX_LLAMADAS`/`IA_RPM` en `.env` o args;
  servidores locales sin tope por defecto.
- **Scrapers browser reciben `port` CDP** del caller; el fetcher nunca crea navegador.
- **Config declarativa**: plataformas/sitios en BD (`init-sources`), no en código.
- **Dedupe conservador** (decisión 27-10, portando O8 de v1.x): duplicado
  EXACTO (clave empresa|título|ubicación y/o huella de descripción idéntica)
  se auto-marca `dup_of` / hereda estado al ingest — patrón probado en v1.x;
  lo DUDOSO (similitud media) lista `quality duplicates` para revisión manual.
  NUNCA se borra ni se funden datos.
- **Esquema solo con migraciones**: cambio de BD = archivo nuevo
  `src/jobpulse_v15/migrations/00N_*.sql`; nunca ALTER manual ni editar una
  migración ya aplicada.
- **Cada fetcher nuevo** lleva test en `tests/test_<nombre>.py`.

## Comandos esenciales

```powershell
# Arranque (equipo nuevo incluido): venv + Brave CDP 9222 + UI
# (la IA ya NO se pre-arranca: la UI la levanta bajo demanda — botón "Enriquecer")
.\jobpulse-v15.bat
#   (su ruta de Brave está hardcodeada para el PC del usuario; el launcher
#    portátil es .\jobpulse-v15.ps1)

# CLI de orquestación: scrape, site, platform, credenciales, login, run, search, quality…
.\.venv\Scripts\python.exe -m jobpulse_v15 --help

# Servidor IA local (Gemma 4 E2B QAT, puerto 8081) — verificar/arrancar
.\ia-server.bat                # o: .\.venv\Scripts\python.exe start_ia_server.py

# Instalador IA para equipo nuevo (modelo Unsloth + llama.cpp; idempotente)
.\instalar-modelo-ia.bat       # --check = solo verificar

# Enriquecimiento (idempotente: solo procesa lo que falta)
.\.venv\Scripts\python.exe run_enriquecimiento.py

# Diagnóstico BD (SQLite: data/jobpulse_v15.db)
.\.venv\Scripts\python.exe tools\estado_bd.py            # resumen
.\.venv\Scripts\python.exe tools\progreso_enriquecimiento.py   # % por campo
.\.venv\Scripts\python.exe tools\huecos_restantes.py     # huecos: basura vs recuperable

# Tests — test_ui requiere display; corre OK en el PC del usuario (244 tests).
# pytest vive en el python del sistema (el venv no lo tiene instalado).
# Los roots Tk de test se crean con `_tkroot_reintentos()` (tests/test_ui.py):
# encadenar muchos interpretes Tcl falla de vez en cuando en Windows
# ('Can't find a usable tk.tcl', 'tcl_findLibrary' — transitorio, reintentar).
python -m pytest tests/ -q

# UI
.\.venv\Scripts\python.exe -m jobpulse_v15.ui
```

## Gotchas que cuestan horas (leer antes de depurar)

1. **Caché IA en disco** (`data/usuario/ia_cache/`, hash proveedor+modelo+mensajes):
   en pruebas/benchmarks responde instantáneo y falsea resultados. Aislar con
   `JOBPULSE_IA_CACHE` (así lo hace `tools/comparar_ia.py`).
2. **`work_mode='unknown'` es honesto**: el texto de la oferta no menciona
   modalidad. No forzarlo; esos jobs se re-seleccionan en cada pase pero la
   caché los hace instantáneos.
3. **Jobs con descripción basura** (login-wall, ~14-19): el enriquecimiento NO
   los recupera; requieren re-barrido del scraper (O5.3).
4. **`/metrics` del llama-server** requiere arrancar con `--metrics` (ya está
   en `start_ia_server.py`); sin él, el endpoint devuelve 501.
5. **`only_critical` solo filtra la SELECCIÓN de jobs**: `enrich_job_fields`
   llena TODOS los huecos de los jobs seleccionados, incluidos secundarios.
   Efecto neto benigno (idempotente), pero no te sorprendas en los logs.
6. **A/B de modelos**: usar `tools/comparar_ia.py` (caché aislada + mismos jobs).
7. **`-X utf8` SIEMPRE en CLI/scripts que imprimen datos de la BD**: un
   `\uf0b7` dentro de una descripción revienta la salida (extract-pending
   reventó así; los saves se completan igual — idempotente). Para CSV por
   consola, fijar antes `[Console]::OutputEncoding = UTF8` (un NEL `\x85`
   parte líneas y falsea conteos).
8. **Venv movido con el repo, no recreado**: los `activate` y `pip.exe` del
   venv apuntan a la ruta vieja y fallan. Siempre `.\.venv\Scripts\python.exe`;
   para pip, `python.exe -m pip` (nunca `pip.exe` ni `activate`).
9. **`--profile-compatibility` se aplica DESPUÉS de `--limit`**: un límite
   chico puede devolver 0 filas aunque haya coincidencias más atrás.
10. **Los launchers NO reinstalan deps si el venv ya existe**: tras añadir
    deps a `pyproject.toml` → `python.exe -m pip install -e .` a mano (así se
    detectó el keyring faltante).
11. **Bug del perfil vacío en `BraveManager` — CORREGIDO (O7.1, 2026-10-27)**:
    `_get_user_data_dir()` devolvía `User Data\Default` en vez de la raíz
    `User Data` (perfil vacío → logins heredados "fallan"; lo enmascaraba
    `login_ane.py`, que teclea credenciales frescas). Fix: raíz +
    `--profile-directory={perfil}`. El botón "Login manual" de Configuración
    y el CLI `login` ya usan el perfil real.
12. **Tests que tocan el cliente IA local DEBEN parchear `asegurar_servidor`**:
    sin el patch, el worker del pase IA de CV arranca el llama-server REAL en
    plena suite (saturación de RAM — ocurrió 2026-10-27; el usuario lo notó).
    Patrón: `patch("jobpulse_v15.ui_perfil.asegurar_servidor", return_value=None)`
    (ver tests del pase IA de CV en tests/test_ui.py).
13. **Embeddings (`search_engine.py`) DORMIDOS por decisión del usuario
    (2026-10-27)**: verificados funcionales (EmbeddingGemma es gated en HF →
    fallback `paraphrase-multilingual-mpnet` 768d; similitud ES↔EN correcta)
    pero SIN cablear y con caché vacía. La precisión de búsqueda viene de la
    data extraída (O1) — nicho del motor: texto libre ES↔EN. `ats.py`/`gate.py`/
    `ia_calibracion.py` sin callers ni tests; no borrar sin redefinir O2/O4.
14. **`failed` en `run_ia_enrichment` NO es error de red**: cuenta jobs cuya
    respuesta IA fue null/"no mencionado" para lo que faltaba; en ciclos
    siguientes la caché de disco los repite instantáneo (0 llamadas HTTP) y
    siguen contando "failed". Los errores REALES se ven como WARNING
    "IA extract {campo} fallo tras 3 intentos". Pase 27-10: ciclo 2 con
    "failed=155" resuelto en 1 segundo = puro caché, nada roto.

## Estado de referencia (actualizado 2026-10-28)

- Modelo local canónico: **Gemma 4 E2B QAT** (8k ctx, MTP draft, puerto 8081).
  Qwen 3.5 2B descartado: ~6.5x más lento y llena mucho menos (ver
  `docs/IA_ENRIQUECIMIENTO.md`).
- **Instalador IA para equipo nuevo**: `instalar-modelo-ia.bat` (modelo desde
  Unsloth HF con SHA256 verificados + llama.cpp + deps; `--check` = verificar).
- **Capa IA de CVs (`cv_ia.py`)**: CV PDF/DOCX/TXT → harvard-ats-v1; probada
  E2E con Gemma local y Gemini (39 facts consistentes; import+revert OK).
  **Integrada** al botón "Importar CV…" de la UI (`ui_perfil.py`): reglas
  primero; si sugieren < 5 facts se ofrece el pase IA (aviso de privacidad
  si el motor del `.env` es externo; progreso no-modal; datos llegan a
  `_DialogoRevision` para revisión antes de guardar).
- **BD: 927 jobs** (ANE 332, Workday 282, Harvie 192, Workable 15, Indeed 36,
  CINDE 17, Greenhouse 13, Ashby 12, Recruitee 11, LinkedIn 9,
  SuccessFactors 7, Procomer 1). Republicaciones ANE curadas: 7 `dismissed`
  + `dup_of` al nuevo. Enriquecimiento: 273 requisitos extraídos;
  ~127 jobs sin `job_analysis`; skills/languages/city/region con huecos
  recuperables.
- Perfil: 48 facts (editor CV en `ui_perfil.py`; datos reales ya cargados;
  `value_code='portfolio'` reservado). 4 CVs en `data/usuario/cv/` (pruebas).
- **O7 UI-first completo (2026-10-28, commit `28ef1f2`)**: flujo **scrape →
  analizar (reglas) → IA → comparar perfil** en un click (checkbox en Corrida).
  "Enriquecer" = IA bajo demanda (validado E2E); "Re-login ANE" = Brave auto.
  Suite: **324 tests** (la base de 293 + `test_matching.py` 31; se arregló
  `test_database.py` que fijaba la versión de esquema en `8`).
- **O6.3 / Paso 5 — matching requisitos vs. perfil (2026-10-29) ✅**: módulo real
  `src/jobpulse_v15/matching.py` (los `paso5_*.py` de la raíz están obsoletos);
  migración `015_job_match_valida.sql` (columna `valida`); **cada cambio de regla
  = una corrida NUEVA** en `job_match` (nunca UPDATE in-place). Regla acordada:
  `descartada` solo si el TEXTO completo confirma título universitario **obligatorio**
  **sin negación y sin alternativa**; si no → `revisar_a_mano` +
  `educacion_no_confirmada`. "bachiller" NO es universitario (en CR es
  secundaria); "licenciatura" sí. **La obligatoriedad la decide el TEXTO**
  ("Required/Minimum/Basic Qualifications", "must have", "degree or above"), no
  solo `requirement_level`; "Preferred" no bloquea. "or equivalent field of
  study" NO es vía alternativa; "or advanced coursework/university studies" SÍ.
  **Estudiante activo** ("currently pursuing", "must be enrolled") es criterio
  distinto → motivo `titulo_universitario_en_curso_requerido`.
  Corrida vigente **`20261029_183231`**: calificada 102 · revisar_a_mano 141 ·
  sin_requisitos 141 · **descartada 45** (37 título + 8 en curso) ·
  datos_insuficientes 31 (las 5 corridas previas quedan `valida=0`).
  Evidencia literal: `docs/PASO5_EVIDENCIA_2026-10-29.md` (generado por
  `generar_evidencia_paso5.py`).
  Herramientas: `run_paso5.py` (`--dry`), `evidencia_descartadas.py`,
  `resumen_bloqueo.py`, `verificar_corridas.py`.
  **Pendiente: aplicar a mano las 20 `educacion_no_confirmada` (Paso 7).**
- **Veredicto del enriquecimiento (`ia_estado.py`, 2026-10-29)**: el flujo ya no
  "asume" que la IA terminó — mide la BD antes/después del pase y decide:
  `evaluar_ia()` → `completado` | `parcial` | `sin_trabajo` (OK) vs `atascado`
  (0 progreso con huecos recuperables) | `fallido` (`error` de `pase_completo`).
  La BD manda sobre las stats de `pase_completo`. Integrado en
  `run_full_flow.py` (exit 0/1 + toast ✅/⚠️) y en la UI (paso 3 del flujo y
  botón "Enriquecer" muestran el estado en el diálogo).
  Separar huecos **recuperables** vs desc. basura (`<200` chars) es clave: la
  basura no cuenta como fallo de la IA.
- **Grilla del paso 4 vacía — resuelto (2026-10-29)**: el paso 4 filtraba
  `matched` a ciegas y **`matched` suele ser 0 en BD real**: 370/447 análisis
  son `partial` (el analizador marca `unknown`/`ambiguous` y el repo exige
  `complete` para `matched` → `needs_review`). Ahora
  `ui.elegir_filtro_compatibilidad(conteo)` usa `matched` si existe y si no
  **muestra todos los vigentes**, explicando en el diálogo la distribución.
  Ojo con **`solo_vigentes` (O8)**: oculta publicaciones con `date_published`
  fuera de la ventana de 6 meses aunque se hayan scrapeado hoy (447 → 423 en
  la BD del 29-10, 24 ocultas por fecha vieja de Workday/Indeed).
  El guard de `analysis_status` está en `analysis.py:334` y
  `repository.candidate_profile_status` (línea ~2522).
- **CLI end-to-end `run_full_flow.py`** (raíz del fork): scrape → reglas →
  IA → resumen con veredicto; `--only-scrape`, `--no-notify`. Los monitores
  ad-hoc (`status_ia.py`, `vigilar_enriquecimiento.py`) son desechables: usar
  `python -X utf8 -c "from jobpulse_v15.ia_estado import snapshot_enriquecimiento as s; print(s())"`
  para un chequeo puntual.
- **`clean_run.py`** (raíz del fork): limpia TODO lo scrapeado para una corrida
  de prueba limpia — jobs, runs, análisis, requisitos, `field_status`,
  source_records, snapshots + VACUUM; **conserva** perfil (facts) y config
  (sites/plataformas). Requiere argumento literal `SI` (corre no-interactivo):
  `.\.venv\Scripts\python.exe -X utf8 clean_run.py SI`.
- **O3 ATS CR directorio versionado (commit `a9083a7`)**: 122 tableros
  (Workday, Greenhouse, Ashby, Lever, Recruitee, Workable, SuccessFactors) en
  `src/jobpulse_v15/seeds/*.json` + botón "Importar directorio ATS (CR)".
  Primer job Workday/Intel scrapeado.
- **Objetivo O3 — Scraping masivo ATS**: **7/7 plataformas validadas** (83/122
  sitios con jobs CR: Workday 51, Greenhouse 8, Ashby 7, Lever 3, Recruitee 3,
  SuccessFactors 4, **Workable 7**). Workable fetcher reescrito para formato
  `jobs.md` markdown (commit actual). Script `run_ats_scrapes.py` listo para
  barrido masivo.
- **Nueva fuente O3: Harvie (commit `3355c7c`)** — `harvie.py` + sitio
  `harvie-cr` registrado. API JSON `https://heyharvie.com/api/candidate/jobs`
  (paginado), 192 jobs CR importados (Lagar, Grupo El Lagar, Grupo Sur Química,
  etc.). `work_mode` detectado via campo `workplace` (on-site/remote/hybrid).
- **Nueva fuente O3: Elempleo (commit actual)** — `elempleo.py` + sitio
  `elempleo-cr` registrado. Browser automation via Playwright CDP
  (iguala a ANE/Indeed/LinkedIn). Selectores: `.result-item` (cards),
  `data-url` para detalle, `h2.item-title.ee-mod a.js-offer-title` (título),
  `.item-company a` (empresa). Detalle extrae: ubicación, modalidad
  (`work_mode`), tipo empleo, fecha, descripción, requisitos, salario.
- Sub-objetivo O3.x — Gestión tableros en Configuración/Fuentes: activar/pausar
  individual, filtrar por plataforma.
- Embeddings verificados funcionales y **DORMIDOS** (data-first) — gotchas 13-14.
- Pendiente O8: O8.1 categorías borrador, prueba de humo usuario, confirmar
  retención 6m, smoke herencia ANE (requiere marcar `reviewed`/`applied`).
