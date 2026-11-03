# UI v2 — arquitectura (plana y modular)

Fecha: 2026-11-02. Autor: sesión de UI v2.

La **UI clásica** (`src/jobpulse_v15/ui.py`, 3978 líneas) **no se toca**:
sigue siendo la interfaz completa. La UI v2 vive aparte, en
`src/jobpulse_v15/ui_v2/`, y por ahora solo trae tres pestañas (Datos crudos,
Perfil, Vacantes). El objetivo es **agregar funciones sin comprometer lo que ya
funciona**.

## Arranque

```powershell
.\jobpulse-v15-v2.bat                                   # lanzador (solo la UI v2)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15.ui_v2  # equivalente
```

## Capas (una responsabilidad por archivo)

| Módulo | Qué es | Regla |
|---|---|---|
| `ui_v2/theme.py` | `Palette`, `Metrics`, `Theme`, `apply_theme()` | ÚNICA fuente de color, tipografía y espaciado |
| `ui_v2/widgets.py` | `Card`, `StatTile`, `Badge`, `SearchField`, `FlatButton`, `EmptyState`, `ScrollFrame`, `SectionTitle`, `KeyValue` | Componentes planos reutilizables |
| `ui_v2/dialogs.py` | `RevisionImportacionDialog` (revisión de CV), `confirmar()` | Toplevels reutilizables; no tocan la BD |
| `ui_v2/data/*.py` | `JobsStore`, `ProfileStore`, `AtsStore` + dataclasses | **SIN Tkinter**: las pestañas no ven SQLite |
| `ui_v2/tabs/base.py` | `BaseTab`, `TabContext` | El CONTRATO de una pestaña |
| `ui_v2/tabs/*.py` | `DatosCrudosTab`, `PerfilTab`, `VacantesTab` | Composición de widgets; hablan con el store |
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
- **Pesado en segundo plano**: los embeddings corren en un `thread` y los
  resultados vuelven por una `queue.Queue`. La UI solo se toca desde el hilo
  principal con `after` — y **el `after` va por el marco**, no por `self`
  (la pestaña NO es un widget Tk; `self.after` revienta con `AttributeError`).
- **Nada se persiste**: el score se regenera al pedirlo ("Calcular ranking");
  no hay migración ni escritura en BD.
- La fórmula, los pesos y los umbrales viven en `ats.py` (`PESOS_RANKING`,
  `UMBRALES_RANKING`), NO en la pestaña.

> La columna **"Paso 5"** sale "—" mientras `job_match` no tenga corrida
> vigente: la UI **no persiste** el Paso 5 (solo `run_paso5.py` crea
> corridas).
