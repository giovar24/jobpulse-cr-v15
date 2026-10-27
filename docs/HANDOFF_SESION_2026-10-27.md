# Handoff — JobPulse CR v1.5 — Sesión 2026-10-27

Reemplaza como handoff vigente al de 2026-10-26
(`HANDOFF_SESION_2026-10-26.md`).

## TL;DR

- **Diagnóstico del barrido UI fallido** (el usuario reportó "solo funcionó
  ANE"): la tabla `source_run_sites` mostró que ANE/Indeed/LinkedIn fallaron
  con `ECONNREFUSED 9222` — **Brave no corría con CDP y la UI nunca lo
  arrancaba**; CINDE/Procomer SÍ corrieron (17+1, "0 nuevas" = idempotencia
  normal, no error).
- **O7 creado e implementado en la misma sesión** (operación UI-first /
  servidores bajo demanda): el barrido de la UI abre/cierra Brave solo;
  botón **"Enriquecer"** (servidor IA sube, enriquece, se apaga); botón
  **"Re-login ANE"** en el diálogo de Corrida; el launcher ya no pre-arranca
  la IA. En el camino se encontró y corrigió el **bug histórico del perfil
  vacío vivo en `BraveManager`** (`User Data\Default` en vez de la raíz).
- **Incidente de tests**: el pase IA de CV arrancó el llama-server REAL en
  plena suite (saturación de RAM — el usuario lo notó). Fix: patch de
  `asegurar_servidor` en los tests (gotcha 12 de AGENTS.md). Suite final:
  **244 tests + 46 subtests en ~28s**, cero spawns de modelo.
- **Motor semántico (embeddings) verificado y DORMIDO por decisión del
  usuario**: funciona tras la mudanza (EmbeddingGemma gated → fallback
  `paraphrase-multilingual-mpnet`), pero está sin cablear y sin caché. El
  usuario decidió **data-first**: la precisión de búsqueda viene de la data
  extraída (O1), no del vector. **O2 redefinido** en consecuencia.
- **O5.4 CERRADO + O1 COMPLETO (continuación de la sesión)**: dedupe ANE
  resuelto por **huella de descripción** (en ANE el nombre de empresa puede
  ser "Confidencial" — la identidad es la descripción): solo 4/120 del lote
  nuevo eran republicaciones → 4 viejas `dismissed` con nota; grupos
  INAMU/SALESLAND = plazas múltiples (decisión del usuario). Y el pase de
  enriquecimiento corrió 44 min con el servidor IA **bajo demanda E2E**
  (subió → 125/166 enriquecidos → se apagó solo). Skills 100%, city 91.9%,
  work_mode 53.6% (resto = honesto/basura O5.3).
- **Objetivos O8 (ciclo de vida de la vacante) + O9 (optimización de UI)
  formalizados al cierre, con decisión del usuario**: recurrentes y aplicadas
  OCULTAS por defecto (visibles solo con filtro opt-in); marcar aplicado =
  manual. Estado del código investigado: registro de aplicados YA existía
  (tabla `applications` + diálogo Seguimiento); NO hay categorías de puestos,
  NADA caduca, y las republicaciones resucitan (estado pegado al ID viejo).
  O2 ganó O2.1 (normalizar locations Indeed) y O2.2 (filtro requisitos +
  columna Req.); O6 ganó O6.4 (dedupe semántico del perfil).

## 1. Lo que se hizo

### Diagnóstico del barrido desde la UI (reporte del usuario)
- Consulta a `source_run_sites`: corridas 04:02 y 04:43 del 27-10 —
  ane/indeed/linkedin `error ECONNREFUSED ::1:9222`; cinde/procomer `ok`
  con 0 nuevas (todo duplicado). El barrido ANE que "sí funcionó" fue el
  del 26-10 23:54 vía CLI tras `login_ane.py`.
- Causa raíz: la UI solo pasa `port` a los fetchers; nadie garantiza CDP.
  Además `BraveManager._get_user_data_dir()` devolvía `User Data\Default`
  (el bug histórico de SITIOS_PROBLEMATICOS.md) — el botón "Login manual"
  y el CLI `login` abrían un perfil VACÍO; lo enmascaraba `login_ane.py`
  (teclea credenciales frescas).

### O7 — Operación UI-first (implementado completo)
| Sub | Qué | Dónde |
|---|---|---|
| O7.1 | Fix perfil: `--user-data-dir` a la RAÍZ `User Data` + `--profile-directory={perfil}`; `stop_brave_sync()`, `cdp_vivo()`, `asegurar_brave()` (devuelve manager SOLO si él abrió), `PLATAFORMAS_NAVEGADOR` | `browser_manager.py` |
| O7.2 | `_ejecutar` (diálogo Corrida): pre-verifica CDP si hay sitios de navegador, abre Brave si falta, lo cierra en `finally` SOLO si ella lo abrió; aviso claro si el Brave diario (sin CDP) bloquea el puerto | `ui.py` |
| O7.3 | `jobpulse_v15/ia_servidor.py` (NUEVO, única fuente del comando llama-server): `servidor_arriba()`, `asegurar_servidor()`, `ServidorIA.detener()` — solo apaga lo que él encendió. Botón **"Enriquecer"** en la UI con diálogo de progreso; orquestación compartida `ia_enrichment.pase_completo()` (ciclos críticos + pase completo, `on_event` para logs/UI); pase IA de CV con servidor bajo demanda; `jobpulse-v15.bat` sin pre-arranque de IA | `ia_servidor.py`, `ui.py`, `ui_perfil.py`, `ia_enrichment.py`, `run_enriquecimiento.py` |
| O7.4 | `jobpulse_v15/ane_login.py` (NUEVO): login ANE con credencial del almacén, `{"estado", "detalle"}`; botón **"Re-login ANE"** en la Corrida; `login_ane.py` queda como wrapper CLI (abre/cierra Brave solo si hace falta; margen de 3s tras login OK para persistir la cookie) | `ane_login.py`, `ui.py`, `login_ane.py` |

### Verificación del motor semántico (pregunta del usuario)
- `search_engine.py` importa y funciona tras la mudanza (torch OK): modelo
  carga en ~60s la primera vez; **EmbeddingGemma-300m es GATED en HF (401)**
  → fallback automático a `paraphrase-multilingual-mpnet-base-v2` (768d).
- Similitud correcta: sim("soporte técnico","IT support")=0.498 vs
  sim("soporte técnico","chef")=0.222.
- PERO: sin cablear (nadie importa `ats.py`/`gate.py`/`ia_calibracion.py`),
  sin tests propios, y `data/usuario/embeddings_cache.npy` NO EXISTE (nunca
  se indexaron los jobs, ni antes de la mudanza).
- Respuesta técnica al usuario: los embeddings NO extraen (solo comparan);
  clasificación por anclas es viable para 2-3 campos con umbral, pero la
  extracción real es de la IA local. El usuario decidió: **data-first** —
  completar O1 (huecos → filtros SQL exactos) antes que cualquier ranking;
  motor semántico dormido (nicho futuro: texto libre ES↔EN). O2 redefinido.

### Tests
- NUEVOS: `test_browser_manager.py` (raíz User Data, args, cdp_vivo,
  asegurar_brave, stop_brave_sync), `test_ia_servidor.py` (health stub,
  asegurar None si arriba, fallo rápido sin llama-server, externo nunca
  local, comando usa puerto del env, detener idempotente),
  `test_ane_login.py` (guardas de credencial, selectores estables),
  `TestPaseCompleto` en `test_ia_enrichment.py` (ciclos, solo_criticos,
  error acumulado).
- FIX de tests existentes: los 2 tests del pase IA de CV en `test_ui.py`
  ahora parchean `jobpulse_v15.ui_perfil.asegurar_servidor` (return None).
- **Suite: 244 passed + 46 subtests en ~28s**, sin cargar ningún modelo real.

### Docs verificadas contra el código
`AGENTS.md` (gotchas 11-13, regla de oro Brave, botón Re-login ANE, 244
tests, estado de sesión), `DESARROLLO_v15.md` (tabla O1-O7 canónica, O2
redefinido, §5 reordenado), `SITIOS_PROBLEMATICOS.md` (bug BraveManager
CORREGIDO; nota ECONNREFUSED desde la UI), `IA_ENRIQUECIMIENTO.md` (modo
"bajo demanda"), `README.md` (launcher sin IA).

### Formalización de objetivos O8/O9 (cierre de sesión)

El usuario recordó un plan previo (puestos recurrentes, guardado de
aplicados, de-baja por tiempo) y pidió agregarlo a los objetivos, porque no
conocía el estado actual. Investigación del código:

| Pieza pedida | Estado real |
|---|---|
| Guardar los puestos aplicados | ✅ YA existente: tabla `applications` (planned → applied → recruiter_contact → interview → offer; applied_at, next_action_at, notas) + diálogo "Seguimiento" por vacante (ui.py) |
| Anotar que ya se aplicó | ✅ manual: diálogo de estado ("Aplicada") con skip_automatic=True por defecto → ya excluye de la búsqueda |
| Categorías de puestos | ❌ no existe ningún campo (solo categorías de REQUISITOS: education/experience/language/license/skill) |
| Recurrentes vs. ya aplicado | ❌ la republicación nace con ID nuevo; el estado manual del ID viejo NO se arrastra → la copia resucita |
| De-baja después de un tiempo | ❌ NADA caduca: la búsqueda no filtra por edad ni vigencia; `expires_at` existe pero solo lo llena ANE y `gate.es_vigente` está dormido |

Decisión del usuario (27-10): **puesto recurrente NO sale salvo que el
usuario decida mostrarlo** (vale también para lo ya aplicado: "solo se
muestran si el usuario lo desea"); **marcar aplicado siempre es MANUAL**.
Refinamiento posterior del mismo día (ejemplo Concentrix, 8 vacantes que
republica constantemente): el match es **por compañía + descripción**, no
por título — O5.4 mostró 13 coincidencias solo-título que NO eran
republicaciones; una copia nueva que coincida (huella exacta o ratio ≥
~0.92) con algo ya revisado/aplicado HEREDA el estado al ingest (nace
oculta + nota de herencia; datos intactos, distinto del automerge
prohibido). Margen incierto → quality duplicates.
La ocultación de recurrentes NO es perpetua: **ventana temporal definida
por el usuario en la pestaña de Configuración** (selector 1/2/3/6 meses…,
decisión del usuario 27-10; ancla = updated_at del estado del original —
existe en user_job_state): la copia solo hereda estado si el original
tiene MENOS de la ventana; superada, la copia entra como vacante NUEVA
(nuevo ciclo, re-aplicable). Default del selector por decidir (prop. 3
meses).
→ Creado objetivo **O8** (O8.1 categorías · O8.2 recurrentes/aplicadas
ocultas por defecto · O8.3 registro de aplicados ✅ · O8.4 de-baja por
tiempo) y placeholder **O9** (optimización de UI). Además: O2 gana
**O2.1** (normalizar locations de Indeed) y **O2.2** (filtro "solo con
requisitos obligatorios" + columna "Req.", aprobado hace tiempo y
pospuesto); O6 gana **O6.4** (dedupe semántico del perfil, slugs ES/EN).

## 2. Decisiones de diseño

1. **Política de servidores bajo demanda**: "solo se detiene lo que la app
   arrancó". Si Brave o el servidor IA ya estaban arriba (usuario/launcher),
   se usan y NO se tocan. Evita matar el navegador diario del usuario.
2. **`ia_servidor.py` como única fuente del comando llama-server** (dentro
   del paquete); `start_ia_server.py` queda como wrapper CLI. Una sola
   verdad para CLI, UI y scripts.
3. **`pase_completo()` compartido CLI/UI** en `ia_enrichment.py`: misma
   orquestación para `run_enriquecimiento.py` y el botón "Enriquecer"
   (`on_event` para progreso; `load_dotenv()` propio porque el proceso UI
   no carga `.env`).
4. **`ane_login.py` al paquete** (login_ane.py = wrapper): el flujo del
   usuario es 100% UI; los scripts de raíz quedan para sesiones de agente.
5. **Embeddings dormidos, no borrados**: verificados funcionales; borrar
   obligaría a redefinir O2/O4 y perdería el nicho ES↔EN. `torch`/`sentence-
   transformers` se quedan instalados.
6. **O2 redefinido por el usuario**: afinar la búsqueda = completar la data
   (O1) → filtros SQL más exactos. La optimización de UI va DESPUÉS de eso.
7. **Tras login ANE OK, 3s de margen** antes de cerrar Brave (cookie de
   sesión persista en el perfil pese al terminate forzado).
8. **Enrichment con reglas primero, IA después** ya existe de facto
   (`rules-1` + `ia_enrichment`); el pre-pase semántico (Alt 2) quedó
   descartado por ahora.

## 3. Objetivos (estado)

| Objetivo | Estado |
|---|---|
| O1 Enriquecimiento IA | ✅ **COMPLETO (27-10, 44 min, servidor bajo demanda E2E)**: 125/166; skills 100%, date 100%, region 95.6%, employment_type/languages 95.3%, city 91.9%; work_mode 137 'unknown' (46 basura O5.3 + 91 honestos); salary_raw 117 = fuente sin texto |
| O2 Afinar la búsqueda | 🟡 **redefinido (data-first)**: motor semántico DORMIDO; alcance operativo — **O2.1** normalizar locations de Indeed · **O2.2** filtro "solo con requisitos obligatorios" + columna "Req." (aprobado, estaba pospuesto) |
| O3 Validar 7 fetchers ATS | ⏳ no iniciado |
| O4 Calibración gate-vs-IA | ⏳ redefinir (sin gate semántico no tiene contra-qué comparar) |
| O5 Higiene | 🟢 O5.1 ✅ · **O5.4 ✅ CERRADO (27-10)**: 4/120 republicaciones (huella = descripción) → 4 viejas `dismissed` con nota; INAMU/SALESLAND = plazas múltiples (usuario); queda **O5.3**: ~46 jobs con descripción basura |
| O6 Perfil candidato | 🟢 O6.1/O6.2 ✅ · sigue O6.3 matching afinado · **O6.4** dedupe semántico del perfil (slugs ES/EN, decisión import vs diálogo) |
| **O7 Operación UI-first** | ✅ **COMPLETO (2026-10-27)** — falta solo la prueba de humo del usuario |
| **O8 Ciclo de vida de la vacante** | 🔵 **creado 27-10** (plan previo del usuario): O8.1 categorías ❌ · O8.2 recurrentes+aplicadas OCULTAS por defecto con opt-in (decisión 27-10) · O8.3 registro de aplicados ✅ YA existía · O8.4 de-baja por tiempo ❌ — pendiente decidir ventana (¿60/90 días?) y taxonomía |
| **O9 Optimización de UI** | ⏳ placeholder — alcances por definir tras O2-redefinido |

## 4. Pendiente inmediato en la próxima sesión

1. **Prueba de humo del usuario** (cierra O7): abrir la UI → "Ejecutar
   barrido" (Brave abre/cierra solo; de paso refresca las ~46 descripciones
   basura si la sesión ANE vive) → "Enriquecer" (con la BD llena es casi
   instantáneo por caché) → si ANE dice "sin sesión": "Re-login ANE".
2. **O5.3** (re-barrido de los ~46 jobs con descripción basura —
   login-wall; vía UI).
3. **O8 Ciclo de vida** (nuevo): recurrentes y aplicadas ocultas por
   defecto (opt-in para verlas); aplicado = manual; copia republicada
   hereda el estado por compañía + huella de descripción (exacta o ratio
   ≥ ~0.92; margen incierto → quality duplicates); ventana temporal
   configurable en Configuración (1/2/3/6 meses…). Falta decidir: default
   de la ventana (prop. 3 meses), de-baja de viejos (O8.4) y taxonomía
   O8.1.
4. **O2-redefinido**: **O2.1** normalizar locations de Indeed · **O2.2**
   filtro "solo con requisitos obligatorios" + columna "Req.".
5. **O6.3** matching · **O6.4** dedupe semántico del perfil (import vs
   diálogo). Luego **O9** (UI, por definir), O3, O4.

## 5. Cómo retomar (comandos)

```powershell
cd D:\Proyectos\v1_5

# Launcher (venv + Brave CDP + UI; la IA ya NO se pre-arranca)
.\jobpulse-v15.bat

# Flujo de humo desde la UI (sin CLI):
#   "Ejecutar barrido" → abre/cierra Brave solo
#   "Enriquecer"       → servidor IA bajo demanda (sube/pasa/apaga)
#   "Re-login ANE"     → en el diálogo de Corrida, si la sesión caducó

# Suite (pytest del sistema; 244 tests)
python -X utf8 -m pytest tests/ -q

# Duplicados ANE para revisión manual (O5.4)
.\.venv\Scripts\python.exe -m jobpulse_v15 quality duplicates --limit 100

# Diagnóstico BD tras el enriquecimiento
.\.venv\Scripts\python.exe tools\progreso_enriquecimiento.py
```

## 6. Archivos clave

| Archivo | Qué |
|---|---|
| `src/jobpulse_v15/browser_manager.py` | FIX O7.1 (raíz `User Data` + `--profile-directory`) + `cdp_vivo`/`asegurar_brave`/`stop_brave_sync`/`PLATAFORMAS_NAVEGADOR` |
| `src/jobpulse_v15/ia_servidor.py` | NUEVO: ciclo de vida del servidor IA (única fuente del comando) |
| `src/jobpulse_v15/ane_login.py` | NUEVO: login ANE con credencial del almacén (selectores probados en producción) |
| `src/jobpulse_v15/ui.py` | `_ejecutar` con Brave auto-gestionado (try/finally); botones "Enriquecer" y "Re-login ANE"; `open_enriquecimiento` |
| `src/jobpulse_v15/ui_perfil.py` | Pase IA de CV con servidor bajo demanda (`asegurar_servidor` inyectable para tests) |
| `src/jobpulse_v15/ia_enrichment.py` | `pase_completo()` compartido CLI/UI |
| `run_enriquecimiento.py` / `start_ia_server.py` / `login_ane.py` | Wrappers refactorizados sobre el paquete (mismos contratos CLI) |
| `jobpulse-v15.bat` | Sin pre-arranque de IA (3 pasos) |
| `tests/test_browser_manager.py`, `test_ia_servidor.py`, `test_ane_login.py`, `TestPaseCompleto` | NUEVOS/extendidos — herméticos (sin navegador ni modelo) |
| `AGENTS.md` | Gotchas 11-13; regla de oro Brave actualizada; 244 tests; estado de sesión |
| `DESARROLLO_v15.md` | Tabla O1-O7 canónica (O2 redefinido); §2/§5 al día |
| `docs/SITIOS_PROBLEMATICOS.md` | Bug de perfil marcado CORREGIDO en BraveManager |
| `docs/IA_ENRIQUECIMIENTO.md` | Modo "bajo demanda" (O7.3) |

## 7. Datos de contexto que no hay que olvidar

- **BD enriquecida (27-10)**: 295 jobs (ANE 240 = 120 lote 25-10 + 120 lote
  26-10 con solo 4 republicaciones — las 4 viejas `dismissed`; Indeed 30,
  CINDE 17, LinkedIn 7, Procomer 1). Estado de campos tras O1: city faltan 24
  (mayoría remotos o lat_raw Indeed sin normalizar), region 13, work_mode
  'unknown' 137 (46 basura O5.3 + 91 honestos), employment_type 14, skills 0,
  languages 14, salary_raw 117 = fuente sin texto (irrecuperable).
- **El barrido de hoy 04:43 no agregó nada** (0 nuevas — todo duplicado);
  el ANE que "funcionó" fue el re-barrido CLI del 26-10.
- **llama-server consume ~4GB de RAM** (máquina: 15.4GB, ~10GB libres tras
  el reinicio). La política "apagar al terminar" evita acumulación; el
  usuario pidió explícitamente reiniciar/limpiar entre corridas.
- **El modelo de embeddings mpnet (~470MB) quedó descargado en la caché HF**
  del usuario tras la verificación — fuera del repo, no molesta.
- **EmbeddingGemma-300m es gated** en HF: si algún día se quiere usar,
  `huggingface-cli login` con cuenta que aceptó la licencia; hoy el fallback
  mpnet funciona sin login.
- **Los fetchers conectan a `http://localhost:{port}`** (ane/indeed/linkedin/
  browser_sites) mientras `BraveManager` usa `127.0.0.1` — Node prueba ambas
  familias, funciona igual; no es fuente de problemas conocida.
- **`configuration_window.py` "Login manual"** ya abre el perfil REAL tras el
  fix O7.1 (antes abría el perfil vacío del bug).
- La rama `fork-v15` del repo viejo sigue SIN pushear (password ANE
  pre-purga). Rotación de password ANE: pendiente del usuario.
