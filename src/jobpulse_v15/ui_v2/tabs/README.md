# tabs (pestañas de la UI v2)

> Un módulo por pestaña. Cada pestaña es una clase `BaseTab` con `key`,
> `title`, `subtitle`, `icon` y los métodos `build(parent)`, `on_show()` y
> `refresh()`.

**Tipo:** Peanut (contrato de directorio hoja)
**Padre:** [`../README.md`](../README.md)
**Registro:** `PESTANIAS` en [`../app.py`](../app.py) — único punto de alta.

## Propósito

Encapsular la UI y las acciones de **una** función del sistema por pestaña,
componiendo los componentes de [`../widgets.py`](../widgets.py) sobre un
`TabContext` y leyendo los stores de [`../data/`](../data/README.md).

| Módulo | Clase | `key` | Qué hace |
|---|---|---|---|
| `base.py` | `BaseTab`, `TabContext` | — | Contrato base y utilidades de hilos/vigilancia de la cola. |
| `crudos.py` | `DatosCrudosTab` | `crudos` | Navegador de los avisos tal como quedaron en la base (valores crudos + panel de detalle), filtro por fuente y exportación CSV. |
| `perfil.py` | `PerfilTab` | `perfil` | Perfil del candidato: importar CV con diálogo de revisión, alta/edición manual, revertir importación y exportar CSV. |
| `vacantes.py` | `VacantesTab` | `vacantes` | Ranking ATS + ajuste técnico, filtros, detalle del desglose, "Ejecutar Paso 5", "Recalcular", "Evidencia" y exportación CSV. |
| `scraping.py` | `ScrapingTab` | `scraping` | Barrido por grupo o selección, cancelable; pipeline (Procesar / Enriquecer IA) y bitácora. |
| `cuentas.py` | `CuentasTab` | `cuentas` | Lista de sitios que piden login, formulario de credencial y alta/baja de sitios manuales. |
| `configuracion.py` | `ConfiguracionTab` | `configuracion` | Nueve tarjetas: IA local, IA externa, navegador, sondas, apariencia, cachés, retención, diagnóstico y exportaciones CSV. |

`__init__.py` re-exporta `BaseTab`, `TabContext` y las seis clases de pestaña.

## Interfaz pública

### `base.py`

| Símbolo | Contrato |
|---|---|
| `TabContext(repository, theme, services={})` | Lo que una pestaña recibe del shell. `services` es el diccionario compartido de stores y callbacks. |
| `BaseTab(context)` | Atributos de clase `key`, `title`, `subtitle`, `icon`; `__init__` guarda `context`, `theme`, `frame` y crea la cola de callbacks. |
| `BaseTab.build(parent) -> tk.Frame` | Crea el marco de la pestaña y lo asigna a `self.frame`. |
| `BaseTab.on_show() -> None` | Se llama cada vez que la pestaña pasa a ser visible. |
| `BaseTab.refresh() -> None` | Recarga los datos. |
| `BaseTab._programar(callback)` | Encola un callback para el **hilo principal**. |
| `BaseTab._lanzar_hilo(funcion)` | Arranca un worker `daemon` y activa el vigilante (`_vigilar`) con `_after`. |
| `BaseTab._after(ms, callback)` / `_vigilar()` | Programan y drenan la cola en el hilo principal. |

### `configuracion.py` — estado a nivel de módulo

- `_HANDLE_SERVIDOR` — handle del `llama-server` que **esta UI** arrancó.
- `_HANDLE_BRAVE` — handle del Brave que **esta UI** abrió.
- `TODAS_LAS_PLATAFORMAS` — valor centinela del filtro de sondas.

Ambos handles viven en el módulo (no en la instancia) para sobrevivir a la
reconstrucción en caliente del tema, que destruye la pestaña y la vuelve a
montar.

### Acciones públicas de `ConfiguracionTab`

`verificar_ia_local`, `arrancar_ia_local`, `detener_ia_local`, `probar_ia`,
`listar_modelos`, `guardar_ia`, `verificar_cdp`, `abrir_brave`, `detener_brave`,
`guardar_brave`, `activar_seleccion`, `pausar_seleccion`, `activar_todas`,
`pausar_todas`, `aplicar_paleta`, `ejecutar_diagnostico`,
`guardar_retencion`. `ScrapingTab` expone `ejecutar_grupo`,
`ejecutar_seleccion`, `cancelar`, `procesar` y `enriquecer_ia`.

## Invariantes

1. **Contrato mínimo de pestaña**: clase con `key`/`title`/`subtitle`/`icon` y
   `build`/`on_show`/`refresh`. Agregar una pestaña = módulo nuevo + una entrada
   en `PESTANIAS`; el shell, el tema y los componentes no se tocan.
2. **Un hilo nunca toca Tk.** Los workers solo llaman `_programar(...)`; el
   vigilante (`_vigilar`, programado con `marco.after`) ejecuta los callbacks
   en el hilo principal. Esto incluye leer variables Tk (`IntVar.get`,
   `Combobox.get`): se leen **antes** de arrancar el worker.
3. **Las pestañas no tocan SQLite**: usan los stores de
   [`../data/`](../data/README.md) (vía `context.services` o instanciados con
   `context.repository`).
4. **Un store compartido se pide con `services.setdefault(...)`**, para que dos
   pestañas que lo usen (p. ej. `retencion_store`) compartan la misma instancia.
5. **Un solo gestor de geometría por contenedor**; el estado vacío
   (`EmptyState`) se posiciona con el mismo gestor que el resto de ese padre.
6. **Ningún color/fuente a mano**: todo sale de `self.theme`.
7. **La retención se respeta al listar** (`crudos` y `vacantes`): ocultar, nunca
   borrar.
8. **Paso 5 es siempre corrida nueva** (`VacantesTab.ejecutar_paso5` →
   `Paso5Store.ejecutar`), con guarda previa si hay análisis obsoletos. La
   guarda es un prompt opcional de tres vías: re-analizar, continuar con los
   análisis actuales (con aviso de que puede dar `sin_requisitos`) o cancelar
   (`tabs/vacantes.py:674-676,720-753`).
9. **Política O7.3**: `ConfiguracionTab` solo detiene el servidor IA y el Brave
   que **ella** arrancó; lo que ya estaba vivo no se toca. Los botones
   "Detener" se habilitan solo si existe el handle del módulo — con el matiz de
   que el "Detener" de IA local se habilita únicamente como efecto secundario
   de `verificar_ia_local` cuando el handle ya existe
   (`tabs/configuracion.py:895-898`); `arrancar_ia_local` nunca lo habilita por
   sí mismo y solo rehabilita el botón "Arrancar"
   (`tabs/configuracion.py:931-938`).
10. **`ScrapingTab` cancela después del sitio en curso**, nunca a mitad de un
    fetch, para no dejar la corrida incompleta en la base.
11. **Privacidad antes de la IA externa**: `ScrapingTab._confirmar_ia_externa`
    pide confirmación explícita cuando el cliente configurado no es local.
12. **La contraseña nunca se carga ni se muestra** en `CuentasTab`: el campo
    arranca vacío y vacío = "conserva la guardada".
13. **Habilitación condicional en el formulario de perfil**: el estado de
    educación solo se habilita para la categoría `education` y la cantidad
    numérica solo para `experience`.
14. **Nada de Tk desde `CuentasTab`**: es síncrono (archivos JSON locales).

## Efectos secundarios

- **Base de datos**: `VacantesTab` escribe corridas de `job_match` (Paso 5) y
  `ScrapingTab` ejecuta `pipeline.ejecutar` con la tupla exacta
  `("analisis", "ia", "reanalisis", "backfill", "paso5", "evidencia")`
  (`tabs/scraping.py:410-413`) y `scraper.ejecutar_barrido`; ambos modifican
  la base apuntada por `context.repository`. **⚠ Discrepancia visible:** el
  texto auxiliar en pantalla de esa misma pestaña omite `backfill`
  ("análisis → IA → re-análisis → Paso 5 → evidencia",
  `tabs/scraping.py:136`), de modo que lo que el usuario lee no coincide con
  lo que se ejecuta.
- **Documentos generados**: `VacantesTab.generar_evidencia` escribe/verifica la
  evidencia del Paso 5 (módulo `jobpulse_v15.evidencia`) y `_texto_evidencia`
  solo la consulta.
- **Archivos de preferencias**: `ConfiguracionTab` escribe el `.env` del
  proyecto (IA y navegador), `~/.jobpulse_v15/ui_config.json` (paleta, densidad,
  idioma, `csv_dir`, retención) y borra cachés de `data/usuario/`.
- **Procesos externos**: `ConfiguracionTab` abre/detiene Brave (CDP) y
  arranca/detiene el `llama-server`; `ScrapingTab` puede hacer que
  `scraper.ejecutar_barrido` abra Brave bajo demanda.
- **Disco**: los diálogos "Exportar CSV" de `crudos`, `perfil` y `vacantes`
  escriben el archivo elegido.
- **Navegador del sistema**: "Abrir aviso en el navegador" usa `webbrowser.open`.
- **Red**: solo la que disparan el scraping, el pipeline y las acciones de IA
  (probar conexión, listar modelos).

## Dependencias

- `tkinter` / `tkinter.ttk`, `queue`, `threading`, `webbrowser`, `filedialog`,
  `messagebox`, `simpledialog`.
- Shell y capa visual: `ui_v2.tabs.base`, `ui_v2.widgets`, `ui_v2.theme`,
  `ui_v2.i18n`, `ui_v2.dialogs`, `ui_v2.configuracion`, `ui_v2.ia_providers`.
- Stores: `ui_v2.data.*` (`jobs`, `profile`, `vacantes`, `paso5`, `scraping`,
  `fuentes`, `cuentas`, `retencion`).
- Dominio: `jobpulse_v15.pipeline`, `pipeline_metricas`, `scraper`, `evidencia`,
  `diagnostico`, `caches`, `credenciales`, `ia_api`, `ia_servidor`,
  `ia_enrichment`, `browser_manager`, `analysis_flow`, `ciclo_vida`.

## Verificación

```powershell
python -m pytest tests/test_ui_v2.py -q
python -m pytest tests/ -q
```

Los tests montan las pestañas con bases temporales. Dos cuidados conocidos:

- `TestConfiguracionTab` **fija la IA local en `setUp`** (y restaura al final):
  importar `jobpulse_v15.cli` ejecuta `load_dotenv()` y carga el `.env` del
  desarrollador en `os.environ` de toda la sesión de pytest.
- Los tests que ejercitan la tarjeta de IA deben parchear
  `jobpulse_v15.ui_v2.tabs.configuracion.asegurar_servidor`; si no, arrancan el
  `llama-server` real durante la suite (saturación de RAM).

Humo de una pestaña sin ventana visible:

```powershell
python -X utf8 -c "from jobpulse_v15.ui_v2.app import crear_app; r,s=crear_app(); [r.update() for _ in range(20)]; t=s.pestana_activa(); t.refresh(); print(t.key, len(t._widgets['tabla'].get_children())); r.destroy()"
```

## Documentos relacionados

- [`../README.md`](../README.md) — shell, tema, componentes y diálogos.
- [`../data/README.md`](../data/README.md) — stores que consumen las pestañas.
- `docs/UI_V2_ARQUITECTURA.md` — capas, pestañas y patrones Tk.
- `AGENTS.md` — hilos, `-X utf8`, Paso 5 y reglas de la IA.
