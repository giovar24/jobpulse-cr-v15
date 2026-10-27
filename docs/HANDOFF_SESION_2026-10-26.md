# Handoff — JobPulse CR v1.5 — Sesión 2026-10-26

Reemplaza como handoff vigente al de la noche del 25
(`HANDOFF_SESION_2026-10-25_noche.md`).

> **CAMBIO DE CASA**: el fork YA NO vive en `D:\Proyectos\jobpulse_cr\v1_5`.
> Es el repo propio **`github.com/giovar24/jobpulse-cr-v15`** en
> **`D:\Proyectos\v1_5`** (historial completo, 95 commits via subtree split).
> El repo viejo (`D:\Proyectos\jobpulse_cr`) queda **congelado** (nota en su
> `AGENTS.md`, Bitácora 63; rama local `fork-v15` = archivo histórico del fork).

## TL;DR

- **Seguridad (regla dura cumplida)**: `login_ane.py` quedó SIN credenciales —
  lee del almacén (`credencial("ANE")`: keyring de Windows +
  `data/empresas/credenciales.json`, fallback `.env` ANE_USER/ANE_PASSWORD).
  `keyring` instalado en el venv (pyproject lo declaraba; faltaba) y la
  credencial ANE migrada al keyring. **PENDIENTE USUARIO: rotar la password en
  ane.cr** (sigue expuesta en el historial PÚBLICO del repo viejo; el nuevo se
  purgó con `git filter-repo` ANTES de publicar).
- **Mudanza completada**: repo público propio, venv + `.env` + BD movidos con
  la carpeta, instalación editable reparada (venv y python del sistema),
  sesión de OpenCode movida. Suite **217 passed + 46 subtests** verde en la
  nueva casa.
- **Docs verificados contra el código** (no solo editados): `AGENTS.md`
  (launcher, CLI, migraciones, dedupe real, python del venv, sufijo de
  handoffs), `DESARROLLO_v15.md` (estado 2026-10-26: FASE 1 completa, gaps
  reales, pytest, init-sources, ruta Brave corregida — decía `User Data\Default`),
  `README.md` (pytest del sistema, pase IA de CVs, launcher).
- **E2E todo verde en la nueva casa**: UI ✓, cinde/procomer idempotentes ✓,
  Brave CDP vía `BraveManager` ✓, **login ANE OK con la credencial migrada** →
  re-barrido ANE 120 nuevas → **BD 175 → 295**. Análisis 295/295 (273
  requisitos). Perfil (48 facts) aplicado a los 295 jobs.
- **Bugs de UI corregidos** (encontrados por el usuario al probar): `_ejecutar`
  del diálogo de corrida (NameError de `site_vars`) y el botón "Guardar todo"
  (método inexistente — la Configuración ni abría). Suite 217 → **221**.

## 1. Lo que se hizo

### Seguridad: el repo quedó sin secretos
- `v1_5/login_ane.py` tenía la password de ANE **en texto plano commiteada**
  (añadida en `b447371` del repo viejo, irónicamente el commit que migró las
  demás al Credential Manager). Reescrito: mismas selectores/verificaciones,
  pero credenciales desde `credencial("ANE")`.
- `keyring` faltaba en el venv (pyproject lo declara desde su añadido): sin él
  el almacén cae a texto plano en el JSON. Instalado con
  `python.exe -m pip install "keyring>=25"`.
- Credencial ANE migrada al keyring leyéndola DESDE el historial git (script
  temporal, nunca impresa en outputs ni logs). Verificado:
  `credencial("ANE")` → usable, `almacen: keyring`. El servicio de keyring es
  "JobPulse CR v1.5".
- Antes de publicar el repo nuevo: `git filter-repo --replace-text` purgó la
  password de TODOS los commits (verificado `git log -S<password>` = 0 hits).

### Mudanza a repo propio (petición del usuario)
- `git subtree split -P v1_5 -b fork-v15` en el repo viejo (95 commits, v1_5
  como raíz) → clon → `D:\Proyectos\v1_5`.
- Movidos con la carpeta (no versionados): `.venv` (con torch), `.env`,
  `data/` (BD + usuario + empresas + cachés IA), logs.
- Repo viejo: `git rm -r v1_5` + Bitácora 63 + `.gitignore` sin sus reglas +
  nota "NO MODIFICAR — CONGELADO" en su `AGENTS.md`.
- Repo nuevo: `.gitignore` propio (secretos/datos personales/BD/venv — el
  viejo vivía en la raíz del otro repo), rama `main`, remote a
  `github.com/giovar24/jobpulse-cr-v15` (público, decisión del usuario), push.
- Instalación editable reparada en **ambos** pythons (venv y sistema apuntaban
  a la ruta vieja): `python -m pip install -e .` — con `python.exe -m pip`
  (el `pip.exe` del venv tiene el path viejo embebido).

### Docs al día, verificados contra el código
- `AGENTS.md`: launcher `jobpulse-v15.bat`, CLI `python -m jobpulse_v15 --help`,
  BD `data/jobpulse_v15.db`, regla de migraciones (`00N_*.sql`, 7 hay),
  dedupe real (`quality duplicates`; **`dup_of` NO existe** — era un plan),
  handoffs con sufijo `_tarde`/`_noche`, README en el mapa, scripts de raíz
  con python del venv, item de repo propio vs raíz congelada.
- `DESARROLLO_v15.md`: §1 tabla (auth/CV/tests/búsqueda actualizados), §2
  estado 2026-10-26 (fetchers CR COMPLETOS, gaps reales: dedupe cross-source,
  scheduler, O2/O3/O4), §3 FASE 1 COMPLETADO, §4 comandos (pytest,
  init-sources, ruta Brave corregida), §5 pendientes vivos, changelog
  2026-10-25/26, pie re-fechado.
- `README.md`: tests con pytest del sistema (decía unittest con venv), pase IA
  de CVs en "Mi perfil", launcher de un clic, ruta de setup.
- Verificaciones que sustentan cada línea: 217 tests coleccionan; `_POPUP_SELECTORES`
  en `indeed.py`; `_tkroot_reintentos` en `test_ui.py`; `--metrics`/`--check`;
  `JOBPULSE_IA_CACHE`/`IA_MAX_LLAMADAS`/`IA_RPM`; `only_critical`; 48 facts.

### E2E en la nueva casa (petición: "UI, scraping, perfil")
| Paso | Resultado |
|---|---|
| UI (`python -m jobpulse_v15.ui`) | ✓ abrió y corrió |
| Scraping API (`run_scrapes.py cinde procomer`) | ✓ 17+1, todas duplicadas (idempotencia) |
| Brave CDP (`BraveManager.start_brave()`) | ✓ 9222 arriba con perfil real |
| ANE 1ª pasada | omitido limpio (sin sesión) — comportamiento documentado |
| `login_ane.py` (credencial del keyring) | **LOGIN ANE: OK** |
| ANE re-barrido | 120 encontradas/nuevas; BD 175 → **295** |
| `analysis extract-pending` | 295 análisis, 273 requisitos, 0 pendientes |
| `search --profile-compatibility` | 295/295 clasificados: no_required 168, needs_review 109, not_registered 18, matched 0 |

### Bugs de UI encontrados por el usuario al probar y corregidos
- `ui.py::_ejecutar` (diálogo de corrida): usaba `site_vars` — residuo del viejo
  diseño con checkboxes, ya reemplazado por Treeview + set `seleccionados` →
  `NameError` al ejecutar un barrido. Fix: `sorted(seleccionados)`.
- `configuration_window.py`: el botón "Guardar todo" referenciaba `self._save_all`
  **inexistente** → `AttributeError` al CREAR la ventana: **la Configuración ni
  siquiera abría**. Implementado `_save_all`: IA → `.env` (helper
  `_save_env_values`, preserva líneas/comentarios ajenos), UI → `ui_config.json`;
  credenciales siguen con su botón aparte (decisión explícita).
- Regresión: `tests/test_configuration_window.py` (4 tests; suite 217 → **221
  passed + 46 subtests**). El closure de `_ejecutar` no es testeable en aislado
  — verificar a mano: abrir Configuración y correr un barrido desde Corrida.

## 2. Decisiones de diseño

1. **Mudanza con `subtree split`** (no mover plano ni `git init`): preserva los
   95 commits del fork — la bitácora/handoffs son parte del método de trabajo.
2. **Público con historial purgado** (decisión del usuario entre privado /
   público-tal-cual): la password se borró de todos los blobs ANTES del push.
   La rama `fork-v15` del repo VIEJO conserva el password pre-purga →
   **NO pushear esa rama a GitHub**.
3. **`login_ane.py` lee del MISMO almacén que el auto-login** (`credencial()`)
   — una sola fuente de credenciales, como manda la regla del proyecto.
4. **Credencial migrada desde el historial**, no re-tecleada: el valor nunca
   pasó por outputs, logs ni archivos permanentes.
5. **Repo viejo congelado, no borrado**: queda como referencia + archivo
   (Bitácora 63 documenta la mudanza).

## 3. Objetivos (estado)

| Objetivo | Estado |
|---|---|
| O1 Enriquecimiento IA | ✅ completo (Gemma canónico). Pendiente: pase sobre los 120 ANE nuevos |
| O2 ATS + gate + ranking en la búsqueda UI | ⏳ no iniciado |
| O3 Validar 7 fetchers ATS huérfanos | ⏳ no iniciado |
| O4 Calibración gate-vs-IA | ⏳ depende de O1+O2 |
| O5 Higiene | 🟡 O5.1 ✅; O5.3 sigue (los ~14-19 basura VIEJOS; los 120 ANE de hoy traen descripción buena) |
| O6 Perfiles del candidato | 🟢 editor + capa IA + integración UI ✅; sigue O6.3 matching afinado |

## 4. Pendiente inmediato en la próxima sesión

1. **Enriquecimiento de los 120 ANE nuevos** (servidor Gemma 8081 arriba;
   `run_enriquecimiento.py` es idempotente). Los huecos crecieron: city 38,
   work_mode 'unknown' 148, employment_type 120, salary 117, skills 120,
   languages 124, region 13.
2. **`quality duplicates`**: ANE **republica vacantes con IDs nuevos**
   (lote viejo `121022…` del 25-10 vs nuevo `121066…` del 26-10, cero
   solapamiento; títulos repetidos tipo "Asesor (a) de Ventas" 3x). Revisión
   manual — alimenta la decisión de dedupe (`dup_of` previsto).
3. O6.3 (matching afinado: niveles/CEFR/work_authorization), O5.3, luego O2/O3/O4.
4. **Del usuario**: rotar la password de ANE en ane.cr y actualizar con
   `credenciales set --empresa ANE …`; borrar a mano el residuo
   `D:\Proyectos\jobpulse_cr\v1_5` (solo junk no versionado; quedó bloqueado
   por un proceso ajeno a la sesión).

## 5. Cómo retomar (comandos)

```powershell
cd D:\Proyectos\v1_5   # NUEVA ruta del repo propio (github.com/giovar24/jobpulse-cr-v15)

# Arranque completo: venv + servidor IA + Brave CDP 9222 + UI
.\jobpulse-v15.bat

# Suite (pytest vive en el python del sistema)
python -m pytest tests/ -q

# Enriquecimiento de los 120 nuevos (idempotente)
.\.venv\Scripts\python.exe run_enriquecimiento.py

# Duplicados ANE para revisión manual
.\.venv\Scripts\python.exe -m jobpulse_v15 quality duplicates --limit 100

# Compatibilidad del perfil (48 facts) sobre los 295
.\.venv\Scripts\python.exe -m jobpulse_v15 search --profile-compatibility not_registered --format csv
```

## 6. Archivos clave

| Archivo | Qué es |
|---|---|
| `ui.py` / `configuration_window.py` | FIXES de crash encontrados por el usuario: `_ejecutar` usa `seleccionados` del Treeview; `_save_all` implementado (IA→`.env`, UI→`ui_config.json`) |
| `tests/test_configuration_window.py` | NUEVO: regresión del botón "Guardar todo" + writer de `.env` |
| `login_ane.py` | REESCRITO: login ANE con credencial del almacén (keyring/.env), sin secretos en código |
| `.gitignore` | NUEVO del repo propio (antes dependía del .gitignore del repo viejo) |
| `AGENTS.md` / `DESARROLLO_v15.md` / `README.md` | Actualizados y verificados contra el código (ver §1) |
| Repo viejo: `AGENTS.md` nota + `DEVELOPMENT_LOG.md` Bitácora 63 + rama `fork-v15` | Congelado; NO pushear `fork-v15` (password pre-purga) |

## 7. Datos de contexto que no hay que olvidar

- **BD: 295 jobs** (ANE 240 = 120 viejos + 120 republicadas con IDs nuevos —
  dedupe manual pendiente; Indeed 30, CINDE 17, LinkedIn 7, Procomer 1).
  225 con descripción >200 chars.
- **Perfil**: 48 facts intactos; compatibilidad: no_required 168,
  needs_review 109, not_registered 18, matched 0 (código exacto: nadie cumple
  TODOS los required).
- **keyring activo**: credencial ANE bajo el servicio "JobPulse CR v1.5";
  `.env` SIN ANE_USER/ANE_PASSWORD (el fallback existe pero está vacío).
- **`-X utf8` SIEMPRE en CLI/scripts con output** (extract-pendent reventó
  imprimiendo `\uf0b7` de una descripción; los saves se completaron igual —
  idempotente). CSV por consola: fijar `[Console]::OutputEncoding = UTF8`
  (un NEL `\x85` parte líneas y falsea conteos).
- **El filtro `--profile-compatibility` se aplica DESPUÉS de `--limit`**
  (documentado en README): límites chicos pueden devolver 0 filas aunque haya
  coincidencias más atrás.
- Launcher `jobpulse-v15.bat`: NO reinstala deps si el venv ya existe — tras
  añadir deps a pyproject hay que `python -m pip install -e .` a mano (así se
  detectó el keyring faltante).
- Venv movido: los `activate` apuntan a la ruta vieja (no se usan — siempre
  `.\.venv\Scripts\python.exe`); `pip.exe` del venv roto → usar `python -m pip`.
