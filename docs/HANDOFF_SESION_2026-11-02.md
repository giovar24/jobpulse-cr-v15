# Handoff — Sesión 2026-11-02: **UI v2 (plana y modular) — Datos crudos + Perfil**

## TL;DR

El usuario pidió **una UI nueva, plana y modular** ("el que tenemos no funciona
muy bien"), **sin quitar la anterior**, pensada para *agregar funciones sin
comprometer lo que ya funciona*; por ahora solo una pestaña con **datos
crudos**. Después pidió el **siguiente paso: el módulo del perfil del usuario
junto con las opciones para ingresar los datos**.

Se entregó, en un paquete nuevo `src/jobpulse_v15/ui_v2/` (la UI clásica
`ui.py` **queda intacta**):

- **Shell** (sidebar + cabecera + contenido) con un **registro de pestañas**
  (`PESTANIAS`): agregar una pestaña = un módulo nuevo + una línea.
- **Pestaña "Datos crudos"**: avisos con sus valores originales (ubicación y
  salario crudos, texto crudo de descripción y requisitos), buscador, filtro
  por fuente, franja de resumen y export CSV.
- **Pestaña "Perfil"**: **importar CV** (PDF/DOCX/TXT → propuesta de datos →
  diálogo de revisión → importación revertible) y **alta/edición manual** de
  hechos del perfil (`candidate_profile_facts`).
- Lanzador `jobpulse-v15-v2.bat`; doc `docs/UI_V2_ARQUITECTURA.md`.
- `tests/test_ui_v2.py`: **27 tests** (datos sin Tk + humo de ventana).

**4 bugs de Tk reales encontrados y corregidos** (la UI v2 arrancaba "bien"
pero con partes invisibles): ver *Decisiones de diseño*.

Cierre: **544 tests verdes** + 204 subtests (`pytest tests/ -q`), commits en
`main` **sin pushear**, IA local **APAGADA**, BD con el corpus de 535 avisos y
48 facts de perfil (no se vació nada).

## Lo que se hizo

### 1. Base de la UI v2 (`ui_v2/`) — commit `968e6f6`

Paquete nuevo con capas de responsabilidad única:

| Módulo | Rol |
|---|---|
| `theme.py` | `Palette`/`Metrics`/`Theme` + `apply_theme()` (tema `clam` plano) — ÚNICA fuente de color/tipografía/espaciado |
| `widgets.py` | `Card`, `StatTile`, `Badge`, `SearchField`, `FlatButton`, `EmptyState`, `ScrollFrame`, `SectionTitle`, `KeyValue` |
| `data/jobs.py` | `JobsStore`, `RawQuery`, `RawRow`, `RawDetail` + formato y export CSV (**sin Tk**) |
| `tabs/base.py` | `BaseTab`, `TabContext` — el contrato de una pestaña |
| `tabs/crudos.py` | Pestaña "Datos crudos" |
| `app.py` | `AppShell`, `crear_app()`, `main()`, `PESTANIAS` |

Las pestañas **no tocan SQLite**: hablan con un *store* que devuelve dataclasses.

### 2. Bugs de Tk corregidos (la parte que costó)

1. **Fuentes de estilos `ttk` sin llaves ni tamaño** (`font="Segoe UI"`): Tk la
   parte por espacios → familia `Segoe` + tamaño `UI` → **las filas del
   `ttk.Treeview` no se pintaban** (la app arrancaba, la tabla salía vacía).
   Fix: `{Segoe UI} 10` (llaves) en todas las fuentes, incluidas
   `option_add("*Font", …)` y `Theme.font()`/`mono()`.
2. **`StatTile` creado pero no empaquetado**: quedaba en 1x1 → la franja de
   métricas salía vacía. Fix: `tile.pack(...)` dentro de la tarjeta.
3. **Tabla sin scrollbar horizontal**: las columnas (1158 px) desbordaban el
   ancho → columnas inalcanzables. Fix: `xscrollcommand` + barra inferior.
4. **`EmptyState` con `pack` dentro de un padre con `grid`** (mezcla inválida:
   `TclError` cuando no hubiera filas). Fix: `grid()`/`grid_remove()`.

También: `ScrollFrame` reescrito — el callback de `yscrollcommand` tocaba el
canvas y producía **reentrada infinita**; ahora solo hace `bar.set` y el
`scrollregion` se recalcula en `<Configure>`.

### 3. Pestaña de Perfil

- `data/profile.py`: `ProfileStore`, `ProfileFact`, `ProfileResumen`,
  `ProfileQuery`, `fact_desde_sugerencia`, `exportar_csv`, etiquetas de las 14
  categorías (**sin Tk**).
- `dialogs.py`: `RevisionImportacionDialog` (lista con casillas de lo detectado
  en el CV + avisos + evidencia literal; devuelve los elegidos) y `confirmar()`.
- `tabs/perfil.py`: toolbar (**Importar CV…**, **Revertir importación**,
  **Exportar CSV**, **Actualizar**), franja de resumen (total / categorías /
  de CV / manuales / áreas), tabla de hechos + formulario de alta/edición
  (categoría, código, valor, nivel, estado de educación solo en `education`,
  cantidad/unidad solo en `experience`, notas).
- Registrada en `PESTANIAS`; el shell ya monta las dos pestañas.

### 4. Documentación

- `docs/UI_V2_ARQUITECTURA.md` (nuevo): capas, cómo agregar una pestaña y los
  patrones de Tk.
- `AGENTS.md`: fila nueva en el mapa, comandos de la UI v2 (incluido un humo
  **sin ventana**), gotchas **21–24** (fuentes entre llaves, no mezclar
  pack/grid, `yscrollcommand`, colocar el widget), estado de referencia y el
  hueco del perfil frente al matching.

## Decisiones de diseño

- **La UI clásica no se toca**: `ui.py` sigue siendo la interfaz completa; la
  v2 vive en su paquete y se abre aparte (pueden convivir).
- **Modularidad real**: el shell no conoce el contenido de las pestañas; una
  pestaña nueva = módulo + registro. Nada de estilos a mano: todo sale de
  `theme`.
- **Las pestañas no ven SQLite**: `data/` devuelve dataclasses → testeable sin
  ventana.
- **Sin dependencias nuevas**: solo Tkinter/ttk (el venv no tiene
  customtkinter/ttkbootstrap/PySide/PIL).
- **Perfil = singleton de `candidate_profile_facts`** (sin `candidate_id`); el
  alta manual respeta las validaciones del `Repository`
  (`education_status` solo `education`, `numeric_value` solo `experience`).
- **Se muestra, no se oculta, el hueco de `codigo_canonico`**: la tabla de
  perfil tiene columna "Canónico" (hoy vacía) porque el motor del Paso 5 exige
  `codigo_canonico IS NOT NULL` y `save_candidate_profile_facts` no lo escribe
  (capa B pendiente). **No se cambió el matching** en esta sesión.

## Estado de objetivos (tabla)

| Objetivo | Estado tras esta sesión |
|---|---|
| **O9 Optimización de UI** | **En curso — UI v2 entregada** (base + Datos crudos + Perfil). Los ajustes pendientes de O9 siguen abiertos |
| O1 Enriquecimiento IA | Cerrado (sin cambios) |
| O2/O4 (búsqueda data-first / calibración) | Abiertos, sin cambios; motor semántico dormido |
| O3 Fetchers ATS huérfanos | Sin cambios |
| O5 Higiene de datos | Solo queda **O5.3** (re-barrido de descripciones basura) |
| O6 Perfil del candidato | O6.1–O6.3 cerrados; **O6.4** (dedupe de slugs ES/EN al importar) pendiente de decisión |
| O7 UI-first | Completo (sin cambios) |
| O8 Ciclo de vida | O8.1 hecho; **O8.2** (recurrentes) y **O8.4** (baja por tiempo) pendientes de portar |
| O10 Filtros/compatibilidad | Filtro por área implementado; refinar `solo_vigentes`, columna "Req." |

## Cómo retomar

```powershell
# UI v2 (plana y modular)
.\jobpulse-v15-v2.bat
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15.ui_v2

# UI clásica (intacta)
.\.venv\Scripts\python.exe -m jobpulse_v15.ui

# Humo SIN ventana (monta el shell, refresca y cuenta filas)
.\.venv\Scripts\python.exe -X utf8 -c "from jobpulse_v15.ui_v2.app import crear_app; r,s=crear_app(); [r.update() for _ in range(20)]; t=s.pestana_activa(); t.refresh(); print(t.key, len(t._widgets['tabla'].get_children())); r.destroy()"

# Tests (python del SISTEMA)
python -m pytest tests/test_ui_v2.py -q     # 27 tests
python -m pytest tests/ -q                  # 544 + 204 subtests (~1.7 min)
```

## Archivos clave

- `src/jobpulse_v15/ui_v2/app.py` — shell + `PESTANIAS` (registro de pestañas).
- `src/jobpulse_v15/ui_v2/theme.py` — paleta/medidas/estilos (fuentes entre llaves).
- `src/jobpulse_v15/ui_v2/widgets.py` — componentes (incl. `ScrollFrame` corregido).
- `src/jobpulse_v15/ui_v2/dialogs.py` — `RevisionImportacionDialog`.
- `src/jobpulse_v15/ui_v2/data/jobs.py` · `data/profile.py` — stores (sin Tk).
- `src/jobpulse_v15/ui_v2/tabs/base.py` · `tabs/crudos.py` · `tabs/perfil.py`.
- `tests/test_ui_v2.py` — 27 tests.
- `jobpulse-v15-v2.bat` — lanzador.
- `docs/UI_V2_ARQUITECTURA.md` · `AGENTS.md` (gotchas 21–24, estado).

## Datos de contexto

- BD `data/jobpulse_v15.db`: **535 avisos** (corrida manual del 01-11, intacta) ·
  **48 facts de perfil** (2 importaciones) · 129 sitios · 14 plataformas · 20
  áreas · 70 conceptos. `job_match` = 0 (falta `run_paso5.py`). `db check` ok.
- En la pestaña de Perfil, la BD real muestra: 48 datos · 7 categorías · 48
  importados · 0 manuales · 0 áreas.
- IA local **APAGADA** (puerto 8081 libre).
- Suite: **544 passed + 204 subtests**, 0 fallos. `test_ui_v2.py` = 27.
- Regla del repo respetada: **nada de `ALTER` manual**, migraciones solo como
  archivo nuevo; **no pushear sin confirmación**.

## Pendiente inmediato

1. **Capa B `codigo_canonico` — ahora también para el PERFIL**: resolver y
   persistir `codigo_canonico` al guardar facts (reutilizable:
   `conceptos.resolver`), con backfill de los 48 actuales; sin eso el perfil es
   **invisible** para el Paso 5. Va junto con la migración `017` pendiente.
2. **O6.4**: dedupe de slugs ES/EN del mismo hecho al importar un CV
   (normalizar al importar vs. decidir en el diálogo — falta decisión).
3. Pestañas futuras de la UI v2 (el shell ya está listo): p. ej. **Áreas de
   empleo** (checkbuttons, hoy solo en la UI clásica), **Configuración**, y
   **Vacantes** con el Paso 5 (O8.2/O8.4).
4. Los pendientes de siempre: las **30 `educacion_no_confirmada`** (firma de
   segunda persona), **O5.3** (re-barrido de descripciones basura), Paso 7,
   O8.2/O8.4, O2/O4, y **O10 `solo_vigentes`** (usa `date_published` vs
   `last_seen_at`).
5. **Confirmar con el usuario si se pushea** (los commits de esta sesión están
   en `main` local, sin subir).
