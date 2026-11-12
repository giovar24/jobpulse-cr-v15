# UI v2 — arquitectura (plana y modular)

Fecha: 2026-11-02. Autor: sesión de UI v2.
Actualizado: 2026-11-03 (pestaña **Cuentas** + **Paso 5 persistido** +
tarjetas de **cachés**, **retención** y **diagnóstico**; **punto 7**: densidad
compacta/normal/amplia + **i18n es/en** con selector en Apariencia).

La **UI v2** es la única interfaz gráfica del proyecto: la **UI clásica**
(`src/jobpulse_v15/ui.py`) y sus módulos se retiraron el 2026-11-11. La UI v2
vive en `src/jobpulse_v15/ui_v2/` y trae seis pestañas (Datos crudos, Perfil,
Vacantes, Scraping, Cuentas, Configuración). El objetivo es **agregar funciones
sin comprometer lo que ya funciona**.

## Arranque

```powershell
.\jobpulse-v15-v2.bat                                   # lanzador (solo la UI v2)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15.ui_v2  # equivalente
```

## Capas (una responsabilidad por archivo)

| Módulo | Qué es | Regla |
|---|---|---|
| `ui_v2/theme.py` | `Palette`, `Metrics`, `Theme`, `apply_theme()`, `PALETAS`, `DENSIDADES` | ÚNICA fuente de color, tipografía, espaciado y **densidad** |
| `ui_v2/widgets.py` | `Card`, `StatTile`, `Badge`, `SearchField`, `FlatButton`, `EmptyState`, `ScrollFrame`, `SectionTitle`, `KeyValue` | Componentes planos reutilizables; **traducción automática** vía `i18n.t()` |
| `ui_v2/i18n.py` | `t()`, `establecer_idioma()`, `IDIOMAS`, catálogo es→en | **i18n sin Tk**; la clave es el literal en español; sin traducción → devuelve la clave |
| `ui_v2/dialogs.py` | `RevisionImportacionDialog`, `confirmar()`, `pedir_texto()` | Toplevels reutilizables; no tocan la BD |
| `ui_v2/configuracion.py` | `cargar`/`guardar` (merge), `paleta_actual`, `densidad_actual`, `idioma_actual`, `directorio_csv`, `guardar_env`, `leer_env`/`valor_env`, `puerto_cdp`, `guardar_navegador` | Persistencia **SIN Tk**: `ui_config.json` y `.env` |
| `ui_v2/data/*.py` | `JobsStore`, `ProfileStore`, `AtsStore`, `FuentesStore`, `ScrapingStore`, `CuentasStore`, `Paso5Store`, `RetencionStore` + dataclasses | **SIN Tkinter**: las pestañas no ven SQLite ni el keyring |
| `ui_v2/tabs/base.py` | `BaseTab`, `TabContext` | El CONTRATO de una pestaña (+ helpers de hilos: cola + vigilante) |
| `ui_v2/tabs/*.py` | `DatosCrudosTab`, `PerfilTab`, `VacantesTab`, `ScrapingTab`, `CuentasTab`, `ConfiguracionTab` | Composición de widgets; hablan con el store |
| `ui_v2/app.py` | `AppShell`, `crear_app()`, `main()`, `PESTANIAS` | El shell no conoce el contenido de las pestañas |

El flujo de una pestaña es: **widgets → store (dataclasses) → Repository → BD**.
Nada de SQL en las pestañas; así se testea la lógica sin abrir ventana.

## Cómo agregar una pestaña (2 pasos)

1. Crear `ui_v2/tabs/<nombre>.py`:

```python
from jobpulse_v15.ui_v2.tabs.base import BaseTab

class MiTab(BaseTab):
    key = "mi_tab"                 # id único (botón del sidebar)
    title = "Mi pestaña"           # se muestra en el sidebar y la cabecera
    subtitle = "Qué se ve aquí"
    icon = "◆"

    def build(self, parent):
        marco = super().build(parent)   # marco con el color de fondo
        # ... widgets (usar theme/widgets, nunca colores a mano) ...
        return marco

    def on_show(self):             # se llama al abrir la pestaña
        self.refresh()

    def refresh(self):
        ...
```

2. Registrarla en `PESTANIAS` (`ui_v2/app.py`).

Nada más: el shell monta/muestra/refresca; el sidebar y la cabecera se
actualizan solos.

## Patrones de Tk que esta UI arregló (ver AGENTS.md, gotchas 21–24)

- **Fuentes**: `theme.font()` devuelve `{Segoe UI} 10` (entre LLAVES). Tk parte
  la especificación por espacios: sin llaves, `Segoe UI` se lee como familia
  `Segoe` + tamaño `UI` → el texto **no se pinta** (el Treeview quedaba vacío).
- **Gestor de geometría**: no mezclar `pack` y `grid` en el mismo padre. El
  estado vacío de una tabla se posiciona con el MISMO gestor que la tabla.
- **Scrollbar**: en `yscrollcommand` solo `bar.set`; tocar el canvas ahí dentro
  produce reentrada infinita (el `scrollregion` se recalcula en `<Configure>`).
- **Componentes**: crear un widget hijo NO lo coloca; hay que `pack`/`grid`arlo
  (un `StatTile` sin empaquetar queda en 1x1, invisible).

## Estado actual de las pestañas

### Datos crudos (`tabs/crudos.py`)

Explorador de los avisos con sus valores **originales** de la fuente. Buscador,
filtro por plataforma, casilla "solo con descripción completa", franja de
resumen (total / con descripción / con ubicación / con salario / con fecha),
tabla y panel de detalle con el **texto crudo** (descripción y requisitos).
Exporta la vista a CSV (`JobsStore` → `data/jobs.py`).

### Perfil (`tabs/perfil.py`)

Datos del candidato sobre `candidate_profile_facts` (singleton: sin
`candidate_id`). Dos caminos:

- **Importar CV…** — `candidate_profile.extract_candidate_profile` lee un
  PDF/DOCX/TXT local y propone datos; un diálogo de revisión deja elegir cuáles
  guardar; se guardan como importación (revertible).
- **Alta/edición manual** — formulario con categoría, código, valor, nivel,
  estado de educación (solo `education`), cantidad/unidad (solo `experience`)
  y notas. Valida según las reglas del `Repository`.

Botones extra: **Revertir importación** (restaura manuales), **Exportar CSV**,
**Actualizar**.

> **Advertencia (capa B pendiente)**: `save_candidate_profile_facts` **no**
> escribe `codigo_canonico`, y el motor del Paso 5 exige
> `codigo_canonico IS NOT NULL` para skill/idioma/educación. Por eso un hecho
> guardado aquí puede ser **invisible para el matching** hasta que se resuelva
> la capa B (ver AGENTS.md y la migración `017`). La tabla muestra la columna
> "Canónico" para que el hueco sea visible, no oculto.

### Vacantes (`tabs/vacantes.py`)
**Ranking ATS**: puntúa cada aviso (0–100) contra el perfil y lista los más
aptos. Detalle completo en `docs/HANDOFF_SESION_2026-11-03.md`; esto es lo
que toca la arquitectura:

- El store `AtsStore` (`data/vacantes.py`) **no ve Tk**; `tabs/vacantes.py`
  arma la pestaña y la pinta.
- **Pesado en segundo plano**: el cálculo del ranking corre en un `thread` y los
  resultados vuelven por una `queue.Queue`. La UI solo se toca desde el hilo
  principal con `after` — y **el `after` va por el marco**, no por `self`
  (la pestaña NO es un widget Tk; `self.after` revienta con `AttributeError`).
- **El score ATS no se persiste**: se regenera al pedirlo ("Recalcular"); no
  hay migración ni escritura en BD.
- La fórmula, los pesos y los umbrales viven en `ats.py` (`PESOS_RANKING`,
  `UMBRALES_RANKING`), NO en la pestaña.

#### El botón "Ejecutar Paso 5" (matching persistido)

El **Paso 5 sí se persiste** y se puede correr desde la UI (antes solo por
CLI: `run_paso5.py`):

- El store `Paso5Store` (`data/paso5.py`) abre **su propia conexión**
  (`sqlite3.Row` es obligatorio: `matching` indexa por nombre de columna) y
  llama a `matching.ejecutar_paso5(...)`: una corrida **NUEVA** en
  `job_match` (las anteriores quedan con `valida = 0`).
- La casilla **"Evaluar todo"** = `aplicar_filtro_areas=False` (ignora las
  áreas marcadas en el perfil), igual que `run_paso5.py --evaluar-todo`.
- Al terminar, la columna **"Paso 5"** de la tabla se puebla sola con los
  estados de la corrida vigente (`AtsStore.estados_paso5()`), y un diálogo
  muestra el resumen `estado | motivo | n`.
- El hilo usa el patrón de `BaseTab` (`_lanzar_hilo` + `_programar`): el
  worker **nunca** toca Tk.

> El score ATS (ranking) y el Paso 5 (matching) son cosas distintas: el
> ranking no se guarda; el matching sí, en `job_match`.

### Scraping (`tabs/scraping.py`)

**Lanza un barrido desde la interfaz** (antes solo por CLI:
`run_scrapes.py`, `run_full_flow.py`, `jobpulse_v15 scrape ...`).

- La pestaña solo arma la UI; el trabajo real vive en el módulo de dominio
  **`src/jobpulse_v15/scraper.py`** (sin Tk): `ejecutar_barrido(site_ids,
  pages, port, on_progress, should_stop)` devuelve un `ResumenBarrido`.
- El store `ScrapingStore` (`data/scraping.py`) lista los sitios y sus
  **grupos de corrida** (`directos`, `cr-gov`, `cr-jobs` — los mismos del
  CLI: `scrape <plataforma> --group`).
- Solo se barren los sitios **activos**: lo que pausó la tarjeta "Sondas de
  scraping" de Configuración (`source_sites.enabled`).
- Cada sitio usa el `pages` de su `site_config` si lo tiene; si no, el de la
  casilla "Páginas".
- **Brave (O7.2)**: `scraper` abre el navegador solo si algún sitio elegido
  lo necesita y lo cierra solo si él lo abrió; el Brave del usuario no se
  toca.
- **Cancelar** termina **después** del sitio en curso (no se corta un fetch a
  medias: la corrida debe quedar consistente en `source_runs`).
- El dispatcher canónico `scrape_dispatch.construir_llamada` ahora pasa
  `skip_source_job_ids` (las ofertas descartadas a mano): el CLI ya lo
  hacía, el dispatcher no, y por eso se re-procesaba lo descartado.

### Cuentas (`tabs/cuentas.py`)

Las **credenciales de los sitios que piden login** (ANE, Indeed, LinkedIn y
todo lo que los proveedores detectaron en vivo).

- El store `CuentasStore` (`data/cuentas.py`) envuelve
  `jobpulse_v15.credenciales` (la única verdad) y devuelve dataclasses
  (`SitioCuenta`) **sin la contraseña**.
- La tabla lista: sitio, grupo, método de acceso, usuario, estado
  (con credencial / pendiente / sin credencial) y auto-login.
- El formulario edita: sitio, usuario, contraseña, método SSO, URL y nota;
  además **Agregar sitio** y **Quitar sitio** (los *seeds* del sistema —ANE,
  Indeed, LinkedIn— no se pueden quitar).
- La **contraseña nunca se lee ni se muestra**: el campo arranca vacío y
  vacío significa "conserva la que ya está guardada". Al guardar, la clave va
  al **Administrador de Credenciales de Windows** (keyring) y los metadatos a
  `data/empresas/credenciales.json` (gitignored).

Bugs del dominio corregidos al hacer la pestaña (afectan también al CLI):

| Bug | Antes | Ahora |
|---|---|---|
| `usuario=None` reventaba | `usuario.strip()` → `AttributeError` (la UI clásica pasaba `... or None`) | `upsert_credencial` normaliza (`str(usuario or "")`) |
| `tiene_credencial` siempre False con keyring | el JSON no tiene la contraseña, solo el metadato `password_almacen` | se **verifica contra el almacén** antes de decir que hay credencial |

### Configuración (`tabs/configuracion.py`)

Nueve tarjetas (una `Card` cada una), planas y sin Toplevel:

| Tarjeta | Qué configura | Dónde se guarda |
|---|---|---|
| **IA local** | Estado/arranque/detención del servidor llama.cpp (puerto 8081) | — (proceso) |
| **IA externa** | Proveedor LLM, base URL, modelo, API key y límites opt-in `IA_MAX_LLAMADAS` / `IA_RPM`; botones **Probar conexión** y **Listar modelos** | `.env` del proyecto (gitignored) |
| **Navegador (Brave / CDP)** | Ruta del ejecutable, perfil con la sesión iniciada y puerto CDP; botones **Verificar CDP**, **Abrir Brave**, **Detener Brave** | `.env` del proyecto (`BRAVE_BIN` / `BRAVE_PERFIL` / `BRAVE_CDP_PORT`) |
| **Sondas de scraping** | Activa/pausa fuentes (`source_sites.enabled`), con filtro por plataforma, selección múltiple, "todas" y aviso si no queda ninguna activa | BD (`source_sites`) |
| **Apariencia** | Esquema de color (`theme.PALETAS`: claro azul / claro verde / oscuro) | `~/.jobpulse_v15/ui_config.json` (clave `paleta`) |
| **Cachés** | Qué ocupa `data/usuario/` (caché de la IA) y botón **Limpiar** | — (disco) |
| **Retención y vigencia** | Ventana de meses (1/2/3/6/12) y si se ocultan los avisos vencidos (O8/O10) | `~/.jobpulse_v15/ui_config.json` (`retencion_puestos_meses`, `solo_vigentes`) |
| **Diagnóstico** | Integridad de la BD, calidad de los datos y huecos del enriquecimiento (botón **Ejecutar diagnóstico**) | — (solo lectura) |
| **Exportaciones CSV** | Directorio inicial de los diálogos "Exportar CSV" | `~/.jobpulse_v15/ui_config.json` (clave `csv_dir`) |

Reglas que esta pestaña respeta:

- **La configuración se guarda, no se aplica a ciegas**: `configuracion.guardar()`
  hace **cargar → update → guardar** porque ese mismo archivo lo escriben
  `ciclo_vida` y la ventana clásica (sobrescribir el dict completo perdería sus
  claves). `guardar_env()` actualiza solo las claves pedidas y preserva el
  resto de líneas/comentarios del `.env`.
- **Cambio de esquema en caliente**: la pestaña llama al servicio
  `reconstruir_ui` (`AppShell.reconstruir_con_paleta`), que destruye los
  widgets, re-aplica el tema y vuelve a montar las pestañas conservando la
  activa. `crear_app()` aplica la paleta guardada al arrancar.
- **Sondas = `source_sites.enabled`**: es la misma verdad que miran
  `Repository.select_sites()`, `run_scrapes.py` y `run_full_flow.py`; pausar
  aquí hace que la corrida no incluya esa fuente. Nada se borra.
- **O7.3 (IA local)**: el handle del servidor que ESTA UI arrancó vive en el
  **módulo** (`tabs.configuracion._HANDLE_SERVIDOR`), no en la instancia, para
  sobrevivir al rebuild; el botón "Detener" solo apaga ese handle. Un servidor
  que ya corría (arrancado a mano) **no se toca**.
- **O7.3 (navegador)**: mismo criterio para Brave: `_HANDLE_BRAVE` guarda solo
  el navegador que abrió esta UI; el que ya estaba vivo (el del usuario) no se
  toca ni se cierra. `asegurar_brave()` devuelve `None` cuando ya había CDP
  arriba.
- **Hilos**: los workers (estado de la IA, arranque, prueba de conexión, CDP)
  **no tocan Tk**: meten callbacks en una `queue.Queue` y el vigilante los
  ejecuta en el hilo principal (`after` agendado desde el hilo principal, igual
  que `VacantesTab`).

#### El puerto CDP es configurable de verdad (punto 2)

Antes `9222` estaba **escrito a mano** en `browser_manager`, `cli.py`,
`run_scrapes.py` y `run_full_flow.py`, y `BRAVE_CDP_PORT` no la leía nadie.
Ahora hay una sola fuente:

| Dónde | Cómo |
|---|---|
| `browser_manager.puerto_cdp_configurado()` | Lee `BRAVE_CDP_PORT` (entorno o `.env`); inválido o fuera de 1024–65535 → 9222 |
| `browser_manager.BraveManager` / `cdp_vivo()` / `asegurar_brave()` | Sin puerto explícito usan el configurado |
| `cli.py` (`scrape ane/linkedin/indeed --port`) | El `--port` por defecto es el configurado |
| `run_scrapes.py` / `run_full_flow.py` | Idem |
| UI v2 (tarjeta "Navegador") | Guarda en el `.env` **y** actualiza `os.environ` en el acto (`load_dotenv` no pisa lo ya presente: sin esto el cambio no rigiría hasta el reinicio) |
| Pestaña "Scraping" | La casilla "Puerto CDP" arranca con el valor configurado |

`crear_app()` carga el `.env` del proyecto al arrancar (`override=False`).
Los perfiles de Brave se detectan en disco (`User Data/*` con su archivo
`Preferences`); el desplegable los ofrece, pero el campo acepta cualquier
nombre escrito a mano.

> El `.env` y `ui_config.json` **no** son del repo: el `.env` está gitignored
> y `ui_config.json` vive en el HOME del usuario.

#### Las cachés (punto 5)

El dominio vive en `src/jobpulse_v15/caches.py` (**sin Tk**); la tarjeta de
Configuración solo lo pinta y pide confirmación.

| Caché | Dónde | Qué guarda | Coste de borrarla |
|---|---|---|---|
| **IA** | `ia_api.CACHE_DIR` (por defecto `data/usuario/ia_cache/`) | Un JSON por petición (`<hash32>.json`) | **Cuesta dinero/tiempo**: el enriquecimiento vuelve a llamar al LLM |

Reglas:

- **La caché de la IA solo se limpia por patrón**: se borran únicamente los
  archivos `[0-9a-f]{32}.json` (los que escribe `ia_api._cache_key`). Un
  archivo ajeno del usuario en esa carpeta **no se toca**.
- **La UI confirma antes de borrar** y dice qué se libera (archivos + bytes).
- **La limpieza corre en un hilo**: el worker no toca Tk; el resultado
  vuelve por la cola (`BaseTab._programar`).

> OJO (Python): el nombre de `with ... as X` **se borra** al salir del
> bloque. En los tests hay que guardar el mock en otra variable
> (`parche.start()` + `limpiar = parche.start()`) si se quiere usarlo
> después.

#### Retención y vigencia (O8/O10) — punto 6

La política de qué avisos siguen "vigentes" vive en el archivo de preferencias
del sistema (`~/.jobpulse_v15/ui_config.json`):

| Clave | Qué es | Por defecto |
|---|---|---|
| `retencion_puestos_meses` | Ventana en meses (1, 2, 3, 6 o 12) | 6 |
| `solo_vigentes` | ¿La UI oculta los avisos vencidos? | `True` |

- El store `RetencionStore` (`ui_v2/data/retencion.py`) **sin Tk** lee y
  escribe esas claves (merge: no pisa `paleta`, `csv_dir` ni las de la UI
  clásica).
- `JobsStore` (Datos crudos) y `AtsStore` (Vacantes) pasan
  `solo_vigentes` + `ventana_retencion_meses` a `Repository.search_jobs`,
  que **OCULTA** (no borra) los avisos vencidos, fuera de ventana o sin
  fecha legible.
- La misma instancia del store se comparte por los servicios del shell
  (`app.py`), así que la pestaña de Configuración y las de avisos hablan
  de la misma política.

> Ocultar **nunca** es borrar: la BD conserva todo (regla O8).

#### Diagnóstico (punto 6)

El módulo `src/jobpulse_v15/diagnostico.py` (**sin Tk**) reunion en un
informe de solo lectura las tres medidas que siempre importan:

| Fuente | Qué mide |
|---|---|
| `Database.check_integrity()` | `PRAGMA integrity_check`, `foreign_key_check` y versión del esquema |
| `ia_estado.snapshot_enriquecimiento(bd)` | Huecos (críticos/secundarios) que el pase IA podría rellenar; los "recuperables" excluyen las descripciones basura (< 200 chars) |
| `Repository.get_data_quality_summary()` | Empresa/país/ubicación sin normalizar, análisis pendiente/parcial/error, campos desconocidos/ambiguos, duplicados potenciales |

En la UI corre **en un hilo** (la BD real tiene 535 avisos) y el informe
se pinta en un `Text` de solo lectura dentro de la tarjeta
"Diagnóstico". `ia_estado.snapshot_enriquecimiento` ahora acepta la ruta
de la BD (`bd=...`) para poder medir la base que la UI tiene abierta y no
la del proyecto.

---

#### Densidad de la interfaz (punto 7a)

La UI v2 tiene tres **densidades** (compacta / normal / amplia) que cambian
el **espaciado**, el **tamaño de fuente** y las **dimensiones** de los
widgets de un solo golpe. Se guardan en `ui_config.json` (clave `densidad`)
y se aplican al arrancar (`crear_app()`) y en caliente (tarjeta
"Apariencia" → "Aplicar ahora" → `reconstruir_ui`).

| Densidad | `row_height` | `pad` | `font_scale` | Uso típico |
|---|---|---|---|---|
| **Compacta** | 24 | 12 | 0.92 | Pantallas pequeñas / mucha información |
| **Normal** | 30 | 18 | 1.00 | Defecto |
| **Amplia** | 38 | 26 | 1.10 | Accesibilidad / pantallas grandes |

Técnicamente:
- `theme.DENSIDADES` define tres `Metrics` (el `Metrics` base es "normal").
- `Theme.font(size)` y `Theme.mono(size)` aplican `font_scale` (piso 6 px).
- `apply_theme()` escala también el `padding` de los estilos ttk
  (`Flat.TButton`, `TEntry`, `TCombobox`, `Flat.Treeview`, etc.) vía
  `k = metrics.font_scale`.
- El cambio de densidad **reconstruye la app entera** (igual que el cambio
  de paleta): los widgets viejos se destruyen y los nuevos se montan con
  las métricas vigentes.

---

#### i18n español / inglés (punto 7b)

La UI v2 es **bilingüe** (es / en) con un catálogo centralizado en
`ui_v2/i18n.py`. No hay archivos `.po` ni dependencias externas.

**Cómo funciona:**
- La **clave** del catálogo es el literal **en español** tal como está
  escrito en el código; el valor es su traducción al inglés.
- `t(clave)` devuelve la traducción si el idioma vigente es `en`, y la
  **misma clave** si es `es` (o si no está en el catálogo): así una
  cadena sin traducir **nunca rompe**.
- `i18n.establecer_idioma(codigo)` fija el idioma (`es` o `en`); se lee
  de `ui_config.json` (clave `idioma`) al arrancar y al reconstruir.

**Dónde se usa `t()`:**
1. **Componentes** (`widgets.py`): `SectionTitle`, `StatTile`, `Badge`,
   `FlatButton`, `EmptyState`, `KeyValue`, `SearchField` traducen sus
   propios argumentos. Una pestaña nueva que use componentes queda
   traducida sin escribir `t()`.
2. **Texto fijo suelto** (etiquetas `tk.Label`, `ttk.Checkbutton`,
   `tree.heading`, `messagebox`, títulos de diálogo): `t("literal")` en
   el punto.
3. **Texto dinámico**: `t("{} de {} activas").format(a, b)`.

**Cobertura actual**: ~130 textos únicos en 10 archivos (`app.py`,
`dialogs.py`, `tabs/*.py`). El test `TestDensidad` + los tests de UI v2
validan que el cambio de idioma + densidad + paleta funciona en caliente.

**Selector en la UI**: tarjeta "Apariencia" → combo "Idioma" con los
nombres visibles de `IDIOMAS` ("Español" / "English"). Al pulsar
"Aplicar ahora" se guarda `idioma` + `densidad` + `paleta` y se
reconstruye la app.
