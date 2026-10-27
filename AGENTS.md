# AGENTS.md — JobPulse CR v1.5

Instrucciones para agentes IA que trabajan en este repo
(`giovar24/jobpulse-cr-v15` — hasta 2026-10-26 fue la carpeta `v1_5` dentro
del repo `jobpulse_cr`).
Objetivo: orientación instantánea sin re-explorar el proyecto.

## Al iniciar sesión

1. **Lee el handoff más reciente**: `docs/HANDOFF_SESION_*.md` — estado exacto,
   objetivos (O1–O7), decisiones y pendiente inmediato.
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
| `DESARROLLO_v15.md` | Arquitectura vs proyecto principal, objetivos O1–O7 (lista canónica en §3), comandos |
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
- **Dedupe conservador**: `quality duplicates` lista grupos candidatos para
  revisión manual; nunca automerge (`dup_of` previsto, hoy no existe la
  columna). ACTUALIZADO (27-10, decisión de usuario por portar O8 desde
  v1.x): los duplicados EXACTOS (clave empresa|título|ubicación y/o huella
  de descripción idéntica) se auto-marcan `dup_of` o heredan estado al
  ingest — cero riesgo, patrón probado en v1.x; lo DUDOSO (similitud media)
  sigue siendo revisión manual; NUNCA se borran ni se funden datos.
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

## Estado de referencia (2026-10-26, tras re-barrido ANE)

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
- BD: **295 jobs** (ANE 240 = 120 lote 25-10 + 120 lote 26-10 — el lote nuevo
  es casi todo NUEVO: **solo 4 republicaciones** con desc. idéntica + fecha
  movida; las 4 VIEJAS quedan `dismissed` con nota desde el 27-10, las 4
  nuevas activas. Los grupos misma-empresa+misma-ciudad (INAMU, SALESLAND)
  son plazas múltiples por decisión del usuario. En ANE la identidad real es
  la DESCRIPCIÓN, no el título+empresa ("Confidencial"). Indeed 30,
  CINDE 17, LinkedIn 7, Procomer 1).
  Enriquecimiento COMPLETO (27-10, O1 ✅): city faltan 24 (mayoría remotos o
  lat_raw de Indeed sin normalizar), region 13, work_mode 'unknown' 137
  (46 basura O5.3 + 91 honestos sin mención), employment_type 14, skills 0,
  languages 14 (10 basura), salary_raw 117 = fuente sin texto (irrecuperable).
  Análisis: 295/295 hechos (273 requisitos).
- Perfil: 48 facts (editor CV en `ui_perfil.py`; datos personales y resumen
  reales ya cargados; `value_code='portfolio'` reservado). Compatibilidad
  sobre 295: no_required 168, needs_review 109, not_registered 18, matched 0.
  Los 4 CVs en `data/usuario/cv/` son material de pruebas (mismo CV en ES/EN).
- **Sesión 2026-10-27 (O7 + O5.4 + O1)**: flujo UI-first — el barrido de la
  UI abre/cierra Brave; botones "Enriquecer" (servidor IA bajo demanda,
  validado E2E: subió → 44 min de pase → se apagó solo) y "Re-login ANE";
  el launcher ya no pre-arranca la IA. Suite: 244 tests. O5.4 cerrado: solo
  4/120 del lote nuevo eran republicaciones (la huella en ANE es la
  DESCRIPCIÓN, no título+empresa); las 4 viejas quedaron `dismissed` con
  nota; los grupos INAMU/SALESLAND son plazas múltiples (decisión del
  usuario). Embeddings verificados funcionales y DORMIDOS por decisión del
  usuario (data-first) — ver gotchas 13-14.
