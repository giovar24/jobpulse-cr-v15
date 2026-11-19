# ui_v2

> Interfaz gráfica Tkinter de JobPulse CR v1.5: única UI del proyecto, plana
> (sin relieve ni sombras) y modular (una pestaña = un módulo).

**Tipo:** Peanut (contrato de directorio con hijos)
**Hijos:** [`data/`](./data/README.md) · [`tabs/`](./tabs/README.md)
**Punto de entrada:** `python -m jobpulse_v15.ui_v2` (o `jobpulse-v15-v2.bat`)

## Propósito

Exponer una interfaz de escritorio para operar el pipeline de JobPulse CR
v1.5: revisar avisos crudos, mantener el perfil del candidato, rankear
vacantes (ATS + ajuste técnico), ejecutar barridos y el pipeline completo,
gestionar cuentas con login y configurar IA, navegador, sondas, apariencia,
cachés, retención y diagnóstico.

El directorio se organiza en tres capas sin ciclos:

| Capa | Qué es | Regla |
|---|---|---|
| Raíz (`app`, `theme`, `widgets`, `dialogs`, `i18n`, `configuracion`, `ia_providers`) | Shell, sistema de diseño, componentes, diálogos, i18n y persistencia de preferencias | Sin lógica de negocio ni SQL |
| [`data/`](./data/README.md) | Stores **sin Tk** que devuelven dataclasses planas | Prohibido importar `tkinter` |
| [`tabs/`](./tabs/README.md) | Una clase `BaseTab` por pestaña | No habla con SQLite; usa los stores |

**Nota sobre `data/`:** la mayoría de los stores envuelven `Repository`, pero
`data/cuentas.py` (`CuentasStore`) y `data/retencion.py` (`RetencionStore`)
**no reciben ningún `Repository`**: envuelven los módulos de dominio
`credenciales` y `ciclo_vida` más el archivo de preferencias.

La UI clásica (`ui.py`) y sus módulos se retiraron el 2026-11-11: este paquete
es la única interfaz gráfica.

## Interfaz pública

### Entrada y shell — `app.py`

| Símbolo | Contrato |
|---|---|
| `PESTANIAS: tuple[Type[BaseTab], ...]` | Registro **único** de pestañas, en orden de aparición. Agregar una pestaña = un módulo en `tabs/` + una entrada aquí. Orden actual: `DatosCrudosTab`, `PerfilTab`, `VacantesTab`, `ScrapingTab`, `CuentasTab`, `ConfiguracionTab`. |
| `AppShell(root, repository, *, theme=None, pestanias=PESTANIAS)` | Construye sidebar, cabecera y área de contenido; instancia todas las pestañas y el `TabContext` compartido. |
| `AppShell.mostrar(indice) -> None` | Monta (la primera vez) y muestra la pestaña `indice`. |
| `AppShell.refrescar() -> None` | Pide `refresh()` a la pestaña activa. |
| `AppShell.reconstruir_con_paleta(nombre) -> None` | Destruye todos los widgets del `root` y vuelve a montar la app con la paleta `nombre`, conservando la pestaña activa y los stores del contexto. |
| `AppShell.pestana_activa() -> BaseTab \| None` | Instancia de la pestaña visible. |
| `crear_app(root=None, database_path=None, *, pestanias=PESTANIAS)` | Crea `Database` + `Repository`, aplica paleta/densidad guardadas y devuelve `(root, shell)`. |
| `main() -> int` | `crear_app()` + `mainloop()`; devuelve `0`. |

`__init__.py` re-exporta únicamente `AppShell`, `crear_app` y `main`.
`__main__.py` llama `main()`.

Servicios que el shell inyecta en `TabContext.services` (contrato compartido
entre pestañas):

- `retencion_store` — instancia **única** de `RetencionStore` compartida por
  `jobs_store`, `ats_store` y `ConfiguracionTab`.
- `jobs_store`, `profile_store`, `paso5_store`.
- `reconstruir_ui` — callback hacia `AppShell.reconstruir_con_paleta`.
- `refrescar_todo` — callback hacia `AppShell.refrescar` (lo usa `ScrapingTab`
  al terminar el pipeline, porque el Paso 5 cambió `job_match`).

### Sistema de diseño — `theme.py`

| Símbolo | Contrato |
|---|---|
| `Palette` (frozen dataclass) | Colores nombrados (`bg`, `surface`, `accent`, `danger`, `sidebar_*`, `selection`, `row_alt`, …). |
| `Metrics` (frozen dataclass) | Medidas en px (`sidebar_width`, `header_height`, `row_height`, `radius`, `pad`, `gap`, `detail_width`, `font_family`, `font_mono`, `font_scale`). |
| `Theme(palette, metrics, styles)` | `color(nombre)`, `font(size, weight)`, `mono(size)`, `escalar(size)`. |
| `PALETAS` / `NOMBRES_PALETA` / `PALETA_DEFECTO` | Paletas `claro_azul`, `claro_verde`, `oscuro`; defecto `claro_azul`. |
| `DENSIDADES` / `NOMBRES_DENSIDAD` / `DENSIDAD_DEFECTO` | Densidades `compacta`, `normal`, `amplia`; defecto `normal`. |
| `paleta_por_nombre(nombre)` / `metrics_por_nombre(nombre)` | Nombre desconocido → valor por defecto (nunca excepción). |
| `apply_theme(root, palette=None, metrics=None) -> Theme` | Configura `ttk` (tema `clam`), fuentes por defecto y estilos `Flat.*`, `Accent.*`, `Ghost.*`, `Sidebar.*`, `Surface.*`, … y devuelve el `Theme`. |

### Componentes reutilizables — `widgets.py`

`Card`, `SectionTitle`, `StatTile`, `Badge`, `SearchField`, `FlatButton`,
`EmptyState`, `ScrollFrame`, `KeyValue` y la función `separador(parent, theme)`.
Cada constructor recibe `theme` y argumentos planos; `SectionTitle`, `StatTile`,
`Badge`, `FlatButton`, `EmptyState`, `SearchField` **y `KeyValue`**
**traducen sus propios textos** (`t()`), de modo que una pestaña nueva hereda
estilos e i18n sin tocar tema ni catálogo.

### Diálogos — `dialogs.py`

| Símbolo | Contrato |
|---|---|
| `RevisionImportacionDialog.mostrar(parent, theme, importacion)` | Muestra modal y devuelve la lista de hechos seleccionados o `None` si se cancela. |
| `confirmar(parent, titulo, mensaje) -> bool` | Confirmación sí/no. |
| `pedir_texto(parent, titulo, mensaje, valor_inicial="", *, password=False) -> str` | Pide una línea; `""` si se cancela. |

### i18n — `i18n.py`

La **clave del catálogo es el literal en español** tal como aparece en el
código; el valor es su traducción al inglés. `t(clave, **sustituciones)`
devuelve la traducción si el idioma vigente es `en`, y la misma clave en `es` o
si falta el término (nunca rompe una cadena). Estado de módulo: `idioma_actual()`,
`establecer_idioma(nombre)`, `catalogo()` (copia para tests), `IDIOMAS`,
`IDIOMA_DEFECTO = "es"`.

### Preferencias persistentes — `configuracion.py` (sin Tk)

- `ARCHIVO = ~/.jobpulse_v15/ui_config.json` — claves de la UI v2: `paleta`,
  `densidad`, `idioma`, `csv_dir`.
- `ENV = <repo>/.env` — clave del proyecto (gitignored).
- Lectura/escritura: `cargar`, `guardar` (solo preferencias JSON),
  `paleta_actual`, `densidad_actual`, `idioma_actual`, `directorio_csv`.
- Entorno: `ruta_env`, `cargar_env`, `leer_env`, `valor_env`, `guardar_env`
  (escribe el `.env`), `puerto_cdp`, `guardar_navegador` (`BRAVE_BIN` /
  `BRAVE_PERFIL` / `BRAVE_CDP_PORT`).
  **Dos escritores distintos**: `guardar` → `~/.jobpulse_v15/ui_config.json`;
  `guardar_env` / `guardar_navegador` → el `.env` del proyecto.

### Proveedores de IA — `ia_providers.py`

`IA_PROVIDERS` / `proveedores_ia()`: adaptación de `jobpulse_v15.ia_api.PRESETS`
a la forma que consume `ConfiguracionTab` (`nombre`, `base_url`, `modelo_def`).
La fuente única de los presets sigue siendo `ia_api.PRESETS`.

## Invariantes

1. **El shell no conoce el contenido de las pestañas**: solo las instancia, las
   monta/oculta y les pide `on_show()` / `refresh()`.
2. **Registro único**: toda pestaña nueva se declara en `PESTANIAS` (`app.py`).
   No hay otro punto de registro.
3. **Fuente única del diseño**: ningún color, fuente ni espaciado se escribe a
   mano en una pestaña; todo sale de `Theme`/`Metrics` y los componentes.
4. **Las pestañas no tocan SQLite**: usan los stores de `data/`.
5. **Un hilo nunca toca Tk**: los workers encolan callbacks (`BaseTab._programar`)
   y el vigilante los ejecuta en el hilo principal.
6. **Un solo gestor de geometría por contenedor** (nunca `pack` y `grid` en el
   mismo padre) y los `tk.Text` de solo lectura usan `state="disabled"`.
7. **Fuentes con espacio van entre llaves** (`{Segoe UI} 10`): sin llaves Tk
   parte la especificación y falla con `expected integer but got 'UI'`.
8. **Idioma es estado de módulo** (`i18n._idioma`): cambiarlo exige reconstruir
   la app entera; no se traduce nada en caliente widget a widget.
9. **Cargar → update → guardar** al escribir `ui_config.json`
   (`configuracion.guardar`): sobrescribir el dict completo perdería claves de
   otros módulos que comparten el archivo.
10. **Un nombre de paleta o densidad desconocido cae al valor por defecto**; las
    funciones de `theme`/`configuracion` no lanzan excepción por un valor basura.

## Efectos secundarios

- `crear_app()` **carga el `.env` del proyecto** (`override=False`: lo que el
  usuario exportó en la sesión manda) y **crea/migra la base** vía
  `Database().initialize()` antes de montar cualquier widget.
- `configuracion.guardar` **escribe** `~/.jobpulse_v15/ui_config.json`, y
  `configuracion.guardar_env` / `guardar_navegador` escriben el `.env` del
  proyecto (crean el directorio padre si falta).
- `guardar_navegador` escribe el `.env` **y actualiza `os.environ` en el acto**
  (el `.env` no vuelve a mandar hasta el próximo arranque).
- `AppShell.reconstruir_con_paleta` **destruye todos los hijos del `root`** y
  remonta las pestañas; el estado que debe sobrevivir se guarda en el módulo
  (por ejemplo los handles de servidor IA y Brave en `tabs/configuracion.py`).
- Las pestañas de Vacantes y Scraping **escriben en la base** (corridas de
  `job_match`, filas de `pipeline_etapa`) y generan documentos de evidencia;
  `ScrapingTab` abre Brave bajo demanda y lo cierra solo si él lo abrió.
- Los diálogos `Exportar CSV` **escriben archivos** en disco.

## Dependencias

- `tkinter` / `tkinter.ttk` (stdlib) — el paquete no define entrypoint en
  `pyproject.toml`: se lanza con `python -m jobpulse_v15.ui_v2`.
- `jobpulse_v15.db.Database` y `jobpulse_v15.repository.Repository` — shell y stores.
- `jobpulse_v15.ia_api.PRESETS` — presets de proveedores; las pestañas también
  usan `jobpulse_v15.ia_api.IAClient` (`tabs/configuracion.py`) y
  `jobpulse_v15.ia_enrichment` (`tabs/scraping.py`).
- Módulos de dominio consumidos por las pestañas (nunca por el shell):
  `pipeline`, `pipeline_metricas`, `scraper`, `analysis_flow`, `evidencia`,
  `diagnostico`, `caches`, `ciclo_vida`, `browser_manager`, `ia_servidor`.
- Módulos de dominio consumidos **solo por la capa `data/`** (no por ninguna
  pestaña): `matching`, `ats`, `viabilidad`, `areas`, `candidate_profile`,
  `credenciales`.
- Subpaquetes propios: [`data/`](./data/README.md) y [`tabs/`](./tabs/README.md).

## Verificación

Desde la raíz del repo (pytest vive en el **python del sistema**, no en el venv):

```powershell
python -m pytest tests/ -q
```

Un archivo concreto o un patrón:

```powershell
python -m pytest tests/test_ui_v2.py -q
python -m pytest tests/ -k ui_v2 -q
```

Humo sin abrir ventana visible (monta la app y refresca la primera pestaña; la
suite crea bases temporales y no requiere red ni credenciales):

```powershell
python -X utf8 -c "from jobpulse_v15.ui_v2.app import crear_app; r,s=crear_app(); [r.update() for _ in range(20)]; t=s.pestana_activa(); t.refresh(); print(t.key, len(t._widgets['tabla'].get_children())); r.destroy()"
```

Notas de prueba: los tests que importan `jobpulse_v15.cli` cargan el `.env` del
desarrollador en `os.environ` (el CLI hace `load_dotenv()` al importarse); un
test que dependa del entorno debe **fijarlo** en `setUp`, no confiar en el
`.env` real. Los tests del cliente IA deben parchear
`jobpulse_v15.ui_v2.tabs.configuracion.asegurar_servidor` para no arrancar el
`llama-server` real durante la suite.

## Documentos relacionados

- [`data/README.md`](./data/README.md) — capa de datos sin Tk.
- [`tabs/README.md`](./tabs/README.md) — contrato de las pestañas.
- `docs/UI_V2_ARQUITECTURA.md` — capas, pestañas y patrones Tk.
- `AGENTS.md` — gotchas de Tk y comandos de verificación del repo.
