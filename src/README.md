# src

> Blueprint del código fuente: un único paquete instalable, `jobpulse_v15/`.

## Overview

`src/` no contiene archivos propios. Existe para fijar el layout de instalación
(`[tool.setuptools] package-dir = {"" = "src"}` en `pyproject.toml`) y alojar el
paquete del proyecto. Todo el código de dominio vive en `jobpulse_v15/`.

## Subdirectories & System Boundaries

- [`jobpulse_v15/`](jobpulse_v15/README.md) — el paquete: pipeline, motor de
  matching, scrapers, capa IA, persistencia y la UI v2 (con sus propios hijos:
  `migrations/`, `providers/`, `ui_v2/`).

## Invariants

- Solo `jobpulse_v15` se empaqueta: `[tool.setuptools.packages.find] where = ["src"]`.
- **Los datos de apoyo están incompletos en `package-data`**: `pyproject.toml`
  declara solo `jobpulse_v15 = ["seeds/*.json"]`, pero el código también lee en
  runtime `seeds/*.csv` (`ubicaciones_cr.py`) y `migrations/*.sql` (`db.py` los
  carga desde `Path(__file__).parent / "migrations"`). Una instalación **no
  editable** (wheel) no los incluye y `db.initialize()` falla con
  `MigrationError("No existe el directorio ...")` en `db.py:157`.
- Cambiar el layout exige reinstalar con
  `.\.venv\Scripts\python.exe -m pip install -e .`.

## Verification

- Run: `python -m pytest tests/ -q` (pytest vive en el python del **sistema**, no en el venv).
